from collections import defaultdict
import requests
import time
from datetime import datetime, timezone
from cryptography.hazmat.primitives import serialization
import jwt
import httpx
from base64 import b64decode
from typing import List, Tuple, Optional
import asyncio

from app.schemas.github_activity import (
    CommitEntry,
    PullRequestEntry,
    IssueEntry,
    ReadmeInfo,
    CommitActivity,
    PullRequestActivity,
    IssueActivity,
    UserActivitySchema
)
from app.core.config import GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH

BASE_URL = "https://api.github.com"

def load_private_key(private_key_path: str):
    """
    주어진 경로에서 GitHub App용 PEM private key를 로드합니다.
    
    Args:
        private_key_path (str): PEM 키 파일 경로

    Returns:
        private key object (RSAPrivateKey 등)
    """
    with open(private_key_path, "rb") as f:
        return serialization.load_pem_private_key(
            f.read(),
            password=None,
        )

def create_jwt_token(app_id: str, private_key) -> str:
    """
    GitHub App용 JWT 토큰 생성 (10분 유효)
    
    Args:
        app_id: GitHub App ID
        private_key: PEM private key 객체 (cryptography로 로드된 키)
    
    Returns:
        str: JWT 토큰 문자열
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
    """
    GitHub App JWT 토큰을 이용해 설치된 Installation ID를 조회하고,
    해당 Installation에 대한 Access Token을 발급받아 반환합니다.
    
    Args:
        jwt_token (str): GitHub App JWT 토큰 (Bearer 토큰)

    Returns:
        access_token (str): Installation Access Token
        installation_info (dict): 설치 정보 (id, account login, account type 등)
    """
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

    # 첫 번째 설치 정보 사용 (필요시 여러 개 중 선택 로직 추가 가능)
    # TODO: DB에서 installation id를 가져와서 넣는 방식으로 수정
    install = installations[0]
    installation_id = install['id']

    print(f"Installation ID: {installation_id}")
    print(f"Target login: {install['account']['login']} ({install['account']['type']})")

    # Installation Access Token 요청
    access_token_url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    token_response = requests.post(access_token_url, headers=headers)
    token_response.raise_for_status()

    access_token = token_response.json().get("token")
    if not access_token:
        raise Exception("Failed to obtain installation access token.")

    return access_token, install

def get_headers(access_token: str):
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/vnd.github+json"
    }

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

                result.append(PullRequestEntry(
                    repo=f"{owner}/{repo}",
                    number=pr["number"],
                    title=pr.get("title"),
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

async def fetch_all_data_for_repo(owner: str, repo: str, access_token: str):
    commits = await fetch_all_branch_commits(owner, repo, access_token)
    prs = await fetch_pull_requests(owner, repo, access_token)
    issues = await fetch_issues(owner, repo, access_token)
    readme = await fetch_readme(owner, repo, access_token)
    
    return {
        "repo": f"{owner}/{repo}",
        "commits": commits,
        "pull_requests": prs,
        "issues": issues,
        "readme": readme
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

def group_activities_by_author(results: List[dict]) -> List[UserActivitySchema]:
    # TODO: 유저별로 묶을 때 readme 데이터 어떻게 할지 고민해야함
    # TODO: 계정정보 -> 같은 사람이 두 개로 나뉘어져서 나오는 문제 해결해야 함!
    user_map = defaultdict(lambda: {
        "commits": [],
        "pull_requests": [],
        "issues": []
    })

    for repo_data in results:
        for commit in repo_data["commits"]:
            if commit.author:
                user_map[commit.author]["commits"].append(
                    CommitActivity(
                        repo=commit.repo,
                        sha=commit.sha,
                        message=commit.message,
                        date=commit.date
                    )
                )

        for pr in repo_data["pull_requests"]:
            if pr.author:
                user_map[pr.author]["pull_requests"].append(
                    PullRequestActivity(
                        repo=pr.repo,
                        number=pr.number,
                        title=pr.title,
                        created_at=pr.created_at,
                        state=pr.state
                    )
                )

        for issue in repo_data["issues"]:
            if issue.author:
                user_map[issue.author]["issues"].append(
                    IssueActivity(
                        repo=issue.repo,
                        number=issue.number,
                        title=issue.title,
                        created_at=issue.created_at,
                        state=issue.state
                    )
                )

    user_activities = []
    for author, activities in user_map.items():
        user_activities.append(UserActivitySchema(
            author=author,
            commits=activities["commits"],
            pull_requests=activities["pull_requests"],
            issues=activities["issues"],
        ))

    return user_activities

async def fetch_github_data():
    # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
    private_key = load_private_key(GITHUB_PRIVATE_KEY_PATH)
    jwt_token = create_jwt_token(GITHUB_APP_ID, private_key)
    access_token, installation_info = get_installation_access_token(jwt_token)
    
    repos = await fetch_repositories(access_token=access_token)
    
    tasks = [
        fetch_all_data_for_repo(owner, repo, access_token)
        for owner, repo in repos
    ]
    results = await asyncio.gather(*tasks)

    return group_activities_by_author(results)
