from app.common.config import EMAIL_COLLECTION_NAME, GIT_COLLECTION_NAME, TEAMS_COLLECTION_NAME
from app.extractor.email_extractor import extract_email_content
from app.extractor.github_activity_extractor import extract_record_from_commit_entry, extract_record_from_issue_entry, extract_record_from_pull_request_entry
from app.extractor.teams_post_extractor import create_records_from_post_entry
from app.schemas.docs_activity import DocsEntry
from app.schemas.email_activity import EmailEntry
from app.schemas.github_activity import GitActivity
from app.schemas.teams_post_activity import PostEntry
from app.pipeline.docs_pipeline import save_docs_data
from app.pipeline.email_pipeline import save_all_email_data
from app.pipeline.github_pipeline import save_github_data
from app.pipeline.teams_post_pipeline import save_teams_posts_data
from app.rdb.repository import find_all_teams, find_all_users, find_all_team_members, find_all_git_info
from app.rdb.client import get_db
from app.common.statics_report import save_user_activities_to_rdb
from fastapi import APIRouter, Request, Depends, Path
from sqlalchemy.orm import Session
from typing import List

from app.test_data_functions import load_commits_from_json, load_emails_from_json, load_issues_from_json, load_posts_from_json, load_pull_requests_from_json
from app.vectordb.client import flush_all_collections
from app.vectordb.uploader import upload_data_to_db

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}


@router.get("/github/data", response_model=List[GitActivity])
async def get_github_data(db: Session = Depends(get_db)):
    """
    설치된 모든 GitHub repository에 대해 커밋, PR, 이슈 데이터를 저장하여 반환합니다.
    """
    data = await save_github_data(db)
    return data

@router.get("/outlook/data", response_model=List[EmailEntry])
async def get_outlook_data(db: Session = Depends(get_db)):
    """
    모든 사용자의 outlook 이메일 데이터를 저장 후 반환합니다.
    """
    data = await save_all_email_data(db)
    return data

@router.get("/teams/post", response_model=List[PostEntry])
async def get_teams_post_data(db: Session = Depends(get_db)):
    """
    조직 내 Teams 게시물 데이터를 저장 후 반환합니다.
    """
    data = await save_teams_posts_data(db)
    return data

@router.get("/document/data", response_model=List[DocsEntry])
async def get_document_data(db: Session = Depends(get_db)):
    """
    조직 내 문서 데이터를 저장 후 반환합니다.
    """
    data = await save_docs_data(db)
    return data

@router.get("/collections")
def list_collections(request: Request):
    """
    VectorDB 연결 확인 api, DB의 collection 리스트 반환
    """
    qdrant = request.app.state.qdrant_client
    return qdrant.get_collections()

@router.get("/team/all")
def get_all_teams(db: Session = Depends(get_db)):
    """
    Teams 게시물에 대한 분석 데이터를 반환합니다.
    """
    return find_all_teams(db)

@router.get("/user/all")
def get_all_users(db: Session = Depends(get_db)):
    """
    모든 사용자 정보를 반환합니다.
    """
    return find_all_users(db)

@router.get("/team-member/all")
def get_all_team_members(db: Session = Depends(get_db)):
    """
    모든 팀 멤버 정보를 반환합니다.
    """
    return find_all_team_members(db)

@router.get("/git-hub/all")
def get_all_team_members(db: Session = Depends(get_db)):
    """
    모든 팀 멤버 정보를 반환합니다.
    """
    return find_all_git_info(db)

@router.get("/vectordb/userActivity/{target_date}")
def get_vector_user_activity(
    target_date: str = Path(..., description="기준 날짜 (YYYY-MM-DD 형식) / 가급적 금요일로 테스트바랍니다.."),
    db: Session = Depends(get_db)
):
    """
    모든 팀 멤버의 활동 정보를 벡터DB에 저장합니다.
    """
    # TODO: 일요일 저녁에 배치 돌린다는 가정 하에, 7일 전으로 설정되게 할 것
    # return save_user_activities_to_rdb("2025-05-30", db)
    return save_user_activities_to_rdb(target_date, db)

@router.get("/flush")
def flush_collections(request: Request):
    return flush_all_collections()

@router.get("/git-test-data")
def get_git_test_data():
    commits = load_commits_from_json("data/commit_entries_mock.json")
    prs = load_pull_requests_from_json("data/pull_requests_mock.json")
    issues = load_issues_from_json("data/git_issue_data.json")
    
    commit_records = [extract_record_from_commit_entry(commit) for commit in commits]
    pr_records = [extract_record_from_pull_request_entry(pr) for pr in prs]
    issue_records = [extract_record_from_issue_entry(issue) for issue in issues]
    
    upload_data_to_db(collection_name=GIT_COLLECTION_NAME, records = commit_records)
    upload_data_to_db(collection_name=GIT_COLLECTION_NAME, records = pr_records)
    upload_data_to_db(collection_name=GIT_COLLECTION_NAME, records = issue_records)
    
    return

@router.get("/email-test-data")
def get_email_test_data(
    db: Session = Depends(get_db)
):
    emails = load_emails_from_json("data/full_email_data.json")
    email_records = [extract_email_content(email, db) for email in emails]
    upload_data_to_db(collection_name=EMAIL_COLLECTION_NAME, records = email_records)
    
    
@router.get("/teams-test-data")
def get_teams_test_data():
    teams = load_posts_from_json("data/teams_post_data.json")
    teams_records = []
    for team in teams:
        preprocessed_docs = create_records_from_post_entry(team)
        teams_records.extend(preprocessed_docs)

    upload_data_to_db(collection_name=TEAMS_COLLECTION_NAME, records = teams_records)