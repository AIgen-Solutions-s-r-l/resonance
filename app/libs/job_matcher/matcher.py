"""
Core job matching logic.

This module contains the main functionality for matching jobs with resumes.
"""

from typing import List, Optional, Dict, Any, Tuple
from loguru import logger
from time import time

from app.schemas.location import LocationFilter
from app.core.config import settings
from app.metrics.algorithm import async_matching_algorithm_timer

from app.libs.job_matcher.exceptions import ValidationError
from app.libs.job_matcher.cache import cache
from app.libs.job_matcher.persistence import persistence
from app.libs.job_matcher.vector_matcher import vector_matcher
from app.libs.job_matcher.query_builder import query_builder
from app.services.applied_jobs_service import applied_jobs_service
from app.services.cooled_jobs_service import cooled_jobs_service


class JobMatcher:
    """Core job matching functionality."""
    
    def __init__(self) -> None:
        """Initialize the job matcher."""
        self.settings = settings
        logger.info("JobMatcher initialized")
        
    async def _get_filter_conditions(
        self,
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        experience: Optional[List[str]] = None
    ) -> Tuple[List[str], List[Any]]:
        """
        Get the SQL filter conditions for the job query.
        
        Args:
            location: Optional location filter
            keywords: Optional keyword filter
            experience: Optional experience level filter
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        return query_builder.build_filter_conditions(
            location=location,
            keywords=keywords,
            experience=experience
        )
    
    @async_matching_algorithm_timer("process_job_optimized")
    async def process_job(
        self,
        resume: Dict[str, Any],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        save_to_mongodb: bool = False,
        offset: int = 0,
        use_cache: bool = True,
        limit: int = 25,
        experience: Optional[List[str]] = None,
        include_total_count: bool = True
    ) -> Dict[str, Any]:
        """
        Process a job matching request.
        
        Args:
            resume: Resume data with vector embedding
            location: Optional location filter
            keywords: Optional keyword filter
            save_to_mongodb: Whether to save results to MongoDB
            offset: Results offset (will be reset to 0 if greater than 1500)
            use_cache: Whether to use result caching
            limit: Results limit
            
        Returns:
            Dictionary with matched jobs list
        """
        start_time = time()
        
        # Validate offset parameter - reset to 0 if greater than 1500 (frontend limitation)
        if offset > 1500:
            logger.warning(
                "Offset exceeds maximum allowed value (1500), resetting to 0",
                original_offset=offset
            )
            offset = 0
        try:
            # Log all parameters at the start for debugging
            logger.info(
                "Starting job processing",
                has_location=location is not None,
                has_keywords=keywords is not None and len(keywords) > 0,
                has_experience=experience is not None and len(experience) > 0,
                offset=offset,
                limit=limit,
                use_cache=use_cache
            )
            logger.info("RESUME CHECK: Checking resume for vector embedding")
            
            # Check for vector embedding
            if "vector" not in resume:
                logger.warning("No vector found in resume")
                return {"jobs": []}
            else:
                vector_length = len(resume['vector']) if isinstance(resume.get('vector'), list) else 'unknown'
                logger.info(f"RESUME CHECK: Vector found in resume, length: {vector_length}")
            
            resume_id = str(resume.get("_id", "unknown"))
            logger.info(f"RESUME CHECK: Resume ID: {resume_id}")
            
            # Add log to debug resume structure
            logger.info(f"RESUME CHECK: Resume keys: {list(resume.keys())}")
            
            # Fetch applied job IDs for the user *before* cache check
            applied_ids: Optional[List[str]] = None
            if "user_id" in resume:
                user_id = resume["user_id"]
                logger.info(f"PROCESSING: Fetching applied job IDs for user: {user_id}")
                try:
                    # Ensure applied_jobs_service is awaited if it's async
                    applied_ids = await applied_jobs_service.get_applied_jobs(user_id)
                    if applied_ids:
                         logger.info(f"PROCESSING: Found {len(applied_ids)} applied job IDs for cache key.")
                    else:
                         logger.info(f"PROCESSING: No applied job IDs found for user {user_id}.")
                except AttributeError:
                     logger.error("AppliedJobsService does not have 'get_applied_jobs'. Cannot include in cache key.")
                     applied_ids = None # Ensure it's None if fetch fails
                except Exception as e:
                    logger.error(f"Error fetching applied job IDs for cache key: {e}")
                    applied_ids = None # Proceed without filtering on error
            else:
                logger.info("PROCESSING: No user_id in resume, cannot fetch applied jobs for cache key.")
                
            # Fetch cooled job IDs *before* cache check
            cooled_ids: Optional[List[str]] = None
            try:
                logger.info("PROCESSING: Fetching cooled job IDs")
                cooled_ids = await cooled_jobs_service.get_cooled_jobs()
                if cooled_ids:
                    logger.info(f"PROCESSING: Found {len(cooled_ids)} cooled job IDs for cache key.")
                else:
                    logger.info("PROCESSING: No cooled job IDs found.")
            except AttributeError:
                logger.error("CooledJobsService does not have 'get_cooled_jobs'. Cannot include in cache key.")
                cooled_ids = None # Ensure it's None if fetch fails
            except Exception as e:
                logger.error(f"Error fetching cooled job IDs for cache key: {e}")
                cooled_ids = None # Proceed without filtering on error

            # Check cache if enabled
            if use_cache:
                logger.info("CACHE CHECK: Checking cache for existing results")
                cache_key = await cache.generate_key(
                    resume_id,
                    offset=offset,
                    location=location.dict() if location else None,
                    keywords=keywords,
                    experience=experience,
                    applied_job_ids=applied_ids, # Include applied IDs in cache key
                    cooled_job_ids=cooled_ids # Include cooled IDs in cache key
                )
                logger.info(f"CACHE CHECK: Generated cache key: {cache_key}")
                cached_results = await cache.get(cache_key)
                logger.info(f"CACHE CHECK: Cache hit: {cached_results is not None}")
                if cached_results:
                    logger.info(
                        "Using cached job matches",
                        cache_key=cache_key,
                        matches_found=len(cached_results.get("jobs", [])),
                        elapsed_time=f"{time() - start_time:.6f}s"
                    )

                    # Post-cache filtering is removed. Cache key now includes applied_ids hash.
                    logger.info(f"RESULTS: Final job matches count from cache (key includes applied_ids): {len(cached_results.get('jobs', []))}")
                    
                    return cached_results
            
            logger.info("PROCESSING: No cache hit, proceeding with matching")
            
            # Process the match
            logger.info("PROCESSING: Extracting CV embedding from resume")
            cv_embedding = resume["vector"]
            vector_length = len(cv_embedding) if isinstance(cv_embedding, list) else 'unknown'
            logger.info(f"PROCESSING: Starting vector similarity search with embedding length: {vector_length}")
            
            # Applied IDs and cooled IDs are already fetched before the cache check.
            
            # Combine applied and cooled job IDs for filtering
            filtered_job_ids = []
            if applied_ids:
                filtered_job_ids.extend(applied_ids)
            if cooled_ids:
                filtered_job_ids.extend(cooled_ids)
                
            if filtered_job_ids:
                logger.info(f"PROCESSING: Combined {len(filtered_job_ids)} job IDs for filtering (applied + cooled)")
            else:
                logger.info("PROCESSING: No job IDs to filter (neither applied nor cooled)")

            # Use the vector matcher to find matches, passing combined IDs for filtering
            logger.info("PROCESSING: Calling vector_matcher.get_top_jobs_by_vector_similarity with filtering")
            job_matches = await vector_matcher.get_top_jobs_by_vector_similarity(
                cv_embedding,
                location=location,
                keywords=keywords,
                offset=offset,
                limit=limit,
                experience=experience,
                applied_job_ids=filtered_job_ids # Pass the combined IDs
            )
            
            logger.info(f"RESULTS: Received {len(job_matches)} matches from vector matcher")
            job_results = {
                "jobs": [match.to_dict() for match in job_matches]
            }
            
            # Add total count to response if requested
            if include_total_count:
                # We need to get the full count from vector_matcher's internal count logic
                # This uses the same filter conditions but ignores offset/limit
                # This query is already done as part of get_top_jobs_by_vector_similarity
                # To avoid having to do it again, we'll get the count through vector_matcher
                from app.utils.db_utils import get_db_cursor
                # Get the filter conditions
                where_clauses, query_params = await self._get_filter_conditions(
                    location=location, keywords=keywords, experience=experience
                )
                
                async with get_db_cursor() as cursor:
                    from app.utils.db_utils import get_filtered_job_count
                    total_jobs = await get_filtered_job_count(cursor, where_clauses, query_params, False)
                    logger.info(f"RESULTS: Total job count for pagination: {total_jobs}")
                    job_results["total_count"] = total_jobs
            
            # Post-filtering logic removed as filtering is now done in the DB query
            logger.info(f"RESULTS: Final job matches count after DB filtering: {len(job_results['jobs'])}")
            
            # Save matches if requested
            if save_to_mongodb:
                logger.info("RESULTS: Saving matches to MongoDB")
                await persistence.save_matches(job_results, resume_id, save_to_mongodb)
            
            # Store in cache if enabled
            if use_cache:
                logger.info("RESULTS: Storing results in cache")
                # Regenerate key including applied_ids for setting cache
                # Note: applied_ids was fetched before the initial cache check
                cache_key = await cache.generate_key(
                    resume_id,
                    offset=offset,
                    location=location.dict() if location else None,
                    keywords=keywords,
                    experience=experience,
                    applied_job_ids=applied_ids, # Include applied IDs in cache key
                    cooled_job_ids=cooled_ids # Include cooled IDs in cache key
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