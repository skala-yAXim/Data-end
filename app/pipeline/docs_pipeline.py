import os
from typing import List
from app.client.ms_graph_client import download_file_from_graph, fetch_all_sites, fetch_drive_files, get_access_token, get_drive_id
from app.common.config import DOCS_COLLECTION_NAME, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID
from app.extractor.document_extractor import create_record_from_entry, extract_file_content
from app.schemas.docs_activity import DocsEntry
from app.vectordb.uploader import upload_data_to_db

async def save_docs_data():
    # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
    token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
    
    all_docs: List[DocsEntry] = []
    sites = fetch_all_sites(token)
    
    for site in sites:
        site_id = site.get("id")
        site_name = site.get("name")
        site_url = site.get("webUrl", "")
        
        if not site_id:
            print(f"[건너뜀] site_id 없음: {site}")
            continue
        
        print(f"[시도 중] 사이트 이름: {site_name}, 주소: {site_url}")

        try:
            site_id = site_id
            if not site_id:
                continue

            drive_id = get_drive_id(token, site_id)
            if not drive_id:
                continue

            docs = fetch_drive_files(token, drive_id)
            all_docs.extend(docs)

        except Exception as e:
            print(f"[오류] 사이트 {site_name} 처리 중 오류 발생: {str(e)}")
            continue
    
    records = []

    for doc in all_docs:
        try:
            file_path = download_file_from_graph(
                drive_id=doc.drive_id,
                file_id=doc.file_id,
                filename=doc.filename,
                access_token=token
            )
            content = extract_file_content(doc, file_path)
        finally:
            try:
                os.remove(file_path)
                os.rmdir(os.path.dirname(file_path))
            except Exception:
                pass
        
        if content is None:
            content = ""  # 빈 문자열로 대체하거나 continue 할 수도 있음
        
        record_list = create_record_from_entry(content, doc)
        records.extend(record_list)
    
    upload_data_to_db(collection_name=DOCS_COLLECTION_NAME, records=records)
        
    return all_docs




