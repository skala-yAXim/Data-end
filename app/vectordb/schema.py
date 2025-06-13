
from datetime import datetime
from typing import Generic, List, TypeVar
from uuid import uuid4
from pydantic import BaseModel, Field

class BaseMetadata(BaseModel):
    pass

class TeamsPostMetadata(BaseMetadata):
  author: int
  type: str
  date: datetime

class DocumentMetadata(BaseMetadata):
  file_id: str
  filename: str
  author: List[int]
  last_modified: datetime
  type: str
  size: int
  chunk_id: int
  
class GitCommitMetadata(BaseMetadata):
  author: int
  date: datetime
  type: str
  repo_name: str
  sha: str

class GitPRMetadata(BaseMetadata):
  author: int
  date: datetime
  type: str
  repo_name: str
  number: int
  state: str
  
class GitIssueMetadata(BaseMetadata):
  author: int
  date: datetime
  type: str
  repo_name: str
  number: int

class EmailMetadata(BaseMetadata):
  author: int
  sender: str
  receivers: List[str]
  subject: str
  conversation_id: str
  date: datetime

class GitReadMeMetadata(BaseMetadata):
  repo_name: str
  html_url: str
  download_url: str
  
M = TypeVar("M", bound=BaseMetadata)

class BaseRecord(BaseModel, Generic[M]):
  id: str = Field(default_factory=lambda: str(uuid4()))
  text: str
  metadata: M