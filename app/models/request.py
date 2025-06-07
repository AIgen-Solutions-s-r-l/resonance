from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class SearchRequest(BaseModel):
    user_id: int
    time: datetime
    location: Optional[List[float]] = None
    keywords: Optional[List[str]] = None