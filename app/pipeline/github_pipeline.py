from datetime import datetime
from sqlalchemy.orm import Session
from app.client.github_client import create_jwt_token, fetch_all_branch_commits, fetch_issues, fetch_pull_requests, fetch_readme, fetch_repositories, get_installation_access_token, load_private_key
from app.extractor.github_activity_extractor import extract_record_from_commit_entry, extract_record_from_issue_entry, extract_record_from_pull_request_entry, extract_record_from_readme
from app.common.config import GIT_COLLECTION_NAME, GITHUB_APP_ID, GITHUB_PRIVATE_KEY_PATH, README_COLLECTION_NAME
from app.schemas.github_activity import GitActivity
from app.vectordb.uploader import upload_data_to_db
from app.common.utils import get_git_emails_and_ids

async def save_all_data_for_repo(owner: str, repo: str, access_token: str, git_email: dict[str, int], git_id: dict[str, int], date: datetime):
    commits = await fetch_all_branch_commits(owner, repo, access_token, git_email, date)
    commit_records = [extract_record_from_commit_entry(commit) for commit in commits]
    if commit_records:
        upload_data_to_db(collection_name=GIT_COLLECTION_NAME, records=commit_records)
    else:
        print("커밋 데이터 없음. 업로드 생략.")
    
    prs = await fetch_pull_requests(owner, repo, access_token, git_email, git_id, date)
    pr_records = [extract_record_from_pull_request_entry(pr) for pr in prs]
    if pr_records:
        upload_data_to_db(collection_name=GIT_COLLECTION_NAME, records=pr_records)
    else:
        print("PR 데이터 없음. 업로드 생략.")
    
    issues = await fetch_issues(owner, repo, access_token, git_email, git_id, date)
    issue_records = [extract_record_from_issue_entry(issue) for issue in issues]
    if issue_records:
        upload_data_to_db(collection_name=GIT_COLLECTION_NAME, records=issue_records)
    else:
        print("이슈 데이터 없음. 업로드 생략.")
    
    readme = await fetch_readme(owner, repo, access_token)
    
    readme_record = extract_record_from_readme(readme)
    if readme_record:
        upload_data_to_db(collection_name=README_COLLECTION_NAME, records=[readme_record])
    else:
        print("README 데이터 없음. 업로드 생략.")
    
    return GitActivity(
        repo = f"{owner}/{repo}",
        commits = commits,
        pull_requests = prs,
        issues =  issues,
        readme = readme
    )


async def save_github_data(db: Session, date: datetime):
    # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
    private_key = load_private_key(GITHUB_PRIVATE_KEY_PATH)
    jwt_token = create_jwt_token(GITHUB_APP_ID, private_key)
    access_tokens = get_installation_access_token(jwt_token, db) # list로 반환
    git_email, git_id = get_git_emails_and_ids(db)
    
    results = []
    
    for access_token in access_tokens:
        repos = await fetch_repositories(access_token=access_token)
        
        for owner, repo in repos:
            result = await save_all_data_for_repo(owner, repo, access_token, git_email, git_id, date)
            results.append(result)

    return results
