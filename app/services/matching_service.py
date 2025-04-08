from typing import Dict, Any, Optional
from typing import List
from app.libs.job_matcher_optimized import OptimizedJobMatcher
from app.core.mongodb import collection_name
from app.log.logging import logger
from app.schemas.job import JobSchema
from app.schemas.location import LocationFilter


async def get_resume_by_user_id(
    user_id: int, version: Optional[str] = None
) -> Dict[str, Any]:
    try:
        query = {"user_id": user_id}
        if version:
            query["version"] = version

        resume = await collection_name.find_one(query)
        if not resume:
            logger.warning(
                "Resume not found",
                event_type="resume_not_found",
                user_id=user_id,
                version=version,
            )
            return {"error": f"Resume not found for user ID: {user_id}"}

        resume["_id"] = str(resume["_id"])

        logger.info(
            "Resume retrieved",
            event_type="resume_retrieved",
            user_id=user_id,
            version=version,
        )
        return resume

    except Exception as e:
        logger.exception(
            "Error retrieving resume",
            event_type="resume_retrieval_error",
            user_id=user_id,
            version=version,
            error_type=type(e).__name__,
            error_details=str(e),
        )
        return {"error": "Error retrieving resume"}

async def match_jobs_with_resume(
    resume: Dict[str, Any],
    location: Optional[LocationFilter] = None,
    keywords: Optional[List[str]] = None,
    save_to_mongodb: bool = False,
    offset: int = 0,
    experience: Optional[List[str]] = None,
    include_total_count: bool = False,
    radius: Optional[int] = None,
) -> Dict[str, Any]:
    try:
        matcher = OptimizedJobMatcher()
        
        # If location is provided and resume has geolocation data, add it to the location filter
        if location is None:
            location = LocationFilter()
        
        # Check if resume has geolocation data from legacy matching
        if resume and "latitude" in resume and "longitude" in resume:
            location.legacy_latitude = resume.get("latitude")
            location.legacy_longitude = resume.get("longitude")
            
            # If radius is provided, use it
            if radius is not None:
                location.radius = radius
        
        matched_jobs = await matcher.process_job(
            resume,
            location=location,
            keywords=keywords,
            save_to_mongodb=save_to_mongodb,
            offset=offset,
            experience=experience,
            include_total_count=include_total_count,
        )
        return matched_jobs
    except Exception as e:
        logger.exception(
            "Error matching jobs with resume",
            event_type="job_matching_error",
            error_type=type(e).__name__,
            error_details=str(e),
        )
        raise Exception("Failed to match jobs with resume.") from e
