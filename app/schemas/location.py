from pydantic import BaseModel

class LocationFilter(BaseModel):
    country: str | None = None,
    city: str | None = None