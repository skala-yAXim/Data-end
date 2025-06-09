from base64 import b64decode
import time
from typing import List, Optional, Tuple
from cryptography.hazmat.primitives import serialization
import httpx
import jwt
import requests

from app.schemas.github_activity import CommitEntry, IssueEntry, PullRequestEntry, ReadmeInfo
from data import GIT

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

def get_installation_access_token(jwt_token: str):
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

    # TODO: DB에서 installation id를 가져와서 넣는 방식으로 수정
    # Installation Access Token 요청
    access_token_url = f"https://api.github.com/app/installations/68835585/access_tokens"
    token_response = requests.post(access_token_url, headers=headers)
    token_response.raise_for_status()

    access_token = token_response.json().get("token")
    if not access_token:
        raise Exception("Failed to obtain installation access token.")

    return access_token

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

async def fetch_all_branch_commits(owner: str, repo: str, access_token: str, limit_per_branch: int = 5) -> List[CommitEntry]:
    branches_url = f"{BASE_URL}/repos/{owner}/{repo}/branches"
    commits = []

    async with httpx.AsyncClient() as client:
        try:
            # 1. 브랜치 목록 조회
            res_branches = await client.get(branches_url, headers=get_headers(access_token))
            res_branches.raise_for_status()
            branches = res_branches.json()

            # 2. 각 브랜치별 커밋 조회
            for branch in branches:
                branch_name = branch["name"]
                commits_url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
                params = {"sha": branch_name, "per_page": limit_per_branch}
                res_commits = await client.get(commits_url, headers=get_headers(access_token), params=params)
                res_commits.raise_for_status()

                for item in res_commits.json():
                    commit = item["commit"]
                    author_name = commit["author"]["email"] if commit.get("author") else None
                    
                    author_name = GIT.get(author_name, author_name)

                    commits.append(CommitEntry(
                        repo=f"{owner}/{repo}",
                        sha=item["sha"],
                        message=commit.get("message"),
                        date=commit["author"]["date"],
                        author=author_name
                    ))

        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            print(f"Unexpected error occurred: {str(e)}")
            raise

    return commits


async def fetch_pull_requests(owner: str, repo: str, access_token: str) -> List[PullRequestEntry]:
    url = f"{BASE_URL}/repos/{owner}/{repo}/pulls?state=all"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=get_headers(access_token))
            res.raise_for_status()

            pull_requests = res.json()
            result = []

            for pr in pull_requests:
                username = pr["user"]["login"] if pr.get("user") else None
                author_email = None

                if username:
                    author_email = await fetch_user_email(username, access_token, client)
                
                author_email = GIT.get(author_email, author_email)

                result.append(PullRequestEntry(
                    repo=f"{owner}/{repo}",
                    number=pr["number"],
                    title=pr.get("title"),
                    content=pr.get("body"),
                    created_at=pr["created_at"],
                    state=pr["state"],
                    author=author_email or username  # fallback to username
                ))

            return result
    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred while fetching PRs: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"Unexpected error occurred while fetching PRs: {e}")
        return []


async def fetch_issues(owner: str, repo: str, access_token: str) -> List[IssueEntry]:
    url = f"{BASE_URL}/repos/{owner}/{repo}/issues?state=all"

    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=get_headers(access_token))
            res.raise_for_status()

            issues = []
            for issue in res.json():
                if "pull_request" in issue:
                    continue

                username = issue["user"]["login"] if issue.get("user") else None
                author_email = None

                if username:
                    author_email = await fetch_user_email(username, access_token, client)

                author_email = GIT.get(author_email, author_email)
                
                issues.append(IssueEntry(
                    repo=f"{owner}/{repo}",
                    number=issue["number"],
                    title=issue.get("title"),
                    created_at=issue["created_at"],
                    state=issue["state"],
                    author=author_email or username
                ))

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
                name=data["name"],
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