from sqlalchemy.orm import Session
from typing import List
from app.client.ms_graph_client import fetch_all_teams, fetch_channel_posts, fetch_channels, get_access_token
from app.common.config import MICROSOFT_CLIENT_ID, MICROSOFT_CLIENT_SECRET, MICROSOFT_TENANT_ID, TEAMS_COLLECTION_NAME
from app.extractor.teams_post_extractor import create_records_from_post_entry
from app.schemas.teams_post_activity import PostEntry
from app.vectordb.uploader import upload_data_to_db

async def save_teams_posts_data(db: Session):
    # TODO: 오늘 날짜 데이터만 긁어올 수 있도록 수정
    token = get_access_token(client_id=MICROSOFT_CLIENT_ID, client_secret=MICROSOFT_CLIENT_SECRET, tenant_id=MICROSOFT_TENANT_ID)
    
    teams = fetch_all_teams(token)
    
    all_team_posts: List[PostEntry] = []
    
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

                channel_posts = fetch_channel_posts(token, team_id, channel_id, db)
                team_posts.extend(channel_posts)

        except Exception as e:
            print(f"오류 발생 (팀:{team_name}): {e}")

        all_team_posts.extend(team_posts)
    
    records = []
    for team_post in all_team_posts:
        preprocessed_docs = create_records_from_post_entry(team_post)
        records.extend(preprocessed_docs)
    
    upload_data_to_db(collection_name=TEAMS_COLLECTION_NAME, records=records)
    
    return all_team_posts
