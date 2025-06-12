from typing import List
from app.client.ms_graph_client import fetch_user_email_ids, fetch_user_inbox_emails, fetch_user_sent_emails, get_access_token
from app.extractor.email_extractor import extract_email_content
from app.schemas.email_activity import EmailEntry
from app.common.config import EMAIL_COLLECTION_NAME, MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID
from app.vectordb.uploader import upload_data_to_db

async def save_all_email_data():
    # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
    token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
    
    all_emails: List[EmailEntry] = []
    
    all_users = fetch_user_email_ids(token)
    
    for user in all_users:
        print(f"[INFO] 사용자 '{user}'의 메일을 조회 중...")

        inbox = fetch_user_inbox_emails(token, user)
        sent = fetch_user_sent_emails(token, user)

        all_emails.extend(inbox)
        all_emails.extend(sent)
    
    records = [extract_email_content(email) for email in all_emails]
    if records:
        upload_data_to_db(collection_name=EMAIL_COLLECTION_NAME, records=records)
        
    return all_emails
