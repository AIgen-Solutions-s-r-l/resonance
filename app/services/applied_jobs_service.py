"""
Service for interacting with applied jobs collection.

This service provides functionality to check and retrieve jobs that users have already applied for.
"""

from typing import List, Optional
from app.core.mongodb import database
from app.log.logging import logger


class AppliedJobsService:
    """Service for interacting with applied jobs collection."""

    @staticmethod
    async def get_applied_jobs(user_id: int) -> List[str]:
        """
        Get list of job IDs that the user has already applied for.
        
        Args:
            user_id: The user ID
            
        Returns:
            List of job IDs
        """
        try:
            collection = database.get_collection("already_applied_jobs")
            cursor = collection.find({"user_id": user_id})
            documents = await cursor.to_list(length=None)
            
            # Extract job_ids from each document and flatten into a single list.
            applied_job_ids = []
            for doc in documents:
                job_ids = doc.get("job_ids", [])
                if job_ids:
                    applied_job_ids.extend(job_ids)
            
            logger.info(
                "Retrieved applied jobs for user {user_id} with count {count}",
                user_id=user_id,
                count=len(applied_job_ids)
            )
            
            return applied_job_ids
        except Exception as e:
            logger.exception(
                "Error retrieving applied jobs for user {user_id} with error {error_type} {error}",
                user_id=user_id,
                error_type=type(e).__name__,
                error=str(e)
            )
            return []

    @staticmethod
    async def is_job_applied(user_id: int, job_id: str) -> bool:
        """
        Check if a user has already applied for a specific job.
        
        Args:
            user_id: The user ID
            job_id: The job ID
            
        Returns:
            True if the user has applied for the job, False otherwise
        """
        try:
            collection = database.get_collection("already_applied_jobs")
            document = await collection.find_one({"user_id": user_id, "job_id": job_id})
            return document is not None
        except Exception as e:
            logger.exception(
                "Error checking if job is applied",
                user_id=user_id,
                job_id=job_id,
                error_type=type(e).__name__,
                error=str(e)
            )
            return False


# Create a singleton instance
applied_jobs_service = AppliedJobsService()