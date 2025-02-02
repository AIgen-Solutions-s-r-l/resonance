from pydantic import BaseModel

class LocationFilter(BaseModel):
    country: str | None = None,
    city: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
    radius_km: float