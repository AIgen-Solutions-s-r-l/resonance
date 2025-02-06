from typing import Dict, Any, Optional
from typing import List
from app.libs.job_matcher import JobMatcher
from app.core.config import settings
from app.core.mongodb import collection_name
from pymongo import ReturnDocument
from app.core.logging_config import get_logger_context
import loguru

from app.schemas.job import JobSchema
from app.schemas.location import LocationFilter

logger_context = get_logger_context()
logger = loguru.logger.bind(**logger_context)


async def get_resume_by_user_id(user_id: int, version: Optional[str] = None) -> Dict[str, Any]:
    try:
        query = {"user_id": user_id}
        if version:
            query["version"] = version

        resume = await collection_name.find_one(query)
        if not resume:
            logger.warning("Resume not found", extra={
                "event_type": "resume_not_found",
                "user_id": user_id,
                "version": version
            })
            return {"error": f"Resume not found for user ID: {user_id}"}

        resume["_id"] = str(resume["_id"])

        logger.info("Resume retrieved", extra={
            "event_type": "resume_retrieved",
            "user_id": user_id,
            "version": version
        })
        return resume

    except Exception as e:
        logger.error(f"Error retrieving resume: {str(e)}", extra={
            "event_type": "resume_retrieval_error",
            "user_id": user_id,
            "version": version,
            "error_type": type(e).__name__,
            "error_details": str(e)
        })
        return {"error": f"Error retrieving resume: {str(e)}"}


async def match_jobs_with_resume(
    resume: Dict[str, Any],
    location: Optional[LocationFilter] = None,
    keywords: Optional[List[str]] = None,
    save_to_mongodb: bool = False,
    offset: int = 0
) -> List[JobSchema]:
    try:
        matcher = JobMatcher()
        
        matched_jobs = await matcher.process_job(
            resume,
            location=location,
            keywords=keywords,
            save_to_mongodb=save_to_mongodb,
            offset=offset
        )
        return matched_jobs
    except Exception as e:
        raise Exception("Failed to match jobs with resume.") from e