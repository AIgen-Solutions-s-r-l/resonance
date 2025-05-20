from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from typing import List
from app.libs.job_matcher_optimized import OptimizedJobMatcher
from app.core.mongodb import collection_name
from app.log.logging import logger
from app.core.config import settings
from app.schemas.job_match import SortType
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
    is_remote_only: Optional[bool] = None, # Add new parameter
    sort_type: SortType = SortType.RECOMMENDED
) -> Dict[str, Any]:
    try:
        matcher = OptimizedJobMatcher()
        
        # If location is provided, ensure it's properly configured
        if location is None:
            location = LocationFilter()
        
        # If frontend provided coordinates and radius, use them for geospatial filtering
        if location.latitude is not None and location.longitude is not None:
            # These are already set in the LocationFilter from the API parameters
            # If radius is provided separately, use it (in meters)
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
            is_remote_only=is_remote_only # Pass new parameter 
        )

        if offset % settings.CACHE_SIZE > (offset + settings.RETURNED_JOBS_SIZE) % settings.CACHE_SIZE:
            # Then we recieved something like 499 as offset. Should never happen, but users are assholes
            # so better be safe than sorry
            matched_jobs_overflow = await matcher.process_job(
                resume,
                location=location,
                keywords=keywords,
                save_to_mongodb=save_to_mongodb,
                offset=offset + settings.CACHE_SIZE,
                experience=experience,
                include_total_count=include_total_count,
                is_remote_only=is_remote_only # Pass new parameter 
            )
            matched_jobs["jobs"] = matched_jobs.get("jobs", []) + matched_jobs_overflow.get("jobs", [])

        jobs: list[dict[str, Any]] = matched_jobs.get("jobs", [])
        if len(jobs) == 0:
            logger.warning("user matched with zero jobs", resume_id = resume.get("_id", None))

        score_threshold = 60.0
        if sort_type == SortType.DATE:

            def sorting_algo(job: dict) -> datetime:
                posted_date = job.get('posted_date', datetime(1999, 1, 1))
                if isinstance(posted_date, str):
                    posted_date = datetime.fromisoformat(posted_date)
                delta: timedelta = datetime.now() - posted_date
                score = job.get('score', 0.0)
                return -delta.total_seconds() if score >= score_threshold else score - 3600.0 * 24 * 90

            jobs.sort(key = sorting_algo, reverse = True)

        elif sort_type == SortType.RECOMMENDED:

            def recommend_algo(job: dict) -> float:
                posted_date = job.get('posted_date', datetime(1999, 1, 1))
                if posted_date is None:
                    posted_date = datetime(1999, 1, 1)
                if isinstance(posted_date, str):
                    posted_date = datetime.fromisoformat(posted_date)
                delta: timedelta = datetime.now() - posted_date
                score = job.get('score', 0.0)
                if score < score_threshold:
                    return score -100 * 14.4
                return score + 100 * (-(1.03)**delta.days + 1)

            jobs.sort(key = recommend_algo, reverse = True)

        start = offset % settings.CACHE_SIZE
        matched_jobs["jobs"] = jobs[start : start + settings.RETURNED_JOBS_SIZE]

        return matched_jobs
    except Exception as e:
        logger.exception(
            "Error matching jobs with resume",
            event_type="job_matching_error",
            error_type=type(e).__name__,
            error_details=str(e),
        )
        raise Exception("Failed to match jobs with resume.") from e
