from app.core.config import EMBEDDING_MODEL_NAME
from app.vectordb.client import create_collection, get_qdrant_client
from app.vectordb.schema import BaseRecord
from sentence_transformers import SentenceTransformer
from typing import List
from pydantic import BaseModel

def upload_data_to_db(
    collection_name: str,
    records: List[BaseRecord],
): 
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
    
    client = get_qdrant_client()
    
    print("벡터DB 클라이언트 연결 완료")
    
    if not client.collection_exists(collection_name):
        create_collection(client=client, collection_name=collection_name)
    
    print("데이터 저장 시작!")
    
    points = []
    for record in records:
        # 임베딩 직접 생성 (만약 record.vector가 없으면)
        vector = record.vector if hasattr(record, "vector") else embedding_model.encode(record.text).tolist()

        # 메타데이터 dict로 변환
        metadata = record.metadata.model_dump() if hasattr(record.metadata, "model_dump") else dict(record.metadata)
        metadata["page_content"] = record.text
        
        points.append({
            "id": record.id,
            "vector": vector,
            "payload": metadata
        })
    
    client.upsert(
        collection_name=collection_name,
        points=points
    )
    
    print("데이터 저장 완료!")
