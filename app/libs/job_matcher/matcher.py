"""
Core job matching logic.

This module contains the main functionality for matching jobs with resumes.
"""

from typing import List, Optional, Dict, Any
from loguru import logger
from time import time

from app.schemas.location import LocationFilter
from app.core.config import settings
from app.metrics.algorithm import async_matching_algorithm_timer

from app.libs.job_matcher.exceptions import ValidationError
from app.libs.job_matcher.cache import cache
from app.libs.job_matcher.persistence import persistence
from app.libs.job_matcher.vector_matcher import vector_matcher


class JobMatcher:
    """Core job matching functionality."""
    
    def __init__(self) -> None:
        """Initialize the job matcher."""
        self.settings = settings
        logger.info("JobMatcher initialized")
    
    @async_matching_algorithm_timer("process_job_optimized")
    async def process_job(
        self,
        resume: Dict[str, Any],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        save_to_mongodb: bool = False,
        offset: int = 0,
        use_cache: bool = True,
        limit: int = 5
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Process a job matching request.
        
        Args:
            resume: Resume data with vector embedding
            location: Optional location filter
            keywords: Optional keyword filter
            save_to_mongodb: Whether to save results to MongoDB
            offset: Results offset
            use_cache: Whether to use result caching
            limit: Results limit
            
        Returns:
            Dictionary with matched jobs list
        """
        start_time = time()
        try:
            logger.info(
                "Starting job processing",
                has_location=location is not None,
                has_keywords=keywords is not None and len(keywords) > 0,
                offset=offset,
                limit=limit,
                use_cache=use_cache
            )
            
            # Check for vector embedding
            if "vector" not in resume:
                logger.warning("No vector found in resume")
                return {"jobs": []}
            
            resume_id = str(resume.get("_id", "unknown"))
            
            # Check cache if enabled
            if use_cache:
                cache_key = await cache.generate_key(
                    resume_id, 
                    offset=offset,
                    location=location.dict() if location else None,
                    keywords=keywords
                )
                cached_results = await cache.get(cache_key)
                
                if cached_results:
                    logger.info(
                        "Using cached job matches",
                        cache_key=cache_key,
                        matches_found=len(cached_results.get("jobs", [])),
                        elapsed_time=f"{time() - start_time:.6f}s"
                    )
                    return cached_results
            
            # Process the match
            cv_embedding = resume["vector"]
            
            # Use the vector matcher to find matches
            job_matches = await vector_matcher.get_top_jobs_by_vector_similarity(
                cv_embedding,
                location=location,
                keywords=keywords,
                offset=offset,
                limit=limit
            )
            
            job_results = {
                "jobs": [match.to_dict() for match in job_matches]
            }
            
            # Save matches if requested
            if save_to_mongodb:
                await persistence.save_matches(job_results, resume_id, save_to_mongodb)
            
            # Store in cache if enabled
            if use_cache:
                cache_key = await cache.generate_key(
                    resume_id, 
                    offset=offset,
                    location=location.dict() if location else None,
                    keywords=keywords
                )
                await cache.set(cache_key, job_results)
            
            elapsed = time() - start_time
            logger.success(
                "Successfully processed job",
                matches_found=len(job_results["jobs"]),
                elapsed_time=f"{elapsed:.6f}s"
            )
            
            return job_results
        
        except Exception as e:
            elapsed = time() - start_time
            logger.exception(
                "Failed to process job",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise


# Singleton instance
matcher = JobMatcher()