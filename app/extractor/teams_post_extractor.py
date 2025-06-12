from typing import List, Union
from app.common.utils import clean_html
from app.schemas.teams_post_activity import PostEntry, ReplyEntry
from app.vectordb.schema import BaseRecord, TeamsPostMetadata

def create_record_from_post_entry(team_post: PostEntry) -> List[BaseRecord[TeamsPostMetadata]]:
    docs: List[BaseRecord[TeamsPostMetadata]] = []

    parsed = parse_post_data(team_post)

    record = BaseRecord[TeamsPostMetadata](
        text=parsed.text,
        metadata=TeamsPostMetadata(
            user_id=parsed.metadata.user_id,
            date=parsed.metadata.date
        )
    )
    docs.append(record)

    for reply in team_post.replies or []:
        parsed_reply = parse_post_data(
            data=reply,
            is_reply=True,
            post_content=team_post.content
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

    combined_text = "\n".join(text_parts).strip()

    metadata = TeamsPostMetadata(
        user_id=data.author,
        date=data.date
    )

    return BaseRecord[TeamsPostMetadata](
        text=combined_text,
        metadata=metadata
    )