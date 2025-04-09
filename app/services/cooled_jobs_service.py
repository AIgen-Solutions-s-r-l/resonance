"""
Service for interacting with cooled jobs collection.

This service provides functionality to retrieve jobs that are in the cooling period.
"""

from typing import List
from app.core.mongodb import database
from app.log.logging import logger


class CooledJobsService:
    """Service for interacting with cooled jobs collection."""

    @staticmethod
    async def get_cooled_jobs() -> List[str]:
        """
        Get list of job IDs that are in the cooling period.
        
        Returns:
            List of job IDs
        """
        try:
            collection = database.get_collection("cooled_jobs")
            cursor = collection.find({})
            documents = await cursor.to_list(length=None)
            
            # Extract job_ids from each document
            cooled_job_ids = []
            for doc in documents:
                job_id = doc.get("job_id")
                if job_id:
                    cooled_job_ids.append(job_id)
            
            logger.info(
                "Retrieved cooled jobs with count {count}",
                count=len(cooled_job_ids)
            )
            
            return cooled_job_ids
        except Exception as e:
            logger.exception(
                "Error retrieving cooled jobs with error {error_type} {error}",
                error_type=type(e).__name__,
                error=str(e)
            )
            return []


# Create a singleton instance
cooled_jobs_service = CooledJobsService()