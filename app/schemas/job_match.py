from enum import Enum
from typing import List
from pydantic import BaseModel
from app.schemas.job import JobSchema

class JobsMatchedResponse(BaseModel):
    """
    Response model for job matching endpoints.
    Includes both the list of matched jobs and the total count for pagination.
    """
    jobs: List[JobSchema]
    total_count: int

class SortType(Enum):
    SCORE = "matching_score"
    DATE = "date"
    RECOMMENDED = "recommended"