from app.schemas.github_activity import UserActivitySchema
from app.services.github_service import fetch_github_data
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/")
def read_root():
    return {"message": "Hello from FastAPI"}


@router.get("/github/data", response_model=List[UserActivitySchema])
async def get_github_data():
    """
    설치된 모든 GitHub repository에 대해 커밋, PR, 이슈, README 데이터를 반환합니다.
    """
    data = await fetch_github_data()
    return data