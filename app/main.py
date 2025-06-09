from contextlib import asynccontextmanager
from app.vectordb.client import get_qdrant_client
from fastapi import FastAPI
from app.api import endpoints

@asynccontextmanager
async def lifespan(app: FastAPI):
  qdrant_client = get_qdrant_client()
  app.state.qdrant_client = qdrant_client

  yield

app = FastAPI(lifespan = lifespan)

app.include_router(endpoints.router)
