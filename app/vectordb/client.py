from typing import List
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
import requests
import os
from dotenv import load_dotenv

from app.common.config import DOCS_COLLECTION_NAME, EMAIL_COLLECTION_NAME, GIT_COLLECTION_NAME, README_COLLECTION_NAME, TEAMS_COLLECTION_NAME

load_dotenv()

def get_qdrant_client() -> QdrantClient:
  QDRANT_HOST = os.getenv("QDRANT_HOST")
  QDRANT_PORT = os.getenv("QDRANT_PORT", "6333")

  return QdrantClient(
    host=QDRANT_HOST,
    port=QDRANT_PORT
  )

def create_collection(client: QdrantClient, collection_name: str): 
  client.create_collection(
      collection_name=collection_name,
      vectors_config=VectorParams(size=384, distance=Distance.COSINE),
  )
  
def flush_all_collections():
    client = get_qdrant_client()
    # 모든 컬렉션 이름 가져오기
    collections = [TEAMS_COLLECTION_NAME, EMAIL_COLLECTION_NAME, GIT_COLLECTION_NAME, DOCS_COLLECTION_NAME, README_COLLECTION_NAME]

    deleted = []
    errors = []
    
    for collection_name in collections:
        try:
            print(f"Deleting collection: {collection_name}")
            client.delete_collection(collection_name=collection_name)
            deleted.append(collection_name)
        except Exception as e:
            print(f"Unexpected error while deleting {collection_name}: {e}")
            errors.append((collection_name, str(e)))

    if deleted:
        print(f"✅ Deleted collections: {', '.join(deleted)}")
    if errors:
        print("Errors occurred during deletion:")
        for name, msg in errors:
            print(f" - {name}: {msg}")

    return "완료!"