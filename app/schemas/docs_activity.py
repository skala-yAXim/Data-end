
from datetime import datetime
from typing import List
from pydantic import BaseModel

class DocsEntry(BaseModel):
  filename: str
  author: List[str]
  last_modified: datetime
  type: str
  size: int
  url: str