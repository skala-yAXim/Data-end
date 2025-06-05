from typing import List, Optional
from app.common.utils import extract_from_docx, extract_from_txt, extract_from_xlsx, split_into_chunks
from app.schemas.docs_activity import DocsEntry
from app.vectordb.schema import BaseRecord, DocumentMetadata

def extract_file_content(docs_entry: DocsEntry, file_path: str) -> List[str]:
    
    file_ext = docs_entry.filename.lower().split('.')[-1]

    try:
        if file_ext == 'docx':
            content = extract_from_docx(file_path)
            if content:
                return split_into_chunks(content)
            else:
                return []
        elif file_ext == 'xlsx':
            return extract_from_xlsx(file_path)  # 이미 List[str] 반환
        elif file_ext == 'txt':
            content = extract_from_txt(file_path)
            if content:
                return split_into_chunks(content)
            else:
                return []
        else:
            print("지원하지 않는 파일 형식")
            return [f"지원하지 않는 파일 형식: {file_ext}"]
    except Exception as e:
        return f"파일 읽기 오류: {str(e)}"


def create_record_from_entry(contents: List[str], entry: DocsEntry) -> List[BaseRecord[DocumentMetadata]]:
    records = []
    for idx, chunk in enumerate(contents):
        text = chunk.strip()
        if not text:
            continue  # 빈 청크는 무시
        
        records.append(BaseRecord[DocumentMetadata](
            text=text,
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
