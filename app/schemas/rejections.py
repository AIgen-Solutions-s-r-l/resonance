from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class PassJobIn(BaseModel):
    job_id: str = Field(..., min_length=1)

class UndoJobIn(BaseModel):
    job_id: str = Field(..., min_length=1)

class RejectedItem(BaseModel):
    job_id: str
    timestamp: datetime

class RejectedListOut(BaseModel):
    items: List[RejectedItem]
    count: int

class StatusOut(BaseModel):
    job_id: str
    is_rejected: bool
