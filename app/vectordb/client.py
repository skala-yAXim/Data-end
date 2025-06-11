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

def flush_collection(collection_name: str, host: str = "localhost", port: int = 6333):
    client = get_qdrant_client()
    response = client._client.post(f"/collections/{collection_name}/flush")
    return response.json()
