from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobSchema(BaseModel):
    id: str  # Changed back to string to match existing UUID format in database
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
