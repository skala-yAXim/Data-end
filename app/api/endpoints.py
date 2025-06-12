from app.schemas.docs_activity import DocsEntry
from app.schemas.email_activity import EmailEntry
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

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}


@router.get("/github/data")
async def get_github_data():
    """
    설치된 모든 GitHub repository에 대해 커밋, PR, 이슈 데이터를 저장하여 반환합니다.
    """
    data = await save_github_data()
    return data

@router.get("/outlook/data", response_model=List[EmailEntry])
async def get_outlook_data():
    """
    모든 사용자의 outlook 이메일 데이터를 저장 후 반환합니다.
    """
    data = await save_all_email_data()
    return data

@router.get("/teams/post", response_model=List[PostEntry])
async def get_teams_post_data():
    """
    조직 내 Teams 게시물 데이터를 저장 후 반환합니다.
    """
    data = await save_teams_posts_data()
    return data

@router.get("/document/data", response_model=List[DocsEntry])
async def get_document_data():
    """
    조직 내 문서 데이터를 저장 후 반환합니다.
    """
    data = await save_docs_data()
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