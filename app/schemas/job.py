from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobSchema(BaseModel):
    id: int
    title: str
    is_remote: Optional[bool] = None
    workplace_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    description: Optional[str] = None
    apply_link: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    portal: Optional[str] = None

    class Config:
        from_attributes = True  # Updated for Pydantic v2


