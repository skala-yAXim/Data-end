from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EmailEntry(BaseModel):
    author: int
    sender: str
    receivers: List[str]
    subject: str
    content: str
    date: datetime
    conversation_id: Optional[str]
    attachment_list: Optional[List[str]]
