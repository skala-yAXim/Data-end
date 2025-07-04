from base64 import b64decode
from datetime import datetime
from sqlalchemy.orm import Session
import time
from typing import List, Optional, Tuple
from cryptography.hazmat.primitives import serialization
import httpx
import jwt
import requests
from sqlalchemy.orm import Session
from qdrant_client.http import models

from app.client.utils import parse_last_page
from app.common.utils import convert_utc_to_kst
from app.schemas.github_activity import CommitEntry, IssueEntry, PullRequestEntry, ReadmeInfo
from app.rdb.repository import find_all_teams
from app.vectordb.client import get_qdrant_client
from app.common.config import README_COLLECTION_NAME

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

def get_installation_access_token(jwt_token: str, db: Session) -> list[str]:
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

    teams = find_all_teams(db)
    installation_ids = [team.installation_id for team in teams if team.installation_id is not None]
    access_tokens = []

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
    date: datetime,
    limit_per_branch: int = None
) -> List[CommitEntry]:
    branches_url = f"{BASE_URL}/repos/{owner}/{repo}/branches"
    commits = []
    seen_shas = set()
    target_date_kst = date.date()

    async with httpx.AsyncClient() as client:
        try:
            res_branches = await client.get(branches_url, headers=get_headers(access_token))
            res_branches.raise_for_status()
            branches = res_branches.json()

            for branch in branches:
                branch_name = branch["name"]
                commits_url = f"{BASE_URL}/repos/{owner}/{repo}/commits"
                params = {
                    "sha": branch_name,
                    "per_page": 100,
                    "page": 1
                }

                # 먼저 첫 페이지 요청
                res = await client.get(commits_url, headers=get_headers(access_token), params=params)
                res.raise_for_status()
                commit_items = res.json()
                link_header = res.headers.get("Link", "")
                last_page = parse_last_page(link_header)

                fetched = 0
                for page in range(1, last_page + 1):
                    if page != 1:
                        params["page"] = page
                        res = await client.get(commits_url, headers=get_headers(access_token), params=params)
                        res.raise_for_status()
                        commit_items = res.json()

                    if not commit_items:
                        break

                    for item in commit_items:
                        sha = item["sha"]
                        if sha in seen_shas:
                            continue
                        seen_shas.add(sha)

                        commit = item["commit"]
                        author_email = commit["author"]["email"] if commit.get("author") else None
                        author_id = git_email.get(author_email, 0)
                        
                        commit_datetime_kst = convert_utc_to_kst(commit["author"]["date"])
                        commit_date_kst = commit_datetime_kst.date()
                        
                        if commit_date_kst != target_date_kst:
                            continue
                        
                        commits.append(CommitEntry(
                            repo=f"{owner}/{repo}",
                            sha=sha,
                            message=commit.get("message"),
                            date=commit_datetime_kst,
                            author=author_id
                        ))

                        fetched += 1
                        if limit_per_branch and fetched >= limit_per_branch:
                            break

                    if limit_per_branch and fetched >= limit_per_branch:
                        break

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
    git_id: dict[str, int],
    date: datetime
) -> List[PullRequestEntry]:
    base_url = f"{BASE_URL}/repos/{owner}/{repo}/pulls"
    per_page = 100
    result = []
    target_date_kst = date.date()

    try:
        async with httpx.AsyncClient() as client:
            # 1. 첫 페이지 요청
            params = {"state": "all", "per_page": per_page, "page": 1}
            res = await client.get(base_url, headers=get_headers(access_token), params=params)
            res.raise_for_status()
            pull_requests = res.json()
            link_header = res.headers.get("Link", "")
            last_page = parse_last_page(link_header)

            # 2. 페이지 반복
            for page in range(1, last_page + 1):
                if page != 1:
                    params["page"] = page
                    res = await client.get(base_url, headers=get_headers(access_token), params=params)
                    res.raise_for_status()
                    pull_requests = res.json()

                if not pull_requests:
                    break

                for pr in pull_requests:
                    username = pr["user"]["login"] if pr.get("user") else None
                    author_email = None
                    
                    pr_datetime_kst = convert_utc_to_kst(pr["created_at"])
                    pr_date_kst = pr_datetime_kst.date()
                    
                    if pr_date_kst != target_date_kst:
                        continue

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
                        created_at=pr_datetime_kst,
                        state=pr["state"],
                        author=mapped_author or username
                    ))

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
    git_id: dict[str, int],
    date: datetime
) -> List[IssueEntry]:
    base_url = f"{BASE_URL}/repos/{owner}/{repo}/issues"
    per_page = 100
    issues = []
    target_date_kst = date.date()

    try:
        async with httpx.AsyncClient() as client:
            # 첫 페이지 요청 및 Link 헤더에서 마지막 페이지 파악
            params = {"state": "all", "per_page": per_page, "page": 1}
            res = await client.get(base_url, headers=get_headers(access_token), params=params)
            res.raise_for_status()
            issue_batch = res.json()
            link_header = res.headers.get("Link", "")
            last_page = parse_last_page(link_header)

            for page in range(1, last_page + 1):
                if page != 1:
                    params["page"] = page
                    res = await client.get(base_url, headers=get_headers(access_token), params=params)
                    res.raise_for_status()
                    issue_batch = res.json()

                if not issue_batch:
                    break

                for issue in issue_batch:
                    if "pull_request" in issue:
                        continue
                    
                    issue_datetime_kst = convert_utc_to_kst(issue["created_at"])
                    issue_date_kst =issue_datetime_kst.date()
                    
                    if issue_date_kst != target_date_kst:
                        continue

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
                        created_at=issue_date_kst,
                        state=issue["state"],
                        author=mapped_author or username
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
            repo_name = f"{owner}/{repo}"
            readme_hash = data.get("sha", "")
        
            if await get_sha_from_vector_db(repo_name) == readme_hash:
                print(f"{repo_name}의 README 변경사항 없음. 저장 생략.")
                return None
            else: 
                print(f"{repo_name}의 README 변경사항 있음. 저장 진행.")
                return ReadmeInfo(
                    repo_name=repo_name,
                    content=decoded,
                    html_url=data["html_url"],
                    download_url=data.get("download_url"),
                    readme_hash=readme_hash
                )


    except httpx.HTTPStatusError as e:
        print(f"HTTP error occurred while fetching README: {e.response.status_code} - {e.response.text}")
        return None
    except Exception as e:
        print(f"Unexpected error occurred while fetching README: {e}")
        return None
    

async def get_sha_from_vector_db(repo_name: str) -> Optional[str]:
    """
    벡터 DB에서 주어진 repo_name에 해당하는 README의 SHA를 조회합니다.
    """

    try:
        client = get_qdrant_client()

        if not client.collection_exists(README_COLLECTION_NAME):
            return None

        # Qdrant scroll 메서드 올바른 사용법
        result = client.scroll(
            collection_name=README_COLLECTION_NAME,
            limit=1,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="repo_name",
                        match=models.MatchValue(value=repo_name)
                    )
                ]
            ),
            with_payload=True  # 페이로드 포함
        )

        # 결과에서 SHA 추출
        points, _ = result
        if points:
            point = points[0]
            sha = point.payload.get('readme_hash')
            print(f"벡터DB에서 조회한 {repo_name} SHA: {sha[:8] if sha else 'None'}...")
            return sha
        else:
            print(f"벡터DB에서 {repo_name}을 찾을 수 없습니다.")
            return None
    except Exception as e:
        print(f"Error fetching SHA from vector DB for {repo_name}: {e}")
        return None