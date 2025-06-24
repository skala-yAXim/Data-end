from datetime import datetime
import json
from typing import List

from app.schemas.email_activity import EmailEntry
from app.schemas.github_activity import CommitEntry, IssueEntry, PullRequestEntry
from app.schemas.teams_post_activity import PostEntry, ReplyEntry
from app.vectordb.schema import BaseRecord, EmailMetadata


def load_commits_from_json(file_path: str) -> List[CommitEntry]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    commits = []
    for entry in data:
        commit = CommitEntry(
            repo=entry['repo'],
            sha=entry['sha'],
            message=entry.get('message'),
            date=datetime.fromisoformat(entry['date']),
            author=entry.get('author')
        )
        commits.append(commit)
    
    return commits

def load_pull_requests_from_json(file_path: str) -> List[PullRequestEntry]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    pull_requests = []
    for entry in data:
        pr = PullRequestEntry(
            repo=entry['repo'],
            number=entry['number'],
            title=entry.get('title'),
            content=entry.get('content'),
            created_at=datetime.fromisoformat(entry['created_at']),
            state=entry['state'],
            author=entry.get('author')
        )
        pull_requests.append(pr)
    
    return pull_requests

def load_issues_from_json(file_path: str) -> List[IssueEntry]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    issues = []
    for entry in data:
        issue = IssueEntry(
            repo=entry['repo'],
            number=entry['number'],
            title=entry.get('title'),
            created_at=datetime.fromisoformat(entry['created_at']),
            state=entry['state'],
            author=entry.get('author')
        )
        issues.append(issue)
    
    return issues

def load_emails_from_json(file_path: str) -> List[EmailEntry]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    emails = []
    for entry in data:
        email = EmailEntry(
            author=entry['author'],
            sender=entry['sender'],
            receivers=entry['receivers'],
            subject=entry['subject'],
            content=entry['content'],
            date=datetime.fromisoformat(entry['date']),
            conversation_id=entry.get('conversation_id'),
            attachment_list=entry.get('attachment_list')
        )
        emails.append(email)

    return emails

def extract_email_record(email: EmailEntry):
  attachments_text = ", ".join(email.attachment_list) if email.attachment_list else "None"
  combined_text = f"Content: {email.content.strip()}\nAttachments: {attachments_text}"
  
  return BaseRecord[EmailMetadata](
      text=combined_text,
      metadata=EmailMetadata(
          author=email.author,
          sender=email.sender,
          receivers=email.receivers,
          subject=email.subject,
          date=email.date,
          conversation_id=email.conversation_id
      )
  )

def load_posts_from_json(file_path: str) -> List[PostEntry]:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    posts = []
    for entry in data:
        # replies가 있을 경우 ReplyEntry 리스트로 변환
        replies = None
        if entry.get('replies'):
            replies = [
                ReplyEntry(
                    author=reply['author'],
                    content=reply['content'],
                    date=datetime.fromisoformat(reply['date']),
                    attachments=reply.get('attachments')
                )
                for reply in entry['replies']
            ]

        post = PostEntry(
            author=entry['author'],
            subject=entry['subject'],
            summary=entry['summary'],
            content=entry['content'],
            replies=replies,
            attachments=entry.get('attachments'),
            application_content=entry.get('application_content'),
            date=datetime.fromisoformat(entry['date'])
        )
        posts.append(post)

    return posts