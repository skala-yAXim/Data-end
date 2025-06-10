from app.schemas.email_activity import EmailEntry
from app.vectordb.schema import BaseRecord, EmailMetadata


def extract_email_content(email: EmailEntry, user_info: dict[str, int]) -> BaseRecord[EmailMetadata]:
    attachments_text = ", ".join(email.attachment_list) if email.attachment_list else "None"
    combined_text = f"Content: {email.content.strip()}\nAttachments: {attachments_text}"
    
    return BaseRecord[EmailMetadata](
        text=combined_text,
        metadata=EmailMetadata(
            author=user_info.get(email.author, 0),
            sender=email.sender,
            receiver=email.receiver,
            subject=email.subject,
            date=email.date,
            conversation_id=email.conversation_id
        )
    )