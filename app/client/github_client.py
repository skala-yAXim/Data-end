from base64 import b64decode
from sqlalchemy.orm import Session
import time
from typing import List, Optional, Tuple
from cryptography.hazmat.primitives import serialization
import httpx
import jwt
import requests

from app.common.utils import convert_utc_to_kst
from app.schemas.github_activity import CommitEntry, IssueEntry, PullRequestEntry, ReadmeInfo
from app.common.cache import app_cache

BASE_URL = "https://api.github.com"

def load_private_key(private_key_path: str):
    """
    주어진 경로에서 GitHub App용 PEM private key를 로드
    """
    with open(private_key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
        )

def create_jwt_token(app_id: str, private_key) -> str:
    """
    GitHub App용 JWT 토큰 생성 (10분 유효)
    """
    now = int(time.time())
    payload = {
        "iat": now,
        "exp": now + (10 * 60),  # 10분 후 만료
        "iss": app_id,
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")
    
    print("JWT 토큰 생성 완료")
    
    return token

def get_installation_access_token(jwt_token: str) -> list[str]:
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json"
    }

    # 설치된 앱 리스트 조회
    response = requests.get("https://api.github.com/app/installations", headers=headers)
    response.raise_for_status()  # 오류 시 예외 발생

    installations = response.json()
    if not installations:
        raise Exception("No installations found for this GitHub App.")

    teams = app_cache.teams
    installation_ids = [team.installation_id for team in teams if team.installation_id is not None]
    access_tokens = []
    # TODO installation id 확인 후 수정 필요!
    installation_ids = ["71420197"]

    for installation_id in installation_ids:
        access_token_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
        token_response = requests.post(access_token_url, headers=headers)
        token_response.raise_for_status()

        access_token = token_response.json().get("token")
        if not access_token:
            raise Exception("Failed to obtain installation access token.")
        
        access_tokens.append(access_token)

    return access_tokens

def get_headers(access_token: str):
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json"
    }

async def fetch_repositories(access_token: str) -> List[Tuple[str, str]]:
    url = f"{BASE_URL}/installation/repositories"

    async with httpx.AsyncClient() as client:
        res = await client.get(url, headers=get_headers(access_token))
        res.raise_for_status()

        data = res.json()
        return [
            (repo["owner"]["login"], repo["name"])
            for repo in data.get("repositories", [])
        ]

async def fetch_user_email(username: str, access_token: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    사용자 GitHub 공개 이메일을 조회합니다. 없을 경우 None을 반환합니다.
    """
    user_url = f"{BASE_URL}/users/{username}"
    headers = get_headers(access_token)

    try:
        res = await client.get(user_url, headers=headers)
        res.raise_for_status()
        user_data = res.json()
        return user_data.get("email")  # 이메일이 공개된 경우만 반환
    except httpx.HTTPStatusError as e:
        print(f"HTTP error while fetching user {username}: {e.response.status_code}")
    except Exception as e:
        print(f"Unexpected error while fetching user {username}: {e}")
    
    return None

async def fetch_all_branch_commits(
    owner: str,
    repo: str,
    access_token: str,
    git_email: dict[str, int],
    git_id: dict[str, int],
    limit_per_branch: int = None  # None이면 제한 없이 전체 가져오기
) -> List[CommitEntry]:
    branches_url = f"{BASE_URL}/repos/{owner}/{repo}/branches"
    commits = []
    seen_shas = set()

    async with httpx.AsyncClient() as client:
        try:
            res_branches = await client.get(branches_url, headers=get_headers(access_token))
            res_branches.raise_for_status()
            branches = res_branches.json()

            for branch in branches:
                branch_name = branch["name"]
                page = 1
                fetched = 0

                while True:
                    commits_url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
                    params = {
                        "sha": branch_name,
                        "per_page": 100,
                        "page": page
                    }

                    res_commits = await client.get(commits_url, headers=get_headers(access_token), params=params)
                    res_commits.raise_for_status()
                    commit_items = res_commits.json()

                    if not commit_items:
                        break  # 더 이상 커밋 없음

                    for item in commit_items:
                        sha = item["sha"]
                        if sha in seen_shas:
                            continue

                        seen_shas.add(sha)

                        commit = item["commit"]
                        author_email = commit["author"]["email"] if commit.get("author") else None
                        author_id = git_email.get(author_email, 0)

                        commits.append(CommitEntry(
                            repo=f"{owner}/{repo}",
                            sha=sha,
                            message=commit.get("message"),
                            date=convert_utc_to_kst(commit["author"]["date"]),
                            author=author_id
                        ))

                        fetched += 1
                        if limit_per_branch and fetched >= limit_per_branch:
                            break

                    if limit_per_branch and fetched >= limit_per_branch:
                        break
                    page += 1

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"Unexpected error occurred: {str(e)}")
            raise

    return commits


async def fetch_pull_requests(
    owner: str,
    repo: str,
    access_token: str,
    git_email: dict[str, int],
    git_id: dict[str, int]
) -> List[PullRequestEntry]:
    base_url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
    page = 1
    per_page = 100
    result = []

    try:
        async with httpx.AsyncClient() as client:
            while True:
                params = {"state": "all", "per_page": per_page, "page": page}
                res = await client.get(base_url, headers=get_headers(access_token), params=params)
                res.raise_for_status()

                pull_requests = res.json()
                if not pull_requests:
                    break  # 더 이상 PR이 없으면 종료

                for pr in pull_requests:
                    username = pr["user"]["login"] if pr.get("user") else None
                    author_email = None

                    if username:
                        try:
                            author_email = await fetch_user_email(username, access_token, client)
                        except Exception:
                            author_email = None

                    mapped_author = git_email.get(author_email, None)
                    if not mapped_author:
                        mapped_author = git_id.get(username, 0)

                    result.append(PullRequestEntry(
                        repo=f"{owner}/{repo}",
                        number=pr["number"],
                        title=pr.get("title"),
                        content=pr.get("body"),
                        created_at=convert_utc_to_kst(pr["created_at"]),
                        state=pr["state"],
                        author=mapped_author or username  # fallback
                    ))

                page += 1  # 다음 페이지로

        return result

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred while fetching PRs: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"Unexpected error occurred while fetching PRs: {e}")
        return []


async def fetch_issues(
    owner: str,
    repo: str,
    access_token: str,
    git_email: dict[str, int],
    git_id: dict[str, int]
) -> List[IssueEntry]:
    base_url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
    page = 1
    per_page = 100
    issues = []

    try:
        async with httpx.AsyncClient() as client:
            while True:
                params = {"state": "all", "per_page": per_page, "page": page}
                res = await client.get(base_url, headers=get_headers(access_token), params=params)
                res.raise_for_status()

                issue_batch = res.json()
                if not issue_batch:
                    break  # 더 이상 가져올 이슈 없음

                for issue in issue_batch:
                    if "pull_request" in issue:
                        continue  # PR은 제외

                    username = issue["user"]["login"] if issue.get("user") else None
                    author_email = None

                    if username:
                        try:
                            author_email = await fetch_user_email(username, access_token, client)
                        except Exception:
                            author_email = None

                    mapped_author = git_email.get(author_email, None)
                    if not mapped_author:
                        mapped_author = git_id.get(username, 0)

                    issues.append(IssueEntry(
                        repo=f"{owner}/{repo}",
                        number=issue["number"],
                        title=issue.get("title"),
                        created_at=convert_utc_to_kst(issue["created_at"]),
                        state=issue["state"],
                        author=mapped_author or username
                    ))

                page += 1  # 다음 페이지로 이동

        return issues

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred while fetching issues: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"Unexpected error occurred while fetching issues: {e}")
        return []


async def fetch_readme(owner: str, repo: str, access_token: str) -> Optional[ReadmeInfo]:
    url = f"{BASE_URL}/repos/{owner}/{repo}/readme"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=get_headers(access_token))
            if res.status_code == 404:
                return None
            res.raise_for_status()

            data = res.json()
            decoded = b64decode(data["content"]).decode("utf-8")
            return ReadmeInfo(
                repo_name=f"{owner}/{repo}",
                content=decoded,
                html_url=data["html_url"],
                download_url=data.get("download_url")
            )

    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred while fetching README: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error occurred while fetching README: {e}")
        return None