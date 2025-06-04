import chromadb
from chromadb.config import Settings

# 기본 설정값 (필요시 settings.yaml이나 .env에서 불러오도록 확장 가능)
CHROMA_DB_DIR = "chroma_db"  # 로컬 디스크에 저장될 경로
COLLECTION_NAME = "documents"  # 기본 컬렉션명

def get_chroma_client() -> chromadb.PersistentClient:
    return chromadb.PersistentClient(path=CHROMA_DB_DIR)

def get_or_create_collection(client: chromadb.PersistentClient, name: str = COLLECTION_NAME):
    return client.get_or_create_collection(name=name)