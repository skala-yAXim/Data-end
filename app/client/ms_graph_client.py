from datetime import datetime, timedelta, timezone
import os
import re
from sqlalchemy.orm import Session
from typing import List, Optional
from msal import ConfidentialClientApplication
import requests
from dateutil.parser import parse
from app.common.utils import convert_utc_to_kst, extract_text_from_json
from app.schemas.docs_activity import DocsEntry
from app.schemas.email_activity import EmailEntry
from app.schemas.teams_post_activity import PostEntry, ReplyEntry
from app.common.utils import get_user_emails_and_names

KST = timezone(timedelta(hours=9))

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

def get_user_email(user_id: str, access_token: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/users/{user_id}"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data.get("mail") or data.get("userPrincipalName") or "알 수 없음"
    else:
        return "알 수 없음"

def get_drive_id(access_token: str, site_id: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"드라이브 ID 조회 실패: {response.status_code} - {response.text}")

def fetch_all_teams(token: str):
    endpoint = "https://graph.microsoft.com/v1.0/groups?$filter=resourceProvisioningOptions/Any(x:x eq 'Team')"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    
    teams = []
    url = endpoint

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            teams.extend(data.get("value", []))
            url = data.get("@odata.nextLink")  # 페이징 처리
        else:
            raise Exception(f"팀 목록 조회 실패: {response.status_code} {response.text}")
    
    return teams

def fetch_channels(token: str, team_id: str):
    endpoint = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    response = requests.get(endpoint, headers=headers)
    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        raise Exception(f"채널 조회 실패: {response.status_code} {response.text}")

def fetch_replies_for_message(token: str, team_id: str, channel_id: str, message_id: str, user_email: dict[str, int]) -> List[ReplyEntry]:
    endpoint = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    response = requests.get(endpoint, headers=headers)
    replies: List[ReplyEntry] = []

    if response.status_code == 200:
        reply_data = response.json().get("value", [])
        for reply in reply_data:
            reply_author_id = reply.get("from", {}).get("user", {}).get("id", "알 수 없음")
            reply_author = get_user_email(reply_author_id, token)
            author = user_email.get(reply_author, 0)
            reply_content = reply.get("body", {}).get("content", "")
            reply_date = convert_utc_to_kst(reply.get("createdDateTime", ""))
            
            reply_attachments = [
                att.get("name")
                for att in reply.get("attachments", [])
                if att.get("name") is not None
            ]

            replies.append(ReplyEntry(
                author=author,
                content=reply_content,
                date=reply_date,
                attachments=reply_attachments if reply_attachments else []
            ))
    else:
        print(f"댓글 조회 실패: {response.status_code}")
        print(response.text)

    return replies

def fetch_channel_posts(token: str, team_id: str, channel_id: str, db: Session) -> List[PostEntry]:
    endpoint = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    posts: List[PostEntry] = []
    url = endpoint

    user_email, user_name = get_user_emails_and_names(db)

    while url:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"메시지 조회 실패 (팀:{team_id}, 채널:{channel_id}): {response.status_code}")
            print(response.text)
            break

        data = response.json()
        for item in data.get("value", []):
            # print(item)
            from_info = item.get("from")
            if from_info is None:
                author = 0
            else:
                user_info = from_info.get("user")
                application_info = from_info.get("application")

                if user_info:
                    user_id = user_info.get("id")
                    author = get_user_email(user_id, token) if user_id else "알 수 없음"
                    author = user_email.get(author, 0)
                elif application_info:
                    author = application_info.get("displayName", 0)
                else:
                    author = 0
            
            subject = item.get("subject") or ""
            summary = item.get("summary") or ""       
            content = item.get("body", {}).get("content", "")
            date = convert_utc_to_kst(item.get("createdDateTime", ""))
            
            attachments_raw = item.get("attachments", [])

            attachments = []
            application_content = None

            for att in attachments_raw:
                content_type = att.get("contentType")
                
                if content_type == "application/vnd.microsoft.card.adaptive":
                    # Adaptive Card 내용 처리
                    attachment_content = att.get("content", "")
                    if content:
                        application_content = extract_text_from_json(attachment_content)
                else:
                    # 일반 파일 첨부 처리
                    name = att.get("name")
                    if name:
                        attachments.append(name)

            replies: List[ReplyEntry] = fetch_replies_for_message(token, team_id, channel_id, item["id"], user_email)

            if author == "Jira Cloud" and application_content[0]:
                match = re.match(r"([^\s]+)\s", application_content[0])
                if match:
                    author = user_name.get(match.group(1), 0)

            posts.append(PostEntry(
                author=author,
                subject=subject,
                summary=summary,
                content=content,
                date=date,
                attachments=attachments if attachments else [],
                application_content=application_content,
                replies=replies
            ))

        url = data.get("@odata.nextLink")

    return posts

def fetch_all_sites(access_token: str) -> List[dict]:
    url = "https://graph.microsoft.com/v1.0/sites?search=*"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        raise Exception(f"사이트 목록 조회 실패: {response.status_code} - {response.text}")
    
    return response.json().get("value", [])

def fetch_drive_files(access_token: str, drive_id: str, user_info: dict[str, int], folder_id: Optional[str] = None) -> List[DocsEntry]:
    entries: List[DocsEntry] = []

    # 폴더 경로 설정
    if folder_id:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{folder_id}/children"
    else:
        url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/root/children"

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"파일 목록 조회 실패: {response.status_code} - {response.text}")

    data = response.json().get("value", [])

    for item in data:
        filename = item.get("name")
        size = item.get("size", 0)
        last_modified = item.get("lastModifiedDateTime")
        url_link = item.get("webUrl", "")
        file_type = (
            item.get("file", {}).get("mimeType") if "file" in item
            else "folder" if "folder" in item else "unknown"
        )
        file_id = item.get("id", "unknown")


        authors = set()

        # 작성자 정보
        created_by = item.get("createdBy", {}).get("user", {})
        if created_by:
            email = created_by.get("email") or created_by.get("displayName", "알 수 없음")
            user_id = user_info.get(email, 0)
            authors.add(user_id)

        # 파일 버전 기록 확인
        if "file" in item:
            versions_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item['id']}/versions"
            versions_response = requests.get(versions_url, headers=headers)

            if versions_response.status_code == 200:
                versions = versions_response.json().get("value", [])
                for version in versions:
                    modified_by = version.get("lastModifiedBy", {}).get("user", {})
                    if modified_by:
                        email = modified_by.get("email") or modified_by.get("displayName", "알 수 없음")
                        user_id = user_info.get(email, 0)
                        authors.add(user_id)

        # 폴더면 재귀적으로 내부 파일 가져오기
        if "folder" in item:
            folder_items = fetch_drive_files(access_token, drive_id, user_info, item["id"])
            entries.extend(folder_items)
        else:
            entry = DocsEntry(
                filename=filename,
                author=list(authors),
                last_modified=last_modified,
                type=file_type,
                size=size,
                file_id=file_id,
                drive_id=drive_id
            )
            entries.append(entry)

    return entries

def download_file_from_graph(drive_id: str, file_id: str, filename: str, access_token: str) -> str:
    import tempfile

    tmp_dir = tempfile.mkdtemp(prefix="docs_dl_")
    file_path = os.path.join(tmp_dir, filename)

    download_url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{file_id}/content"
    headers = {"Authorization": f"Bearer {access_token}"}

    response = requests.get(download_url, headers=headers)
    if response.status_code != 200:
        raise Exception(f"파일 다운로드 실패: {response.status_code} - {response.text}")

    with open(file_path, "wb") as f:
        f.write(response.content)

    return file_path

def fetch_user_email_ids(token: str) -> List[str]:
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
        receivers: List[str] = []

        for msg in messages:
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
            receivers = [
                recipient.get("emailAddress", {}).get("address", "")
                for recipient in msg.get("toRecipients", [])
            ]
            subject = msg.get("subject", "")
            content = msg.get("body", {}).get("content", "")
            date = convert_utc_to_kst(msg.get("receivedDateTime", ""))
            conversation_id = msg.get("conversation_id", "")
            attachments = msg.get("attachments", [])

            attachment_list = [att.get("name", "") for att in attachments if att.get("@odata.type") != "#microsoft.graph.itemAttachment"]

            email_entry = EmailEntry(
                author=user_email,
                sender=sender,
                receivers=receivers,
                subject=subject,
                content=content,
                date=date,
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
        receivers: List[str] = []

        for msg in messages:
            sender = msg.get("from", {}).get("emailAddress", {}).get("address", "")
            receivers = [
                recipient.get("emailAddress", {}).get("address", "")
                for recipient in msg.get("toRecipients", [])
            ]
            subject = msg.get("subject", "")
            content = msg.get("body", {}).get("content", "")
            date = convert_utc_to_kst(msg.get("receivedDateTime", ""))
            conversation_id = msg.get("conversationId", "")
            attachments = msg.get("attachments", [])

            attachment_list = [att.get("name", "") for att in attachments if att.get("@odata.type") != "#microsoft.graph.itemAttachment"]

            email_entry = EmailEntry(
                author=user_email,
                sender=sender,
                receivers=receivers,
                subject=subject,
                content=content,
                date=date,
                conversation_id=conversation_id,
                attachment_list=attachment_list if attachment_list else None
            )
            results.append(email_entry)

        return results

    else:
        print(f"API 요청 실패: {response.status_code}")
        print(response.text)
        return []