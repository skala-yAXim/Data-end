
from datetime import datetime
from typing import Generic, List, TypeVar
from uuid import uuid4
from pydantic import BaseModel, Field

class BaseMetadata(BaseModel):
    pass

class TeamsPostMetadata(BaseMetadata):
  user_id: str
  date: datetime

class DocumentMetadata(BaseMetadata):
  file_id: str
  filename: str
  author: List[str]
  last_modified: datetime
  type: str
  size: int
  
class GitCommitMetadata(BaseMetadata):
  author: str
  date: datetime
  type: str
  repo_name: str
  sha: str

class GitPRMetadata(BaseMetadata):
  author: str
  date: datetime
  type: str
  repo_name: str
  number: int
  state: str
  
class GitIssueMetadata(BaseMetadata):
  author: str
  date: datetime
  type: str
  repo_name: str
  number: int

class EmailMetadata(BaseMetadata):
  author: str
  sender: str
  receiver: str
  subject: str
  conversation_id: str
  date: datetime
  
M = TypeVar("M", bound=BaseMetadata)

class BaseRecord(BaseModel, Generic[M]):
  id: str = Field(default_factory=lambda: str(uuid4()))
  text: str
  metadata: M