# app/schemas/schemas.py

from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CompanySchema(BaseModel):
    company_id: int
    company_name: str

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class LocationSchema(BaseModel):
    location_id: int
    location: str

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class JobSchema(BaseModel):
    job_id: int
    title: str
    is_remote: Optional[bool] = None
    workplace_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    description: Optional[str] = None
    apply_link: Optional[str] = None
    company: CompanySchema
    location: LocationSchema

    class Config:
        from_attributes = True  # Updated for Pydantic v2

class JobsResponseSchema(BaseModel):
    jobs: List[JobSchema]

    class Config:
        from_attributes = True  # Updated for Pydantic v2
