from typing import List, Optional
from app.common.utils import extract_from_docx, extract_from_txt, extract_from_xlsx, split_into_chunks
from app.schemas.docs_activity import DocsEntry
from app.vectordb.schema import BaseRecord, DocumentMetadata

def extract_file_content(docs_entry: DocsEntry, file_path: str) -> Optional[str]:
    
    file_ext = docs_entry.filename.lower().split('.')[-1]

    try:
        if file_ext == 'docx':
            return extract_from_docx(file_path)
        elif file_ext == 'xlsx':
            return extract_from_xlsx(file_path)
        elif file_ext == 'txt':
            return extract_from_txt(file_path)
        else:
            print("지원하지 않는 파일 형식")
            return f"지원하지 않는 파일 형식: {file_ext}"
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}"


def create_record_from_entry(content: str, entry: DocsEntry) -> List[BaseRecord[DocumentMetadata]]:
    file_ext = entry.filename.lower().split('.')[-1]
    should_chunk = file_ext in ['docx', 'txt']
    
    chunks = []
    
    if should_chunk:
        chunks = split_into_chunks(content)
        if len(chunks) == 0:
            chunks = [content.strip()]  # fallback 처리
    else:
      chunks = [content.strip()]
    
    records = []
    for idx, chunk in enumerate(chunks):
        records.append(BaseRecord[DocumentMetadata](
            text=chunk,
            metadata=DocumentMetadata(
                file_id=entry.file_id,
                filename=entry.filename,
                author=entry.author,
                last_modified=entry.last_modified,
                type=entry.type,
                size=entry.size,
                chunk_id=idx
            )
        ))
    
    return records