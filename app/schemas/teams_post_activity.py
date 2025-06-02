
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel

class ReplyEntry(BaseModel):
  author: str
  content: str
  date: datetime
  attachments: Optional[List[str]]

class PostEntry(BaseModel):
  author: str
  subject: str
  summary: str
  content: str
  replies: Optional[List[ReplyEntry]]
  attachments: Optional[List[str]]
  date: datetime
  
class TeamPost(BaseModel):
  team_id: str
  team_name: str
  posts: Optional[List[PostEntry]]