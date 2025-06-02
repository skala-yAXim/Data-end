from datetime import datetime, timezone
from msal import ConfidentialClientApplication
import requests
from typing import Dict, List
from app.schemas.email_activity import EmailEntry, UserEmailActivitySchema
from app.core.config import MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID

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
def fetch_all_users_emails(token: str) -> List[UserEmailActivitySchema]:
    """모든 유저에 대해 메일 리스트 조회하여 UserEmailActivitySchema 리스트로 반환"""
    user_emails = fetch_user_emails(token)
    all_results: List[UserEmailActivitySchema] = []

    for email in user_emails:
        print(f"사용자: {email} 메일 조회 중...")
        inbox_emails = fetch_user_inbox_emails(token, email)
        sent_emails = fetch_user_sent_emails(token, email)
        combined_emails = inbox_emails + sent_emails

        user_activity = UserEmailActivitySchema(
            author=email,
            emails=combined_emails
        )
        all_results.append(user_activity)

    return all_results

async def fetch_all_email_data():
  # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
  token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
  return fetch_all_users_emails(token)