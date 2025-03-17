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

    @field_validator("skills_required", mode="before")
    @classmethod
    def parse_skills_required(cls, value):
        # If it's already a list, just return it.
        if isinstance(value, list):
            return value
        if value is None:
            return []
        
        # Otherwise, assume it's a string like '{Excel,Word,"Power Point"}'
        # and parse it into a list of strings.
        
        # 1) Remove leading/trailing braces if any:
        value = value.strip()
        if value.startswith("{") and value.endswith("}"):
            value = value[1:-1]
        
        # 2) Now split on commas (or do something more robust if the data can contain commas inside quotes)
        # A quick approach:
        items = value.split(",")

        # 3) Clean quotes/spaces around each item
        items = [item.strip().strip('"') for item in items]

        return items

    class Config:
        from_attributes = True


class JobDetailResponse(BaseModel):
    """
    Response model for job details endpoint.
    Contains a list of jobs, count of jobs, and status.
    """
    jobs: List[JobSchema]
    count: int
    status: str
