"""
Asynchronous job matching router with non-blocking API endpoints.

This router provides endpoints for matching jobs with resumes using
a non-blocking asynchronous approach for better performance and scalability.
"""

from typing import List, Any, Optional, Union
from fastapi import APIRouter, HTTPException, Depends, status, Query, Path, BackgroundTasks
from datetime import datetime, UTC
from sqlalchemy import select
import re
import uuid


from app.core.auth import get_current_user, verify_api_key
from app.schemas.job import JobSchema, JobDetailResponse
from app.schemas.job_match import JobsMatchedResponse
from app.models.job import Job
from app.utils.db_utils import get_db_cursor
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
        None, description="Filter jobs within the radius in kilometers"
    ),
    radius: Optional[int] = Query(
        None, description="Filter jobs within the radius in meters (for geographic matching)"
    ),
    keywords: Optional[List[str]] = Query(
        None,
        description="Filter jobs containing any of these keywords in the title or description. Multiple keywords will be treated as a single phrase.",
    ),
    offset: Optional[int] = Query(0, description="Get further jobs"),
    experience: Optional[List[str]] = Query(
        None, description="Filter jobs by experience level. Allowed values: Entry-level, Executive-level, Intern, Mid-level, Senior-level"
    ),
    is_remote_only: Optional[bool] = Query(None, description="Filter jobs that are remote only"),
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
            experience=experience,
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
        
        # Preprocess keywords: concatenate multiple keywords into a single string with spaces
        processed_keywords = None
        if keywords and len(keywords) > 0:
            processed_keywords = [" ".join(keywords)]
            logger.info(
                "Preprocessed keywords for user {current_user}: {original} -> {processed}",
                current_user=current_user,
                original=keywords,
                processed=processed_keywords,
            )
        
        # Process the task in the background
        background_tasks.add_task(
            TaskManager.process_job_matching,
            task_id,
            resume,
            location_filter,
            processed_keywords,
            offset if offset is not None else 0,
            experience,
            radius,
            is_remote_only, # Pass the new parameter
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
                task_status, result = await TaskManager.get_task_status(task_id)
                
                if task_status == TaskStatus.COMPLETED and result:
                    # Return the actual results instead of the task
                    if isinstance(result, dict) and "jobs" in result:
                        job_list = result["jobs"]
                        job_pydantic_list = [JobSchema.model_validate(job) for job in job_list]
                        return job_pydantic_list
                
                if task_status in (TaskStatus.FAILED, TaskStatus.EXPIRED):
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


# Legacy endpoint for backward compatibility - returns jobs with total count for pagination
@router.get(
    "/match/legacy",
    response_model=JobsMatchedResponse,
    summary="Get Jobs Matching User's Resume (Legacy)",
    description="Returns a list of jobs that match the authenticated user's resume along with total count for pagination.",
    status_code=status.HTTP_200_OK,
    deprecated=False,
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
        None, description="Filter jobs within the radius in kilometers"
    ),
    radius: Optional[int] = Query(
        None, description="Filter jobs within the radius in meters (for geographic matching)"
    ),
    keywords: Optional[List[str]] = Query(
        None,
        description="Filter jobs containing any of these keywords in the title or description. Multiple keywords will be treated as a single phrase.",
    ),
    offset: Optional[int] = Query(0, description="Get further jobs"),
    experience: Optional[List[str]] = Query(
        None, description="Filter jobs by experience level. Allowed values: Entry-level, Executive-level, Intern, Mid-level, Senior-level"
    ),
    is_remote_only: Optional[bool] = Query(None, description="Filter jobs that are remote only"),
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
            experience=experience,
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

        # Preprocess keywords: concatenate multiple keywords into a single string with spaces
        processed_keywords = None
        if keywords and len(keywords) > 0:
            processed_keywords = [" ".join(keywords)]
            logger.info(
                "Preprocessed keywords for user {current_user}: {original} -> {processed}",
                current_user=current_user,
                original=keywords,
                processed=processed_keywords,
            )
            
        matched_jobs = await match_jobs_with_resume(
            resume,
            location=location_filter,
            keywords=processed_keywords,
            offset=offset if offset is not None else 0,
            experience=experience,
            include_total_count=True,  # Request total count for pagination
            radius=radius,
            is_remote_only=is_remote_only, # Pass the new parameter
        )

        if not isinstance(matched_jobs, dict):
            logger.exception("Unexpected data structure for matched_jobs")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid data structure for matched jobs.",
            )

        # Extract jobs list
        job_list = matched_jobs.get("jobs", [])
        
        # Extract total count (or use length of results if not available)
        total_count = matched_jobs.get("total_count", len(job_list))

        job_count = len(job_list)
        logger.info(
            "Found {job_count} jobs matched for user {current_user} (total: {total_count})",
            job_count=job_count,
            total_count=total_count,
            current_user=current_user,
        )

        job_pydantic_list = [JobSchema.model_validate(job) for job in job_list]

        # Return the new response model with both jobs and total count
        return JobsMatchedResponse(
            jobs=job_pydantic_list,
            total_count=total_count
        )

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
    "/details",
    response_model=JobDetailResponse,
    summary="Get Detailed Job Information by IDs",
    description="Returns detailed information for multiple jobs by their IDs",
    status_code=status.HTTP_200_OK,
)
async def get_jobs_by_ids(
    job_ids: Optional[List[str]] = Query(None, description="List of job IDs to retrieve"),
    _: bool = Depends(verify_api_key),
):
    """
    Get detailed information for multiple jobs by their IDs.
    
    Args:
        job_ids: List of job IDs to retrieve
        _: API key verification dependency
        
    Returns:
        A structured response with job details
    """
    if not job_ids:
        return JobDetailResponse(
            jobs=[],
            count=0,
            status="success"
        )
    
    # Filter invalid UUIDs
    uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
    valid_job_ids = [job_id for job_id in job_ids if uuid_pattern.match(job_id)]
    
    if len(valid_job_ids) < len(job_ids):
        logger.warning(
            "Filtered {filtered_count} invalid job IDs",
            filtered_count=len(job_ids) - len(valid_job_ids)
        )
    
    if not valid_job_ids:
        return JobDetailResponse(
            jobs=[],
            count=0,
            status="success"
        )
    
    try:
        logger.info(
            "Retrieving job details for {count} IDs",
            count=len(valid_job_ids)
        )
        
        # Get database cursor
        async with get_db_cursor() as cursor:
            # Build the query to get full job details including related data
            query = """
            SELECT
                j.id,
                j.title,
                j.description,
                j.workplace_type,
                j.short_description,
                j.field,
                j.experience,
                j.skills_required,
                j.posted_date,
                j.job_state,
                j.apply_link,
                j.portal,
                l.city || ', ' || co.country_name AS location,
                c.company_name,
                c.logo AS company_logo
            FROM "Jobs" j
            LEFT JOIN "Companies" c ON j.company_id = c.company_id
            LEFT JOIN "Locations" l ON j.location_id = l.location_id
            LEFT JOIN "Countries" co ON l.country = co.country_id
            WHERE j.id = ANY(%s)
            """
                
            # Execute the query with validated IDs only
            await cursor.execute(query, (valid_job_ids,))
            
            # Fetch all results
            jobs = await cursor.fetchall()
            
            # Process jobs to convert UUIDs to strings
            processed_jobs = []
            for job in jobs:
                # Convert UUID to string if needed
                if isinstance(job['id'], uuid.UUID):
                    job['id'] = str(job['id'])
                processed_jobs.append(job)
            
            # Convert database results to Pydantic models
            job_schemas = [JobSchema.model_validate(job) for job in processed_jobs]
            
            # Create the response
            return JobDetailResponse(
                jobs=job_schemas,
                count=len(job_schemas),
                status="success"
            )
    except Exception as e:
        logger.exception(
            "Error retrieving jobs by IDs",
            error=str(e),
            job_ids=job_ids
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving job details"
        )
