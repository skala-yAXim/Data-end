from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class CommitEntry(BaseModel):
    repo: str
    sha: str
    message: Optional[str]
    date: datetime
    author: Optional[str]

class PullRequestEntry(BaseModel):
    repo: str
    number: int
    title: Optional[str]
    content: Optional[str]
    created_at: datetime
    state: str
    author: Optional[str]

class IssueEntry(BaseModel):
    repo: str
    number: int
    title: Optional[str]
    created_at: datetime
    state: str
    author: Optional[str]

class ReadmeInfo(BaseModel):
    name: str
    content: str
    html_url: str
    download_url: Optional[str]
