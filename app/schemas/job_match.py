from enum import Enum
from typing import Any, List
from pydantic import BaseModel
from app.schemas.job import JobSchema

class ManyToManyFilter(BaseModel):
    relationship: str
    where_clause: str
    params: List[Any]

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


class Subfield(BaseModel):
    name: str
    id: int

class RootField(BaseModel):
    name: str
    subfields: List[Subfield] = []

class FieldsResponse(BaseModel):
    fields: List[RootField] = []