from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class JobSchema(BaseModel):
    id: str
    job_id: str
    title: str
    is_remote: Optional[bool] = None
    location_strict: Optional[bool] = None
    workplace_type: Optional[str] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    description: Optional[str] = None
    apply_link: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    portal: Optional[str] = None
    company_id: Optional[int] = None
    location_id: Optional[int] = None
    cluster_id: Optional[int] = None
    embedding: Optional[List[float]] = None
    short_description: Optional[str] = None
    processed_description: Optional[str] = None
    field: Optional[str] = None
    experience: Optional[str] = None
    skills_required: Optional[List[str]] = None
    sparse_embeddings: Optional[List[float]] = None

    class Config:
        from_attributes = True
