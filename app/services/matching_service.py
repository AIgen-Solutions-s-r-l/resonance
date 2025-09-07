from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from typing import List
from app.libs.job_matcher_optimized import OptimizedJobMatcher
from app.core.mongodb import collection_name, user_collection
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
    
def sort_jobs(
    jobs: list[dict[str, Any]],
    sort_type: SortType,
    score_threshold: float = 50.0
):
    
    if sort_type == SortType.DATE:

        def sorting_algo(job: dict) -> datetime:
            posted_date = job.get('posted_date', datetime(1999, 1, 1))
            if isinstance(posted_date, str):
                posted_date = datetime.fromisoformat(posted_date)
            delta: timedelta = datetime.now() - posted_date
            score = job.get('score', None)
            if score is None or score >= score_threshold:
                return -delta.total_seconds()
            
            return score - 3600.0 * 24 * 90

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


# TODO: temporary approach
async def save_preference(
    user_id: int,
    experience: str
) -> None:
    
    await user_collection.update_one(
        {"user_id": user_id},
        {"$set": {
            "experience": experience
        }},
        upsert=True
    )

async def match_jobs_with_resume(
    resume: Optional[Dict[str, Any]],
    location: List[LocationFilter] = [],
    fields: Optional[List[int]] = None,
    keywords: Optional[List[str]] = None,
    save_to_mongodb: bool = False,
    offset: int = 0,
    experience: Optional[List[str]] = None,
    is_remote_only: Optional[bool] = None, # Add new parameter
    sort_type: SortType = SortType.RECOMMENDED,
    fallback: bool = True
) -> Dict[str, Any]:
    try:
        matcher = OptimizedJobMatcher()
        
        matched_jobs = await matcher.process_job(
            resume,
            location=location,
            keywords=keywords,
            fields=fields,
            save_to_mongodb=save_to_mongodb,
            offset=offset,
            experience=experience,
            is_remote_only=is_remote_only # Pass new parameter 
        )

        jobs: list[dict[str, Any]] = matched_jobs.get("jobs", [])

        if offset % settings.CACHE_SIZE > (offset + settings.RETURNED_JOBS_SIZE) % settings.CACHE_SIZE:
            # Then we recieved something like 999 as offset. Should never happen, but users are assholes
            # so better be safe than sorry
            matched_jobs_overflow = await matcher.process_job(
                resume,
                location=location,
                fields=fields,
                keywords=keywords,
                save_to_mongodb=save_to_mongodb,
                offset=offset + settings.CACHE_SIZE,
                experience=experience,
                is_remote_only=is_remote_only # Pass new parameter 
            )
            jobs = jobs + matched_jobs_overflow.get("jobs", [])

        
        if len(jobs) == 0:
            logger.warning("user matched with zero jobs", resume_id = resume.get("_id") if resume else None)
        else:
            logger.info("matched with {amount} jobs", resume_id = resume.get("_id") if resume else None, amount=len(jobs))
            sort_jobs(
                jobs, 
                sort_type,
                50.0 if fields is None or len(fields) == 0 else 0.0
            )
        
        matched_jobs["total_count"] = 2000
        if fallback and len(jobs) < settings.CACHE_SIZE and offset < settings.CACHE_SIZE:
            logger.info("retrieving further, unfiltered, jobs", resume_id = resume.get("_id") if resume else None)
            # then we extract other (unfiltered) jobs until we have at least ONE cache worth of jobs
            matched_jobs_unfiltered = await matcher.process_job(
                resume,
                save_to_mongodb=save_to_mongodb
            )
            
            ids = set([job["id"] for job in jobs])
            non_duplicates = list(filter(lambda job: job["id"] not in ids, matched_jobs_unfiltered["jobs"]))
            sort_jobs(
                non_duplicates, 
                sort_type,
                50.0 if fields is None or len(fields) == 0 else 0.0
            )
            jobs = jobs + non_duplicates
            matched_jobs["total_count"] = settings.CACHE_SIZE

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
