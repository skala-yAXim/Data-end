
from datetime import datetime
from typing import List
from pydantic import BaseModel

class DocsEntry(BaseModel):
  file_id: str
  filename: str
  full_path: str
  author: List[int]
  last_modified: datetime
  type: str
  size: int
  drive_id: str