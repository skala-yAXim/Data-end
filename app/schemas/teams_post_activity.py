
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

class ReplyEntry(BaseModel):
  author: int
  content: str
  date: datetime
  attachments: Optional[List[str]]

class PostEntry(BaseModel):
  author: int
  subject: str
  summary: str
  content: str
  replies: Optional[List[ReplyEntry]]
  attachments: Optional[List[str]]
  application_content: Optional[List[str]]
  date: datetime
