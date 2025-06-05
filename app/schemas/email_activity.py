from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class EmailEntry(BaseModel):
    author: str
    sender: str
    receiver: str
    subject: str
    content: str
    date: datetime
    conversation_id: Optional[str]
    attachment_list: Optional[List[str]]
