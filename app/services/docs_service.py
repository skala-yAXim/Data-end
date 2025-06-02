from datetime import datetime, timezone
from typing import List, Optional
from app.core.config import MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID
from app.schemas.docs_activity import DocsEntry
from msal import ConfidentialClientApplication
import requests
from dateutil.parser import parse

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

def get_sharepoint_domain(access_token: str) -> str:
    url = "https://graph.microsoft.com/v1.0/sites/root"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        web_url = response.json().get("webUrl", "")
        # 예: https://contoso.sharepoint.com -> contoso.sharepoint.com 추출
        domain = web_url.replace("https://", "").split("/")[0]
        return domain
    else:
        raise Exception(f"SharePoint 도메인 조회 실패: {response.status_code} - {response.text}")

def get_site_id(access_token: str, domain: str, site_name: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{domain}:/sites/{site_name}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"사이트 ID 조회 실패: {response.status_code} - {response.text}")

def get_drive_id(access_token: str, site_id: str) -> str:
    url = f"https://graph.microsoft.com/v1.0/sites/{site_id}/drive"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json().get("id")
    else:
        raise Exception(f"드라이브 ID 조회 실패: {response.status_code} - {response.text}")
      
def fetch_drive_files(access_token: str, drive_id: str, folder_id: Optional[str] = None) -> List[DocsEntry]:
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

        authors = set()

        # 작성자 정보
        created_by = item.get("createdBy", {}).get("user", {})
        if created_by:
            email = created_by.get("email") or created_by.get("displayName", "알 수 없음")
            authors.add(email)

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
                        authors.add(email)

        # 폴더면 재귀적으로 내부 파일 가져오기
        if "folder" in item:
            folder_items = fetch_drive_files(access_token, drive_id, item["id"])
            entries.extend(folder_items)
        else:
            entry = DocsEntry(
                filename=filename,
                author=list(authors),
                last_modified=datetime.fromisoformat(last_modified.replace("Z", "+00:00")) if last_modified else None,
                type=file_type,
                size=size,
                url=url_link
            )
            entries.append(entry)

    return entries

def fetch_all_sites_files(access_token: str, domain: str) -> List[DocsEntry]:
    # 1. 전체 사이트 목록 가져오기
    list_sites_url = "https://graph.microsoft.com/v1.0/sites?search=*"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(list_sites_url, headers=headers)

    if response.status_code != 200:
        raise Exception(f"사이트 목록 조회 실패: {response.status_code} - {response.text}")

    sites = response.json().get("value", [])
    all_entries: List[DocsEntry] = []

    for site in sites:
        site_name = site.get("name")
        if not site_name:
            continue

        try:
            # 2. 사이트 ID 조회
            site_id = get_site_id(access_token, domain, site_name)
            if not site_id:
                continue

            # 3. 드라이브 ID 조회
            drive_id = get_drive_id(access_token, site_id)
            if not drive_id:
                continue

            # 4. 드라이브 파일 목록 조회
            entries = fetch_drive_files(access_token, drive_id)
            all_entries.extend(entries)

        except Exception as e:
            print(f"[오류] 사이트 {site_name} 처리 중 오류 발생: {str(e)}")
            continue

    return all_entries

async def fetch_docs_data():
  # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
  token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
  domain = get_sharepoint_domain(token)
  return fetch_all_sites_files(token, domain)