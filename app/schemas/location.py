from pydantic import BaseModel, Field
from typing import Optional


class LocationFilter(BaseModel):
    country: str | None = None
    city: str | None = None
    latitude: float | None = Field(None, description="Latitude for geographic filtering of job listings")
    longitude: float | None = Field(None, description="Longitude for geographic filtering of job listings")
    radius_km: float = Field(10.0, description="Radius in kilometers for geographic filtering")
    radius: Optional[int] = Field(None, description="Radius in meters for geographic search (takes precedence over radius_km)")
