from datetime import datetime, timezone
from msal import ConfidentialClientApplication
import requests
from typing import Dict, List
from app.schemas.email_activity import EmailEntry
from app.core.config import MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID
from app.vectordb.schema import BaseRecord, EmailMetadata
from app.vectordb.uploader import upload_data_to_db

def get_access_token(client_id: str, client_secret: str, tenant_id: str):
    # Graph API 설정
    authority = f"https://login.microsoftonline.com/{tenant_id}"
    scope = ["https://graph.microsoft.com/.default"]

    # MSAL 앱 초기화
    app = ConfidentialClientApplication(
        client_id,
        authority=authority,
        client_credential=client_secret
    )

    # 액세스 토큰 요청
    result = app.acquire_token_for_client(scopes=scope)

    if "access_token" in result:
        return result["access_token"]
    else:
        # 에러 메시지 출력
        error = result.get("error", "unknown_error")
        error_description = result.get("error_description", "No description provided.")
        raise Exception(f"토큰 요청 실패: {error} - {error_description}")

def fetch_user_emails(token: str) -> List[str]:
    endpoint = "https://graph.microsoft.com/v1.0/users"
    headers = {
        "Authorization": f"Bearer {token}"
    }

    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        users = response.json()
        emails = [user.get('userPrincipalName') for user in users.get("value", [])]
        return emails
    else:
        print(f"API 요청 실패: {response.status_code}")
        print(response.text)
        return []

def fetch_user_inbox_emails(token: str, user_email: str) -> List[EmailEntry]:
    endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/mailFolders/Inbox/messages?$expand=attachments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": 'outlook.body-content-type="text"'  # HTML 대신 plain text로 가져오도록 요청
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        messages = response.json().get("value", [])
        results: List[EmailEntry] = []

        for msg in messages:
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
            receiver = msg.get("toRecipients", [{}])[0].get("emailAddress", {}).get("address", "")
            subject = msg.get("subject", "")
            content = msg.get("body", {}).get("content", "")
            date = msg.get("receivedDateTime", "")
            conversation_id = msg.get("conversation_id", "")
            attachments = msg.get("attachments", [])

            # 수신일자 문자열을 datetime으로 변환
            try:
                parsed_date = datetime.fromisoformat(date.rstrip('Z'))
            except Exception:
                parsed_date = datetime.now(timezone.utc)

            attachment_list = [att.get("name", "") for att in attachments if att.get("@odata.type") != "#microsoft.graph.itemAttachment"]

            email_entry = EmailEntry(
                author=user_email,
                sender=sender,
                receiver=receiver,
                subject=subject,
                content=content,
                date=parsed_date,
                conversation_id=conversation_id,
                attachment_list=attachment_list if attachment_list else None
            )
            results.append(email_entry)

        return results

    else:
        print(f"API 요청 실패: {response.status_code}")
        print(response.text)
        return []

def fetch_user_sent_emails(token: str, user_email: str) -> List[EmailEntry]:
    endpoint = f"https://graph.microsoft.com/v1.0/users/{user_email}/mailFolders/SentItems/messages?$expand=attachments"
    headers = {
        "Authorization": f"Bearer {token}",
        "Prefer": 'outlook.body-content-type="text"'  # HTML 대신 plain text로 가져오도록 요청
    }

    response = requests.get(endpoint, headers=headers)

    if response.status_code == 200:
        messages = response.json().get("value", [])
        results: List[EmailEntry] = []

        for msg in messages:
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
            receiver = msg.get("toRecipients", [{}])[0].get("emailAddress", {}).get("address", "")
            subject = msg.get("subject", "")
            content = msg.get("body", {}).get("content", "")
            date = msg.get("receivedDateTime", "")
            conversation_id = msg.get("conversationId", "")
            attachments = msg.get("attachments", [])

            # 수신일자 문자열을 datetime으로 변환
            try:
                parsed_date = datetime.fromisoformat(date.rstrip('Z'))
            except Exception:
                parsed_date = datetime.now(timezone.utc)

            attachment_list = [att.get("name", "") for att in attachments if att.get("@odata.type") != "#microsoft.graph.itemAttachment"]

            email_entry = EmailEntry(
                author=user_email,
                sender=sender,
                receiver=receiver,
                subject=subject,
                content=content,
                date=parsed_date,
                conversation_id=conversation_id,
                attachment_list=attachment_list if attachment_list else None
            )
            results.append(email_entry)

        return results

    else:
        print(f"API 요청 실패: {response.status_code}")
        print(response.text)
        return []
    
def fetch_all_users_emails(token: str) -> List[EmailEntry]:
    """
    모든 유저에 대해 받은 편지함과 보낸 편지함 메일을 조회하여 EmailEntry 리스트로 반환
    """
    user_emails = fetch_user_emails(token)
    all_emails: List[EmailEntry] = []

    for user_email in user_emails:
        print(f"[INFO] 사용자 '{user_email}'의 메일을 조회 중...")

        inbox = fetch_user_inbox_emails(token, user_email)
        sent = fetch_user_sent_emails(token, user_email)

        all_emails.extend(inbox)
        all_emails.extend(sent)

    return all_emails


async def save_all_email_data():
    # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
    token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
    
    all_emails = fetch_all_users_emails(token)
    
    collection_name = "Emails"
    records = [extract_email_content(email) for email in all_emails]
    
    if records:
        upload_data_to_db(collection_name=collection_name, records=records)
        
    return all_emails

def extract_email_content(email: EmailEntry) -> BaseRecord[EmailMetadata]:
    attachments_text = ", ".join(email.attachment_list) if email.attachment_list else "None"
    combined_text = f"Content: {email.content.strip()}\nAttachments: {attachments_text}"
    
    return BaseRecord[EmailMetadata](
        text=combined_text,
        metadata=EmailMetadata(
            author=email.author,
            sender=email.sender,
            receiver=email.receiver,
            subject=email.subject,
            date=email.date,
            conversation_id=email.conversation_id
        )
    )