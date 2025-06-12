from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CommitEntry(BaseModel):
    repo: str
    sha: str
    message: Optional[str]
    date: datetime
    author: Optional[int]

class PullRequestEntry(BaseModel):
    repo: str
    number: int
    title: Optional[str]
    content: Optional[str]
    created_at: datetime
    state: str
    author: Optional[int]

class IssueEntry(BaseModel):
    repo: str
    number: int
    title: Optional[str]
    created_at: datetime
    state: str
    author: Optional[int]

class ReadmeInfo(BaseModel):
    repo_name: str
    content: str
    html_url: str
    download_url: Optional[str]

class GitActivity(BaseModel):
    repo: str
    commits: Optional[List[CommitEntry]] = None
    pull_requests: Optional[List[PullRequestEntry]] = None
    issues: Optional[List[IssueEntry]] = None
    readme: Optional[ReadmeInfo] = None