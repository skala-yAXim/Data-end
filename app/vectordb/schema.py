
from datetime import datetime
from typing import Generic, TypeVar
from uuid import uuid4
from pydantic import BaseModel, Field

class BaseMetadata(BaseModel):
    pass

class TeamsPostMetadata(BaseMetadata):
  user_id: str
  date: datetime
  
M = TypeVar("M", bound=BaseMetadata)

class BaseRecord(BaseModel, Generic[M]):
  id: str = Field(default_factory=lambda: str(uuid4()))
  text: str
  metadata: M
  