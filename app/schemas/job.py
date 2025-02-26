from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
import re


class JobSchema(BaseModel):
    id: str  # Changed to str type for MongoDB compatibility while maintaining UUID validation
    
    @field_validator('id')
    @classmethod
    def validate_uuid_format(cls, v):
        # Validate that the string is in UUID format
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        if not uuid_pattern.match(v):
            raise ValueError('id must be a valid UUID string format')
        return v
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
