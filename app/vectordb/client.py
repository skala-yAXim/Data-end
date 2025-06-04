from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

def get_qdrant_client() -> QdrantClient:
  return QdrantClient(
    host="localhost",
    port=6333
  )

def create_collection(client: QdrantClient, collection_name: str): 
  client.create_collection(
      collection_name=collection_name,
      vectors_config=VectorParams(size=384, distance=Distance.COSINE),
  )