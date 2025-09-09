from pydantic import BaseModel, Field
from typing import Optional


class LocationFilter(BaseModel):
    country: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_km: Optional[float] = 30.0
