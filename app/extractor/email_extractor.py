from sqlalchemy.orm import Session
from app.schemas.email_activity import EmailEntry
from app.vectordb.schema import BaseRecord, EmailMetadata
from typing import List
from app.common.utils import get_user_emails

def extract_email_content(email: EmailEntry, db: Session) -> BaseRecord[EmailMetadata]:
    attachments_text = ", ".join(email.attachment_list) if email.attachment_list else "None"
    combined_text = f"Content: {email.content.strip()}\nAttachments: {attachments_text}"

    user_info = get_user_emails(db)

    print(user_info, email.author)
    
    return BaseRecord[EmailMetadata](
        text=combined_text,
        metadata=EmailMetadata(
            author=user_info.get(email.author, 0),
            sender=email.sender,
            receivers=email.receivers,
            subject=email.subject,
            date=email.date,
            conversation_id=email.conversation_id
        )
    )

def get_receivers(emails: List[str], user_info: dict):
    receivers = []
    
    for email in emails:
        receivers.append(user_info.get(email, 0))

    return receivers