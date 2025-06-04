from contextlib import asynccontextmanager
from app.vectordb.client import get_chroma_client, get_or_create_collection
from fastapi import FastAPI
from app.api import endpoints

@asynccontextmanager
async def lifespan(app: FastAPI):
  client = get_chroma_client()
  collection = get_or_create_collection(client)
  
  app.state.chroma_client = client
  app.state.chroma_collection = collection
  
  yield

app = FastAPI(lifespan = lifespan)

app.include_router(endpoints.router)
