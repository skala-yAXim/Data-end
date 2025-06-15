from sqlalchemy.orm import Session
from datetime import datetime, timedelta, date
from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue, DatetimeRange
from app.rdb.schema import DailyUserActivity, User, Weekday
from app.rdb.repository import save_daily_user_activity, flush_daily_user_activity_if_exists, find_all_users
from app.common.config import TEAMS_COLLECTION_NAME, GIT_COLLECTION_NAME, EMAIL_COLLECTION_NAME, DOCS_COLLECTION_NAME
from app.vectordb.client import get_qdrant_client

def save_user_activities_to_rdb(target_date: str, db: Session):
    date = datetime.strptime(target_date, "%Y-%m-%d").date()
    data = load_user_activities_from_vector_db(date, db)

    flush_daily_user_activity_if_exists(db)

    for week in data:
        for day in week:
            user_id = day.get("id")
            statics = day.get("statics")

            teams = statics.get("teams")
            email = statics.get("email")
            docs = statics.get("docs")
            git = statics.get("git")

            activity = DailyUserActivity(
                user_id=user_id,
                report_date=date + timedelta(days=day.get("day")),
                day=Weekday(day.get("day")),        # enum 사용
                teams_post=teams.get("post"),
                teams_reply=teams.get("reply"),
                email_send=email.get("sender"),
                email_receive=email.get("receiver"),
                docs_docx=docs.get("application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
                docs_xlsx=docs.get("application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
                docs_pptx=docs.get("application/vnd.openxmlformats-officedocument.presentationml.presentation"),
                docs_etc=docs.get("else"),
                git_pull_request=git.get("pull_request"),
                git_commit=git.get("commit"),
                git_issue=git.get("issue")
            )
            
            save_daily_user_activity(activity, db)

    return data

def load_user_activities_from_vector_db(target_date: date, db: Session) -> list:
    statics = []

    for i in range(7):
        tmp = []

        curr_date = target_date + timedelta(days=i)
        print(curr_date)

        start_str = f"{curr_date}T00:00:00Z"
        end_str = f"{curr_date}T23:59:59Z"

        client = get_qdrant_client()

        users = find_all_users(db)

        for user in users:
            array = {}
            tmp_dict = {}
            array['teams'] = (teams_report(client, user, start_str, end_str))
            array['email'] = (email_report(client, user, start_str, end_str))
            array['docs'] = (docs_report(client, user, start_str, end_str))
            array['git'] = (git_report(client, user, start_str, end_str))

            # tmp_dict["user"] = user.name
            tmp_dict["id"] = user.id
            tmp_dict["day"] = i
            tmp_dict["statics"] = array

            tmp.append(tmp_dict)

        statics.append(tmp)
    return statics


def teams_report(client: QdrantClient, user: User, start_str: str, end_str: str) -> dict:
    metadata_combinations = ["post", "reply"]

    result = {}

    for metadata in metadata_combinations:
        count = client.count(
                    collection_name=TEAMS_COLLECTION_NAME,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="author",
                                match=MatchValue(value=user.id)
                            ),
                            FieldCondition(
                                key="date",
                                range=DatetimeRange(
                                    gte=start_str,
                                    lte=end_str
                                )
                            ),
                            FieldCondition(
                                key="type",
                                match=MatchValue(value=metadata)
                            )
                        ]
                    ),
                    exact=True
                )
        result[metadata] = count.count
    
    return result


def email_report(client: QdrantClient, user: User, start_str: str, end_str: str) -> dict:
    metadata_combinations = ["sender", "receiver"]

    result = {}

    for metadata in metadata_combinations:
        count = client.count(
                    collection_name=EMAIL_COLLECTION_NAME,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="author",
                                match=MatchValue(value=user.id)
                            ),
                            FieldCondition(
                                key="date",
                                range=DatetimeRange(
                                    gte=start_str,
                                    lte=end_str
                                )
                            ),
                            FieldCondition(
                                key=metadata,
                                match=MatchValue(value=user.email)
                            )
                        ]
                    ),
                    exact=True
                )
        result[metadata] = count.count
    
    return result


def docs_report(client: QdrantClient, user: User, start_str: str, end_str: str) -> dict:
    metadata_combinations = [
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document", 
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation"
    ]

    # TODO: VectorDB에 적재되는 type이 수정되면 바뀌어야 함
    # metadata_combinations = [
    #     "docx", 
    #     "xslx",
    #     "pptx",
    #     "txt"
    # ]

    result = {}
    sum = 0

    for metadata in metadata_combinations:
        count = client.count(
                    collection_name=DOCS_COLLECTION_NAME,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="author",
                                match=MatchValue(value=user.id)
                            ),
                            FieldCondition(
                                key="last_modified",
                                range=DatetimeRange(
                                    gte=start_str,
                                    lte=end_str
                                )
                            ),
                            FieldCondition(
                                key="type",
                                match=MatchValue(value=metadata)
                            )
                        ]
                    ),
                    exact=True
                )
        
        result[metadata] = count.count
        sum += count.count

    count = client.count(
                    collection_name=DOCS_COLLECTION_NAME,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="author",
                                match=MatchValue(value=user.id)
                            ),
                            FieldCondition(
                                key="last_modified",
                                range=DatetimeRange(
                                    gte=start_str,
                                    lte=end_str
                                )
                            )
                        ]
                    ),
                    exact=True
                )
    
    result["else"] = count.count - sum

    return result


def git_report(client: QdrantClient, user: User, start_str: str, end_str: str) -> dict:
    metadata_combinations = [
        "pull_request", 
        "commit",
        "issue"
    ]

    result = {}

    for metadata in metadata_combinations:
        count = client.count(
                    collection_name=GIT_COLLECTION_NAME,
                    count_filter=Filter(
                        must=[
                            FieldCondition(
                                key="author",
                                match=MatchValue(value=user.id)
                            ),
                            FieldCondition(
                                key="date",
                                range=DatetimeRange(
                                    gte=start_str,
                                    lte=end_str
                                )
                            ),
                            FieldCondition(
                                key="type",
                                match=MatchValue(value=metadata)
                            )
                        ]
                    ),
                    exact=True
                )
        result[metadata] = count.count
    
    return result