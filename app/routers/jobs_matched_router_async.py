"""
Asynchronous job matching router with non-blocking API endpoints.

This router provides endpoints for matching jobs with resumes using
a non-blocking asynchronous approach for better performance and scalability.
"""

from typing import List, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, status, Query, Path, BackgroundTasks
from datetime import datetime, UTC

from app.core.auth import get_current_user
from app.schemas.job import JobSchema
from app.schemas.task import TaskCreationResponse, TaskStatusResponse, TaskStatus
from app.schemas.location import LocationFilter
from app.services.matching_service import get_resume_by_user_id, match_jobs_with_resume
from app.tasks.job_processor import TaskManager
from app.log.logging import logger


router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        404: {"description": "Task not found"},
        500: {"description": "Internal server error"},
    },
)


@router.post(
    "/match",
    response_model=TaskCreationResponse,
    summary="Start Job Matching Process",
    description="Starts the job matching process and returns a task ID for polling results.",
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_job_matching(
    background_tasks: BackgroundTasks,
    country: Optional[str] = Query(
        None, description="Filter jobs by country (hard filter)"
    ),
    city: Optional[str] = Query(None, description="Filter jobs by city (hard filter)"),
    latitude: Optional[float] = Query(
        None, description="Filter jobs by latitude (soft filter)"
    ),
    longitude: Optional[float] = Query(
        None, description="Filter jobs by longitude (soft filter)"
    ),
    radius_km: Optional[float] = Query(
        None, description="Filter jobs within the radius"
    ),
    keywords: Optional[List[str]] = Query(
        None,
        description="Filter jobs containing any of these keywords in the title or description",
    ),
    offset: Optional[int] = Query(0, description="Get further jobs"),
    wait: bool = Query(False, description="Wait for results (not recommended for production use)"),
    current_user: Any = Depends(get_current_user),
):
    """
    Start the job matching process asynchronously.
    
    This endpoint initiates the matching process but returns immediately with a task ID.
    Clients should then poll the /match/status/{task_id} endpoint to get results.
    
    Args:
        background_tasks: FastAPI background tasks
        country: Optional country filter
        city: Optional city filter
        latitude: Optional latitude for geographical filtering
        longitude: Optional longitude for geographical filtering
        radius_km: Optional radius for geographical filtering
        keywords: Optional keyword filters
        offset: Results offset
        wait: If True, wait for results (not recommended for production)
        current_user: The authenticated user
        
    Returns:
        A task creation response with task ID for polling
    """
    try:
        location_filter = LocationFilter(
            country=country,
            city=city,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km if radius_km is not None else 20.0,
        )

        logger.info(
            "User {current_user} is requesting async job matching",
            current_user=current_user,
            location_filter=location_filter,
            keywords=keywords,
        )

        # Get the resume
        resume = await get_resume_by_user_id(current_user)
        if not resume or "error" in resume:
            logger.error(
                "Resume not found for user {current_user}", current_user=current_user
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found for the current user.",
            )

        # Create a task ID
        task_id = await TaskManager.create_task()
        
        # Process the task in the background
        background_tasks.add_task(
            TaskManager.process_job_matching,
            task_id,
            resume,
            location_filter,
            keywords,
            offset if offset is not None else 0,
        )
        
        # Create response
        response = TaskCreationResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            created_at=datetime.now(UTC),
        )
        
        # If wait=True, poll for results (not recommended for production)
        if wait:
            # Only for backward compatibility and testing
            # This defeats the purpose of async processing but maintains compatibility
            # Wait up to 3 minutes for results
            import asyncio
            max_attempts = 36  # 3 minutes (5 seconds * 36)
            for _ in range(max_attempts):
                await asyncio.sleep(5)  # Check every 5 seconds
                status, result = await TaskManager.get_task_status(task_id)
                
                if status == TaskStatus.COMPLETED and result:
                    # Return the actual results instead of the task
                    if isinstance(result, dict) and "jobs" in result:
                        job_list = result["jobs"]
                        job_pydantic_list = [JobSchema.model_validate(job) for job in job_list]
                        return job_pydantic_list
                
                if status in (TaskStatus.FAILED, TaskStatus.EXPIRED):
                    # Task failed or expired
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail="Job matching process failed.",
                    )
            
            # Timed out
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail="Job matching process timed out.",
            )
        
        return response

    except HTTPException:
        raise
    except ValueError as e:
        logger.exception("Validation error for user {current_user}", current_user=current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "Unexpected error for user {current_user}",
            current_user=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


@router.get(
    "/match/status/{task_id}",
    response_model=Union[TaskStatusResponse, List[JobSchema]],
    summary="Check Job Matching Status",
    description="Check the status of a job matching task and retrieve results if available.",
    status_code=status.HTTP_200_OK,
)
async def get_job_matching_status(
    task_id: str = Path(..., description="Task ID from the job matching request"),
    current_user: Any = Depends(get_current_user),
):
    """
    Check the status of a job matching task.
    
    Args:
        task_id: The ID of the task to check
        current_user: The authenticated user
        
    Returns:
        Task status and results if available
    """
    try:
        logger.info(
            "User {current_user} is checking task status for {task_id}",
            current_user=current_user,
            task_id=task_id,
        )
        
        # Get task status
        status_value, result = await TaskManager.get_task_status(task_id)
        
        if status_value is None:
            logger.error(
                "Task {task_id} not found for user {current_user}",
                task_id=task_id,
                current_user=current_user,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task {task_id} not found.",
            )
            
        # For completed tasks, if auto_return_results=True, return the job results directly
        auto_return_results = True  # This could be a query parameter in the future
        
        if status_value == TaskStatus.COMPLETED and result and auto_return_results:
            if isinstance(result, dict) and "jobs" in result:
                job_list = result["jobs"]
                job_count = len(job_list)
                
                logger.info(
                    "Found {job_count} jobs matched for user {current_user}",
                    job_count=job_count,
                    current_user=current_user,
                )
                
                job_pydantic_list = [JobSchema.model_validate(job) for job in job_list]
                return job_pydantic_list
        
        # Create a status response
        now = datetime.now(UTC)
        return TaskStatusResponse(
            task_id=task_id,
            status=status_value,
            result=result,
            created_at=now,  # Ideally would come from the task storage
            updated_at=now,  # Ideally would come from the task storage
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Unexpected error checking task status for user {current_user}",
            current_user=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )


# Legacy endpoint for backward compatibility - returns a list directly but processes asynchronously
@router.get(
    "/match/legacy",
    response_model=List[JobSchema],
    summary="Get Jobs Matching User's Resume (Legacy)",
    description="Returns a list of jobs that match the authenticated user's resume. This is a legacy endpoint.",
    status_code=status.HTTP_200_OK,
    deprecated=True,
)
async def get_matched_jobs_legacy(
    country: Optional[str] = Query(
        None, description="Filter jobs by country (hard filter)"
    ),
    city: Optional[str] = Query(None, description="Filter jobs by city (hard filter)"),
    latitude: Optional[float] = Query(
        None, description="Filter jobs by latitude (soft filter)"
    ),
    longitude: Optional[float] = Query(
        None, description="Filter jobs by longitude (soft filter)"
    ),
    radius_km: Optional[float] = Query(
        None, description="Filter jobs within the radius"
    ),
    keywords: Optional[List[str]] = Query(
        None,
        description="Filter jobs containing any of these keywords in the title or description",
    ),
    offset: Optional[int] = Query(0, description="Get further jobs"),
    current_user: Any = Depends(get_current_user),
):
    """
    Legacy endpoint to maintain backward compatibility.
    Uses the new async processing but waits for results before returning.
    """
    try:
        location_filter = LocationFilter(
            country=country,
            city=city,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius_km if radius_km is not None else 20.0,
        )

        logger.info(
            "User {current_user} is requesting matched jobs (legacy endpoint)",
            current_user=current_user,
            location_filter=location_filter,
            keywords=keywords,
        )

        resume = await get_resume_by_user_id(current_user)
        if not resume or "error" in resume:
            logger.error(
                "Resume not found for user {current_user}", current_user=current_user
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Resume not found for the current user.",
            )

        matched_jobs = await match_jobs_with_resume(
            resume,
            location=location_filter,
            keywords=keywords,
            offset=offset if offset is not None else 0,
        )

        if isinstance(matched_jobs, list):
            job_list = matched_jobs
        elif isinstance(matched_jobs, dict) and "jobs" in matched_jobs:
            job_list = matched_jobs["jobs"]
        else:
            logger.exception("Unexpected data structure for matched_jobs")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid data structure for matched jobs.",
            )

        job_count = len(job_list)
        logger.info(
            "Found {job_count} jobs matched for user {current_user}",
            job_count=job_count,
            current_user=current_user,
        )

        job_pydantic_list = [JobSchema.model_validate(job) for job in job_list]

        return job_pydantic_list

    except HTTPException:
        raise
    except ValueError as e:
        logger.exception("Validation error for user {current_user}", current_user=current_user)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception(
            "Unexpected error for user {current_user}",
            current_user=current_user,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )