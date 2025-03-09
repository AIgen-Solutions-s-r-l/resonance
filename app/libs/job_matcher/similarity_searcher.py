"""
Vector similarity search functionality.

This module provides optimized vector similarity search for job matching.
"""

from typing import List, Optional, Dict, Any
from loguru import logger
from time import time

from app.schemas.location import LocationFilter
from app.core.config import settings
from app.utils.db_utils import get_db_cursor, execute_vector_similarity_query, get_filtered_job_count
from app.metrics.algorithm import (
    async_matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count
)

from app.libs.job_matcher.models import JobMatch
from app.libs.job_matcher.query_builder import query_builder
from app.libs.job_matcher.job_validator import job_validator
from app.libs.job_matcher.exceptions import VectorSimilarityError


class SimilaritySearcher:
    """Handles vector similarity searches for job matching."""
    
    async def _execute_fallback_query(
        self, 
        cursor: Any,
        where_clauses: List[str], 
        query_params: List[Any],
        limit: int
    ) -> List[JobMatch]:
        """
        Execute a simple fallback query without vector operations.
        
        Args:
            cursor: Database cursor
            where_clauses: SQL WHERE clauses
            query_params: Query parameters
            limit: Results limit
            
        Returns:
            List of JobMatch objects
        """
        start_time = time()
        
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
        
        simple_start = time()
        await cursor.execute(simple_query, query_params + [limit])
        results = await cursor.fetchall()
        simple_elapsed = time() - simple_start
        
        logger.debug(
            "Fallback query execution completed",
            results_count=len(results),
            elapsed_time=f"{simple_elapsed:.6f}s",
            sql_size=len(simple_query)
        )
        
        job_matches = []
        for row in results:
            if job_match := job_validator.create_job_match(row):
                job_matches.append(job_match)
        
        # Report metrics for the fallback path
        if settings.metrics_enabled:
            report_algorithm_path("simple_fallback", {"reason": "few_results"})
            report_match_count(len(job_matches), {"path": "simple_fallback"})
        
        elapsed = time() - start_time
        logger.info(
            "Fallback query process completed",
            matches_found=len(job_matches),
            elapsed_time=f"{elapsed:.6f}s"
        )
        
        return job_matches
    
    async def _execute_vector_query(
        self,
        cursor: Any,
        cv_embedding: List[float],
        where_clauses: List[str],
        query_params: List[Any],
        limit: int,
        offset: int
    ) -> List[JobMatch]:
        """
        Execute vector similarity query.
        
        Args:
            cursor: Database cursor
            cv_embedding: Resume vector embedding
            where_clauses: SQL WHERE clauses
            query_params: Query parameters
            limit: Results limit
            offset: Results offset
            
        Returns:
            List of JobMatch objects
        """
        start_time = time()
        
        # Log incoming parameters for debugging
        logger.info(
            "SIMILARITY: Starting vector query execution",
            cursor_type=type(cursor).__name__,
            embedding_length=len(cv_embedding) if isinstance(cv_embedding, list) else 'unknown',
            where_count=len(where_clauses),
            params_count=len(query_params),
            param_types=[type(p).__name__ for p in query_params],
            param_values=str(query_params)[:100] + "..." if len(str(query_params)) > 100 else query_params,
            limit=limit,
            offset=offset
        )
        
        vector_start = time()
        logger.info("SIMILARITY: Calling execute_vector_similarity_query")
        results = await execute_vector_similarity_query(
            cursor,
            cv_embedding,
            where_clauses,
            query_params,
            limit,
            offset
        )
        vector_elapsed = time() - vector_start
        
        logger.debug(
            "Vector similarity query execution completed",
            results_count=len(results),
            elapsed_time=f"{vector_elapsed:.6f}s"
        )
        
        job_matches = []
        for row in results:
            if job_match := job_validator.create_job_match(row):
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
        
        elapsed = time() - start_time
        logger.info(
            "Vector query process completed",
            matches_found=len(job_matches),
            elapsed_time=f"{elapsed:.6f}s"
        )
        
        return job_matches