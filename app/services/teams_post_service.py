from datetime import datetime, timezone
import json
import re
from dateutil.parser import parse
from typing import List, Union
from app.core.config import MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID
from app.schemas.teams_post_activity import PostEntry, ReplyEntry, TeamPost
from app.vectordb.schema import BaseRecord, TeamsPostMetadata
from app.vectordb.uploader import upload_data_to_db
from msal import ConfidentialClientApplication
import requests

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

def fetch_replies_for_message(token: str, team_id: str, channel_id: str, message_id: str) -> List[ReplyEntry]:
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
            reply_content = reply.get("body", {}).get("content", "")
            reply_date_str = reply.get("createdDateTime", "")
            try:
                reply_date = parse(reply_date_str) if reply_date_str else datetime.now(timezone.utc)
            except:
                reply_date = datetime.now(timezone.utc)
            reply_attachments = [
                att.get("name")
                for att in reply.get("attachments", [])
                if att.get("name") is not None
            ]

            replies.append(ReplyEntry(
                author=reply_author,
                content=reply_content,
                date=reply_date,
                attachments=reply_attachments if reply_attachments else []
            ))
    else:
        print(f"댓글 조회 실패: {response.status_code}")
        print(response.text)

    return replies


def fetch_channel_posts(token: str, team_id: str, channel_id: str) -> List[PostEntry]:
    endpoint = f"https://graph.microsoft.com/v1.0/teams/{team_id}/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    posts: List[PostEntry] = []
    url = endpoint

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
                author = "System"
            else:
                user_info = from_info.get("user")
                application_info = from_info.get("application")

                if user_info:
                    user_id = user_info.get("id")
                    author = get_user_email(user_id, token) if user_id else "알 수 없음"
                elif application_info:
                    author = application_info.get("displayName", "알 수 없음")
                else:
                    author = "System"
            
            subject = item.get("subject") or ""
            summary = item.get("summary") or ""       
            content = item.get("body", {}).get("content", "")
            date_str = item.get("createdDateTime", "")
            try:
                date = parse(date_str) if date_str else datetime.now(timezone.utc)
            except Exception:
                date = datetime.now(timezone.utc)
            
            
            attachments_raw = item.get("attachments", [])

            attachments = []
            application_content = None

            for att in attachments_raw:
                content_type = att.get("contentType")
                
                if content_type == "application/vnd.microsoft.card.adaptive":
                    # Adaptive Card 내용 처리
                    attachment_content = att.get("content", "")
                    if content:
                        application_content = extract_text_values(attachment_content)
                else:
                    # 일반 파일 첨부 처리
                    name = att.get("name")
                    if name:
                        attachments.append(name)

            replies: List[ReplyEntry] = fetch_replies_for_message(token, team_id, channel_id, item["id"])

            # replies 필드는 API에서 바로 안 오므로 별도 호출이 필요할 수 있음 (간략화된 버전)
            # 실제 사용 시에는 메시지 ID로 별도 replies endpoint 호출

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

def fetch_all_team_posts(token: str) -> List[TeamPost]:
    all_team_posts: List[TeamPost] = []
    teams = fetch_all_teams(token)

    for team in teams:
        team_id = team["id"]
        team_name = team.get("displayName", "알 수 없는 팀")
        print(f"▶ 팀: {team_name} (ID: {team_id}) 채널 조회 중...")

        team_posts: List[PostEntry] = []

        try:
            channels = fetch_channels(token, team_id)
            for channel in channels:
                channel_id = channel["id"]
                channel_name = channel.get("displayName", "알 수 없는 채널")
                print(f"  └ 채널: {channel_name} (ID: {channel_id}) 메시지 조회 중...")

                channel_posts = fetch_channel_posts(token, team_id, channel_id)
                team_posts.extend(channel_posts)

        except Exception as e:
            print(f"오류 발생 (팀:{team_name}): {e}")

        all_team_posts.append(TeamPost(
            team_id=team_id,
            team_name=team_name,
            posts=team_posts if team_posts else None
        ))

    return all_team_posts

async def save_teams_posts_data():
  # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
  token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
  
  posts_data = fetch_all_team_posts(token)
  
  preprocessed_docs = extract_texts_from_posts_data(posts_data)
  
  collection_name = "Teams-Posts"
  
  upload_data_to_db(collection_name=collection_name, records=preprocessed_docs)
  
  return posts_data


def extract_text_values(json_str):
    def recursive_extract(obj, results):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == "text":
                    results.append(value)
                else:
                    recursive_extract(value, results)
        elif isinstance(obj, list):
            for item in obj:
                recursive_extract(item, results)

    try:
        parsed = json.loads(json_str)
        texts = []
        recursive_extract(parsed, texts)
        return texts
    except json.JSONDecodeError as e:
        print("Invalid JSON:", e)
        return []

def clean_html(raw_html):
    return re.sub(r'<[^>]+>', '', raw_html)

def extract_texts_from_posts_data(team_posts: List[TeamPost]) -> List[BaseRecord[TeamsPostMetadata]]:
    docs: List[BaseRecord[TeamsPostMetadata]] = []

    for team_post in team_posts:
        for post in team_post.posts or []:
            parsed = parse_json(post)

            record = BaseRecord[TeamsPostMetadata](
                text=parsed.text,
                metadata=TeamsPostMetadata(
                    user_id=parsed.metadata.user_id,
                    date=parsed.metadata.date
                )
            )
            docs.append(record)

            for reply in post.replies or []:
                parsed_reply = parse_json(
                    data=reply,
                    is_reply=True,
                    post_content=post.content
                )
                reply_record = BaseRecord[TeamsPostMetadata](
                    text=parsed_reply.text,
                    metadata=TeamsPostMetadata(
                        user_id=parsed_reply.metadata.user_id,
                        date=parsed_reply.metadata.date
                    )
                )
                docs.append(reply_record)

    return docs


def parse_json(
    data: Union[PostEntry, ReplyEntry],
    is_reply: bool = False,
    post_content: str = None
) -> BaseRecord[TeamsPostMetadata]:
    text_parts = []

    if is_reply:
        if post_content:
            text_parts.append("Reply to: " + clean_html(post_content))
        text_parts.append("Reply Content: " + clean_html(data.content))
    else:
        if getattr(data, "subject", None):
            text_parts.append(f"Subject: {data.subject}")
        if getattr(data, "content", None):
            text_parts.append(clean_html(data.content))
        if getattr(data, "application_content", None):
            text_parts.extend(data.application_content or [])

    if getattr(data, "attachments", None):
        for attachment in data.attachments:
            text_parts.append(f"Attachment: {attachment}")

    combined_text = "\n".join(text_parts).strip()

    metadata = TeamsPostMetadata(
        user_id=data.author,
        date=data.date
    )

    return BaseRecord[TeamsPostMetadata](
        text=combined_text,
        metadata=metadata
    )
