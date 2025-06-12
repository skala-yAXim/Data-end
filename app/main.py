from contextlib import asynccontextmanager
from app.vectordb.client import get_qdrant_client
from fastapi import FastAPI
from app.api import endpoints
from app.rdb.client import SessionLocal
from app.common.cache import app_cache

@asynccontextmanager
async def lifespan(app: FastAPI):
  qdrant_client = get_qdrant_client()
  app.state.qdrant_client = qdrant_client

  # AppCache 초기화
  db = SessionLocal()
  try:
      app_cache.load(db)  # 여기에 초기화
  finally:
      db.close()

  yield

app = FastAPI(lifespan = lifespan)

app.include_router(endpoints.router)
