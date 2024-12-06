# app/routes/jobs.py

from typing import List, Any
from fastapi import APIRouter, HTTPException, Depends, status
from app.core.auth import get_current_user
from app.core.config import Settings
from app.schemas.job import JobSchema
from app.services.matching_service import (
    get_resume_by_user_id,
    match_jobs_with_resume,
)
from app.core.logging_config import get_logger_context

import loguru

logger_context = get_logger_context()
logger = loguru.logger.bind(**logger_context)
settings = Settings()
router = APIRouter(
    prefix="/jobs",
    tags=["jobs"],
    responses={
        401: {"description": "Not authenticated"},
        403: {"description": "Not authorized"},
        500: {"description": "Internal server error"},
    },
)



@router.get(
    "/match",
    response_model=List[JobSchema],
    summary="Get Jobs Matching User's Resume",
    description="Returns a list of jobs that match the authenticated user's resume.",
    status_code=status.HTTP_200_OK,
)
async def get_matched_jobs(
    current_user: Any = Depends(get_current_user),
):
    """
    Endpoint to retrieve all jobs matched with the authenticated user's resume.

    - **current_user**: The authenticated user making the request.
    - **Returns**: A list of jobs that match the user's resume.
    """
    try:
        logger.info(f"User {current_user} is requesting matched jobs.")

        # Recupera il curriculum dell'utente
        resume = await get_resume_by_user_id(current_user)
        if not resume:
            logger.error(f"Resume not found for user {current_user}.")
            raise Exception("Resume not found for the current user.")

        # Abbina i lavori con il curriculum
        matched_jobs = await match_jobs_with_resume(resume,settings)


        
        if isinstance(matched_jobs, list):
            job_list = matched_jobs
        elif isinstance(matched_jobs, dict) and 'jobs' in matched_jobs:
            job_list = matched_jobs['jobs']
        else:
            logger.error("Unexpected data structure for matched_jobs.")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid data structure for matched jobs.",
            )
        
        job_count = len(job_list)
        logger.info(f"Found {job_count} jobs matched for user {current_user}.")

        # Converti gli oggetti ORM in schemi Pydantic
        job_pydantic_list = [JobSchema.from_orm(job) for job in job_list]

        return job_pydantic_list  # Per response_model=List[JobSchema]


    except Exception as e:
        logger.warning(str(e))
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(f"Error matching jobs for user {current_user}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while matching jobs.",
        )
    except Exception as e:
        logger.exception(f"Unexpected error for user {current_user}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
