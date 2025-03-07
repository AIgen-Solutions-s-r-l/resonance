"""
Optimized job matcher implementation with performance enhancements.

This module provides an optimized implementation of the job matching functionality
with connection pooling, vector similarity optimizations, and caching.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, UTC
import json
import asyncio
from time import time

from app.core.config import settings
from app.log.logging import logger
from app.schemas.location import LocationFilter
from app.utils.data_parsers import parse_skills_string
from app.utils.db_utils import get_db_cursor, execute_vector_similarity_query, get_filtered_job_count
from app.metrics.algorithm import (
    async_matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count
)

# Simple in-memory cache for results
# Structure: {cache_key: (result, timestamp)}
_results_cache: Dict[str, tuple] = {}
_cache_ttl = 300  # Cache TTL in seconds
_cache_lock = asyncio.Lock()


@dataclass
class JobMatch:
    """Data class for job matching results, aligned with JobSchema."""
    
    id: str
    title: str
    description: Optional[str] = None
    workplace_type: Optional[str] = None
    short_description: Optional[str] = None
    field: Optional[str] = None
    experience: Optional[str] = None
    skills_required: Optional[List[str]] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    portal: Optional[str] = None
    score: Optional[float] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    apply_link: Optional[str] = None
    location: Optional[str] = None


class OptimizedJobMatcher:
    """An optimized class to handle job matching operations using CV embeddings and similarity metrics."""

    # Required fields that must be present in database results
    REQUIRED_FIELDS = {'id', 'title'}

    def __init__(self) -> None:
        """Initialize the optimized job matcher."""
        self.settings = settings

    def _validate_row_data(self, row: dict) -> bool:
        """
        Validate that row has all required fields.
        
        Args:
            row: Dictionary containing database row data
            
        Returns:
            bool: True if all required fields are present, False otherwise
        """
        return all(field in row for field in self.REQUIRED_FIELDS)

    def _create_job_match(self, row: dict) -> Optional[JobMatch]:
        """
        Create a JobMatch instance from a database row dictionary.
        
        Args:
            row: Dictionary containing job data from database
            
        Returns:
            JobMatch instance if successful, None if required fields are missing
        """
        if not isinstance(row, dict):
            logger.error(
                "Row is not a dictionary",
                row_type=type(row),
                row_data=row
            )
            try:
                row = dict(row)
            except Exception as e:
                logger.error(
                    "Failed to convert row to dictionary",
                    error=str(e)
                )
                return None
                
        if not self._validate_row_data(row):
            logger.warning(
                "Skipping job match due to missing required fields",
                row=row,
                required_fields=self.REQUIRED_FIELDS
            )
            return None
            
        try:
            return JobMatch(
                id=str(row['id']),
                title=row['title'],
                description=row.get('description'),
                workplace_type=row.get('workplace_type'),
                short_description=row.get('short_description'),
                field=row.get('field'),
                experience=row.get('experience'),
                skills_required=parse_skills_string(row.get('skills_required')),
                country=row.get('country'),
                city=row.get('city'),
                company_name=row.get('company_name'),
                company_logo=row.get('company_logo'),
                portal=row.get('portal', 'test_portal'),
                score=float(row.get('score', 0.0)),
                posted_date=row.get('posted_date'),
                job_state=row.get('job_state'),
                apply_link=row.get('apply_link'),
                location=row.get('location')
            )
        except Exception as e:
            logger.error(
                "Failed to create JobMatch instance",
                error=str(e),
                row=row
            )
            return None

    async def _generate_cache_key(
        self,
        resume_id: str,
        location: Optional[LocationFilter],
        keywords: Optional[List[str]],
        offset: int
    ) -> str:
        """
        Generate a cache key for the given parameters.
        
        Args:
            resume_id: Resume ID
            location: Location filter
            keywords: Keyword filter
            offset: Results offset
            
        Returns:
            Cache key string
        """
        key_parts = [resume_id, offset]
        
        if location:
            key_parts.append(f"loc_{location.country}_{location.city}")
            if location.latitude and location.longitude:
                key_parts.append(f"geo_{location.latitude}_{location.longitude}_{location.radius_km}")
        
        if keywords:
            key_parts.append(f"kw_{','.join(sorted(keywords))}")
        
        return "_".join(str(part) for part in key_parts)

    async def _get_cached_results(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """
        Get cached results if available and not expired.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached results or None if not found or expired
        """
        async with _cache_lock:
            if cache_key in _results_cache:
                results, timestamp = _results_cache[cache_key]
                # Check if cache entry has expired
                if time() - timestamp <= _cache_ttl:
                    logger.debug(
                        "Using cached results",
                        cache_key=cache_key
                    )
                    return results
                
                # Cache entry has expired
                del _results_cache[cache_key]
        
        return None

    async def _store_cached_results(self, cache_key: str, results: Dict[str, Any]) -> None:
        """
        Store results in cache.
        
        Args:
            cache_key: Cache key
            results: Results to cache
        """
        async with _cache_lock:
            _results_cache[cache_key] = (results, time())
            
            # Cleanup cache if it gets too large (simple approach)
            if len(_results_cache) > 1000:  # Arbitrary limit
                # Remove oldest entries
                sorted_items = sorted(_results_cache.items(), key=lambda x: x[1][1])
                to_remove = len(_results_cache) // 2  # Remove half of the entries
                
                for key, _ in sorted_items[:to_remove]:
                    del _results_cache[key]

    @async_matching_algorithm_timer("optimized_vector_similarity")
    async def get_top_jobs_by_vector_similarity(
        self,
        cv_embedding: List[float],
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        offset: int = 0,
        limit: int = 5,
    ) -> List[JobMatch]:
        """
        Get top matching jobs using optimized vector similarity.
        
        Args:
            cv_embedding: Resume vector embedding
            location: Optional location filter
            keywords: Optional keyword filter
            offset: Results offset
            limit: Results limit
            
        Returns:
            List of JobMatch objects
        """
        try:
            # Build filter conditions
            where_clauses = ["embedding IS NOT NULL"]
            query_params = []
            
            # Location filter
            if location and location.country:
                where_clauses.append("(co.country_name = CASE WHEN %s = 'USA' THEN 'United States' ELSE %s END)")
                query_params.extend([location.country, location.country])
            
            if location and location.city:
                where_clauses.append("(l.city = %s OR l.city = 'remote')")
                query_params.append(location.city)
            
            if (
                location
                and location.latitude
                and location.longitude
                and location.radius_km
            ):
                where_clauses.append(
                    """
                    (
                        l.city = 'remote'
                        OR ST_DWithin(
                            ST_MakePoint(l.longitude::DOUBLE PRECISION, l.latitude::DOUBLE PRECISION)::geography,
                            ST_MakePoint(%s, %s)::geography,
                            %s * 1000
                        )
                    )
                    """
                )
                query_params.extend(
                    [location.longitude, location.latitude, location.radius_km]
                )
            
            # Keywords filter
            if keywords and len(keywords) > 0:
                or_clauses = []
                for kw in keywords:
                    or_clauses.append("(j.title ILIKE %s OR j.description ILIKE %s)")
                    query_params.extend([f"%{kw}%", f"%{kw}%"])
                
                where_clauses.append("(" + " OR ".join(or_clauses) + ")")
            
            async with get_db_cursor("default") as cursor:
                # Check row count - using a lighter query
                row_count = await get_filtered_job_count(cursor, where_clauses, query_params)
                
                # For very small result sets, use a simpler query without vector operations
                if row_count <= 5:
                    logger.debug(
                        "Using simple fallback query",
                        row_count=row_count
                    )
                    
                    # Simple query without vector operations
                    where_sql = ""
                    if where_clauses:
                        where_sql = "WHERE " + " AND ".join(where_clauses)
                    
                    simple_query = f"""
                    SELECT
                        j.id as id,
                        j.title as title,
                        j.description as description,
                        j.workplace_type as workplace_type,
                        j.short_description as short_description,
                        j.field as field,
                        j.experience as experience,
                        j.skills_required as skills_required,
                        j.posted_date as posted_date,
                        j.job_state as job_state,
                        j.apply_link as apply_link,
                        co.country_name as country,
                        l.city as city,
                        c.company_name as company_name,
                        c.logo as company_logo,
                        'test_portal' as portal,
                        0.0 as score
                    FROM "Jobs" j
                    LEFT JOIN "Companies" c ON j.company_id = c.company_id
                    LEFT JOIN "Locations" l ON j.location_id = l.location_id
                    LEFT JOIN "Countries" co ON l.country = co.country_id
                    {where_sql}
                    LIMIT %s
                    """
                    
                    await cursor.execute(simple_query, query_params + [limit])
                    results = await cursor.fetchall()
                    
                    job_matches = []
                    for row in results:
                        if job_match := self._create_job_match(row):
                            job_matches.append(job_match)
                    
                    # Report metrics for the fallback path
                    if settings.metrics_enabled:
                        report_algorithm_path("simple_fallback", {"reason": "few_results"})
                        report_match_count(len(job_matches), {"path": "simple_fallback"})
                    
                    return job_matches
                
                # Execute optimized vector similarity query
                results = await execute_vector_similarity_query(
                    cursor,
                    cv_embedding,
                    where_clauses,
                    query_params,
                    limit,
                    offset
                )
                
                job_matches = []
                for row in results:
                    if job_match := self._create_job_match(row):
                        job_matches.append(job_match)
                
                # Report metrics for the vector similarity path
                if settings.metrics_enabled:
                    report_algorithm_path("vector_similarity", {"reason": "optimized"})
                    report_match_count(len(job_matches), {"path": "vector_similarity"})
                    
                    # Report score distribution if we have matches
                    if job_matches:
                        scores = [match.score for match in job_matches if match.score is not None]
                        if scores:
                            report_match_score_distribution(scores, {"path": "vector_similarity"})
                
                return job_matches
        
        except Exception as e:
            logger.error(
                "Error in vector similarity query",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    async def save_matches(
        self, job_results: dict, resume_id: str, save_to_mongodb: bool = False
    ) -> None:
        """
        Save job matches to JSON file and optionally to MongoDB.
        
        Args:
            job_results: Matching results
            resume_id: Resume ID
            save_to_mongodb: Whether to save to MongoDB
        """
        try:
            # Save to JSON
            filename = f"job_matches_{resume_id}.json"
            with open(filename, "w") as f:
                json.dump(job_results, f, indent=2)
            
            logger.info("Matched jobs saved to file", filename=filename)
            
            # Save to MongoDB if requested
            if save_to_mongodb:
                from app.core.mongodb import database
                
                matches_collection = database.get_collection("job_matches")
                
                # Add metadata to job results
                job_results["resume_id"] = resume_id
                job_results["timestamp"] = datetime.now(UTC)
                
                await matches_collection.insert_one(job_results)
                
                logger.info(
                    "Successfully saved matches to MongoDB",
                    resume_id=resume_id
                )
        
        except Exception as e:
            logger.error(
                "Failed to save matches",
                error=str(e),
                error_type=type(e).__name__
            )
            raise

    @async_matching_algorithm_timer("process_job_optimized")
    async def process_job(
        self,
        resume: dict,
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        save_to_mongodb: bool = False,
        offset: int = 0,
        use_cache: bool = True,
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
            
        Returns:
            Dictionary with matched jobs list
        """
        try:
            logger.info(
                "Starting optimized job processing",
                has_location=location is not None,
                has_keywords=keywords is not None and len(keywords) > 0,
                offset=offset
            )
            
            # Check for vector embedding
            if "vector" not in resume:
                logger.warning("No vector found in resume")
                return {"jobs": []}
            
            resume_id = str(resume.get("_id", "unknown"))
            
            # Check cache if enabled
            if use_cache:
                cache_key = await self._generate_cache_key(resume_id, location, keywords, offset)
                cached_results = await self._get_cached_results(cache_key)
                
                if cached_results:
                    logger.info(
                        "Using cached job matches",
                        cache_key=cache_key,
                        matches_found=len(cached_results.get("jobs", []))
                    )
                    return cached_results
            
            # Process the match
            cv_embedding = resume["vector"]
            
            job_matches = await self.get_top_jobs_by_vector_similarity(
                cv_embedding,
                location=location,
                keywords=keywords,
                offset=offset
            )
            
            job_results = {
                "jobs": [
                    {
                        "id": str(match.id),
                        "title": match.title,
                        "description": match.description,
                        "workplace_type": match.workplace_type,
                        "short_description": match.short_description,
                        "field": match.field,
                        "experience": match.experience,
                        "skills_required": match.skills_required,
                        "country": match.country,
                        "city": match.city,
                        "company_name": match.company_name,
                        "company_logo": match.company_logo,
                        "portal": match.portal,
                        "score": match.score,
                        "posted_date": match.posted_date.isoformat() if match.posted_date else None,
                        "job_state": match.job_state,
                        "apply_link": match.apply_link,
                        "location": match.location
                    }
                    for match in job_matches
                ]
            }
            
            # Save matches if requested
            if save_to_mongodb:
                await self.save_matches(job_results, resume_id, save_to_mongodb)
            
            # Store in cache if enabled
            if use_cache:
                cache_key = await self._generate_cache_key(resume_id, location, keywords, offset)
                await self._store_cached_results(cache_key, job_results)
            
            logger.success(
                "Successfully processed job",
                matches_found=len(job_results["jobs"])
            )
            
            return job_results
        
        except Exception as e:
            logger.exception(
                "Failed to process job: {e}",
                e=e
            )
            raise