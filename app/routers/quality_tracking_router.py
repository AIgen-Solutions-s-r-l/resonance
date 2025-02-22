"""
FastAPI router for quality tracking endpoints.

This module provides API endpoints for accessing and managing quality tracking
data, following RESTful principles and providing comprehensive documentation.
"""
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from app.core.database import get_session
from app.services.quality_evaluation_service import OpenAIQualityEvaluator
from app.repositories.quality_tracking_repository import QualityTrackingRepository
from app.services.metrics_tracking_service import QualityMetricsTracker
from app.log.logging import logger


# Pydantic models for request/response
class QualityScoreResponse(BaseModel):
    """Response model for quality scores."""
    evaluation_id: UUID
    resume_id: str
    job_id: str
    match_score: float
    quality_score: float
    skill_alignment_score: float
    experience_match_score: float
    evaluation_text: str
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackRequest(BaseModel):
    """Request model for submitting feedback."""
    feedback_score: float = Field(..., ge=0, le=100)
    feedback_text: Optional[str] = None
    reviewer: str


class MetricResponse(BaseModel):
    """Response model for metric data."""
    metric_name: str
    metric_value: float
    recorded_at: datetime


class AggregatedMetrics(BaseModel):
    """Response model for aggregated metrics."""
    count: int
    average: float
    min: float
    max: float
    std_dev: float


# Router setup
router = APIRouter(
    prefix="/quality-tracking",
    tags=["quality-tracking"],
    responses={404: {"description": "Not found"}}
)


# Dependency for service initialization
async def get_quality_services(
    session: AsyncSession = Depends(get_session)
):
    """Initialize and return quality tracking services."""
    repository = QualityTrackingRepository(session)
    metrics_tracker = QualityMetricsTracker(session)
    evaluator = OpenAIQualityEvaluator(repository, metrics_tracker)
    return evaluator, repository, metrics_tracker


@router.post(
    "/evaluate/{resume_id}/{job_id}",
    response_model=QualityScoreResponse,
    summary="Evaluate a resume-job match"
)
async def evaluate_match(
    resume_id: str,
    job_id: str,
    services: tuple = Depends(get_quality_services)
):
    """
    Evaluate the quality of a match between a resume and job.
    
    Args:
        resume_id: ID of the resume
        job_id: ID of the job
        services: Tuple of (evaluator, repository, metrics_tracker)
    
    Returns:
        Quality evaluation results
    """
    evaluator, _, _ = services
    
    try:
        # Get resume and job data
        from app.services.matching_service import get_resume_by_user_id
        from app.models.job import Job
        
        resume = await get_resume_by_user_id(resume_id)
        if "error" in resume:
            raise HTTPException(status_code=404, detail=f"Resume not found: {resume_id}")
        
        job_query = select(Job).where(Job.id == job_id)
        job_result = await services[0].session.execute(job_query)
        job = job_result.scalar_one_or_none()
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        
        # Perform evaluation
        evaluation = await evaluator.evaluate_match(resume, job.dict())
        
        logger.info(
            "Match evaluation completed via API",
            resume_id=resume_id,
            job_id=job_id,
            quality_score=evaluation.quality_score
        )
        
        return evaluation
        
    except Exception as e:
        logger.error(
            "Match evaluation failed via API",
            error=str(e),
            error_type=type(e).__name__,
            resume_id=resume_id,
            job_id=job_id
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to evaluate match: {str(e)}"
        )


@router.get(
    "/evaluations/{evaluation_id}",
    response_model=QualityScoreResponse,
    summary="Get evaluation details"
)
async def get_evaluation(
    evaluation_id: UUID,
    services: tuple = Depends(get_quality_services)
):
    """
    Retrieve details of a specific quality evaluation.
    
    Args:
        evaluation_id: ID of the evaluation to retrieve
        services: Tuple of (evaluator, repository, metrics_tracker)
    
    Returns:
        Quality evaluation details
    """
    _, repository, _ = services
    
    try:
        evaluation = await repository.get_by_id(evaluation_id)
        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation not found: {evaluation_id}"
            )
        
        return evaluation
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to retrieve evaluation",
            error=str(e),
            error_type=type(e).__name__,
            evaluation_id=str(evaluation_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve evaluation: {str(e)}"
        )


@router.post(
    "/evaluations/{evaluation_id}/feedback",
    status_code=201,
    summary="Submit feedback for an evaluation"
)
async def submit_feedback(
    evaluation_id: UUID,
    feedback: FeedbackRequest,
    services: tuple = Depends(get_quality_services)
):
    """
    Submit feedback for a quality evaluation.
    
    Args:
        evaluation_id: ID of the evaluation
        feedback: Feedback data
        services: Tuple of (evaluator, repository, metrics_tracker)
    """
    _, repository, _ = services
    
    try:
        evaluation = await repository.get_by_id(evaluation_id)
        if not evaluation:
            raise HTTPException(
                status_code=404,
                detail=f"Evaluation not found: {evaluation_id}"
            )
        
        from app.models.quality_tracking import ManualFeedback
        
        feedback_entry = ManualFeedback(
            evaluation_id=evaluation_id,
            feedback_score=feedback.feedback_score,
            feedback_text=feedback.feedback_text,
            reviewer=feedback.reviewer
        )
        
        evaluation.feedback.append(feedback_entry)
        await repository.update(evaluation)
        
        logger.info(
            "Feedback submitted",
            evaluation_id=str(evaluation_id),
            reviewer=feedback.reviewer
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Failed to submit feedback",
            error=str(e),
            error_type=type(e).__name__,
            evaluation_id=str(evaluation_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get(
    "/metrics/{evaluation_id}",
    response_model=List[MetricResponse],
    summary="Get metrics for an evaluation"
)
async def get_evaluation_metrics(
    evaluation_id: UUID,
    metric_name: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    services: tuple = Depends(get_quality_services)
):
    """
    Retrieve metrics for a specific evaluation.
    
    Args:
        evaluation_id: ID of the evaluation
        metric_name: Optional name of specific metric to retrieve
        start_time: Optional start time filter
        end_time: Optional end time filter
        services: Tuple of (evaluator, repository, metrics_tracker)
    
    Returns:
        List of metrics
    """
    _, _, metrics_tracker = services
    
    try:
        metrics = await metrics_tracker.get_metric_history(
            evaluation_id,
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time
        )
        
        return metrics
        
    except Exception as e:
        logger.error(
            "Failed to retrieve metrics",
            error=str(e),
            error_type=type(e).__name__,
            evaluation_id=str(evaluation_id)
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve metrics: {str(e)}"
        )


@router.get(
    "/metrics/aggregated/{metric_name}",
    response_model=Dict[str, AggregatedMetrics],
    summary="Get aggregated metrics"
)
async def get_aggregated_metrics(
    metric_name: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    group_by: Optional[str] = Query(None, description="Field to group metrics by"),
    services: tuple = Depends(get_quality_services)
):
    """
    Retrieve aggregated metrics across all evaluations.
    
    Args:
        metric_name: Name of the metric to aggregate
        start_time: Optional start time filter
        end_time: Optional end time filter
        group_by: Optional field to group results by
        services: Tuple of (evaluator, repository, metrics_tracker)
    
    Returns:
        Aggregated metrics
    """
    _, _, metrics_tracker = services
    
    try:
        aggregated = await metrics_tracker.get_aggregated_metrics(
            metric_name,
            start_time=start_time,
            end_time=end_time,
            group_by=group_by
        )
        
        return aggregated
        
    except Exception as e:
        logger.error(
            "Failed to retrieve aggregated metrics",
            error=str(e),
            error_type=type(e).__name__,
            metric_name=metric_name
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve aggregated metrics: {str(e)}"
        )