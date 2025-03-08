"""
Task management schemas for asynchronous job processing.
"""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"


class TaskCreationResponse(BaseModel):
    """Response model for task creation."""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: TaskStatus = Field(..., description="Current status of the task")
    created_at: datetime = Field(..., description="Task creation timestamp")


class TaskStatusResponse(BaseModel):
    """Response model for task status check."""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: TaskStatus = Field(..., description="Current status of the task")
    result: Optional[Dict[str, Any]] = Field(None, description="Task result if completed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last status update timestamp")
    
    class Config:
        """Pydantic model configuration."""
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ErrorDetail(BaseModel):
    """Error details for failed tasks."""
    error: str = Field(..., description="Error message")
    error_type: Optional[str] = Field(None, description="Type of error")


class TaskError(BaseModel):
    """Response model for task errors."""
    detail: ErrorDetail = Field(..., description="Error details")