from app.schemas.docs_activity import DocsEntry
from app.schemas.email_activity import EmailEntry
from app.schemas.teams_post_activity import PostEntry
from app.services.docs_service import save_docs_data
from app.services.email_service import save_all_email_data
from app.services.github_service import save_github_data
from app.services.teams_post_service import save_teams_posts_data
from fastapi import APIRouter, Request
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