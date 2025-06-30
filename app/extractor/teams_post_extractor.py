from typing import List, Union
from app.common.utils import clean_html
from app.schemas.teams_post_activity import PostEntry, ReplyEntry
from app.vectordb.schema import BaseRecord, TeamsPostMetadata
import re

def create_records_from_post_entry(team_post: PostEntry) -> List[BaseRecord[TeamsPostMetadata]]:
    docs: List[BaseRecord[TeamsPostMetadata]] = []

    post_record = parse_post_data(team_post)

    docs.append(post_record)

    for reply in team_post.replies or []:
        reply_record = parse_post_data(
            data=reply,
            is_reply=True,
            post_content=team_post.content
        )

        docs.append(reply_record)

    return docs

def parse_post_data(
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

    cleaned_text_parts = []
    for part in text_parts:
        cleaned = part.replace('\t', '')              # 탭 제거
        cleaned = cleaned.replace('&nbsp;', ' ')      # HTML 비공개 공백 제거
        cleaned = cleaned.replace('\u00A0', ' ')      # 유니코드 비공개 공백 제거
        cleaned_text_parts.append(cleaned)

    combined_text = "\n".join(cleaned_text_parts).strip()

    metadata = TeamsPostMetadata(
        author=data.author,
        type="post" if not is_reply else "reply",
        date=data.date
    )

    return BaseRecord[TeamsPostMetadata](
        text=combined_text,
        metadata=metadata
    )