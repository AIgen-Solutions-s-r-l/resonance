"""
Models for job matching functionality.

This module contains data models used for job matching operations.
"""

from dataclasses import dataclass
from typing import List, Optional, Set
from datetime import datetime


@dataclass
class JobMatch:
    """Data class for job matching results, aligned with JobSchema."""
    
    id: str
    title: str
    description: Optional[str] = None
    workplace_type: Optional[str] = None
    short_description: Optional[str] = None
    field: Optional[str] = None
    experience: Optional[str] = None
    skills_required: Optional[List[str]] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    portal: Optional[str] = None
    score: Optional[float] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    apply_link: Optional[str] = None
    location: Optional[str] = None
    root_fields: Optional[Set[str]] = None
    sub_fields: Optional[Set[str]] = None
    
    def to_dict(self) -> dict:
        """Convert JobMatch to dictionary format."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "workplace_type": self.workplace_type,
            "short_description": self.short_description,
            "field": self.field,
            "experience": self.experience,
            "skills_required": self.skills_required,
            "country": self.country,
            "city": self.city,
            "company_name": self.company_name,
            "company_logo": self.company_logo,
            "score": self.score,
            "posted_date": self.posted_date,
            "job_state": self.job_state,
            "apply_link": self.apply_link,
            "portal": self.portal,
            "location": self.location,
            "root_fields": self.root_fields,
            "sub_fields": self.sub_fields,
        }