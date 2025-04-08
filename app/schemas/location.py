from pydantic import BaseModel, Field
from typing import Optional


class LocationFilter(BaseModel):
    country: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    radius_km: float = 10.0  # Default to 10 km
    
    # Legacy matching fields
    legacy_latitude: Optional[float] = Field(None, description="Latitude from legacy matching")
    legacy_longitude: Optional[float] = Field(None, description="Longitude from legacy matching")
    radius: Optional[int] = Field(None, description="Radius in meters for geographic search")
