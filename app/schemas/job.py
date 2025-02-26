from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from uuid import UUID


class JobSchema(BaseModel):
    id: UUID  # Using UUID type for validation while database stores string representation
    title: str
    workplace_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    description: Optional[str] = None
    apply_link: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    portal: Optional[str] = None
    short_description: Optional[str] = None
    field: Optional[str] = None
    experience: Optional[str] = None
    score: Optional[float] = None
    skills_required: Optional[List[str]] = None

    class Config:
        from_attributes = True
