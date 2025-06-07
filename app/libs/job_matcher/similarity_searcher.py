"""
Vector similarity search functionality.

This module provides optimized vector similarity search for job matching.
"""

from typing import List, Optional, Dict, Any
from app.log.logging import logger
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
            j.portal as portal,
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
        offset: int,
        applied_job_ids: Optional[List[int]] = None, # Added parameter
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
            applied_job_ids: Optional list of job IDs to exclude.

        Returns:
            List of JobMatch objects
        """
        start_time = time()
        
        # Define the expected vector dimension
        EXPECTED_DIMENSION = 1024
        
        # Validate and normalize embedding format
        if isinstance(cv_embedding, str):
            logger.warning(
                f"SIMILARITY: Received string embedding instead of list, attempting to convert")
            try:
                # Remove brackets and split by commas
                cleaned = cv_embedding.strip('[]').split(',')
                cv_embedding = [float(x.strip()) for x in cleaned if x.strip()]
                logger.info(f"SIMILARITY: Successfully converted string to list of {len(cv_embedding)} floats")
            except Exception as e:
                logger.error(f"SIMILARITY: Failed to convert string embedding: {str(e)}")
                raise ValueError(f"Invalid embedding format: {cv_embedding[:50]}...")
        
        # Ensure it's a list
        if not isinstance(cv_embedding, list):
            raise ValueError(f"Embedding must be a list of floats, got {type(cv_embedding).__name__}")
            
        # Check and fix vector dimensions
        current_dim = len(cv_embedding)
        if current_dim != EXPECTED_DIMENSION:
            logger.warning(f"SIMILARITY: Vector dimension mismatch: got {current_dim}, expected {EXPECTED_DIMENSION}")
            
            if current_dim < EXPECTED_DIMENSION:
                # Pad with zeros if too short
                padding = [0.0] * (EXPECTED_DIMENSION - current_dim)
                cv_embedding = cv_embedding + padding
                logger.info(f"SIMILARITY: Padded vector from {current_dim} to {EXPECTED_DIMENSION} dimensions")
            else:
                # Truncate if too long
                cv_embedding = cv_embedding[:EXPECTED_DIMENSION]
                logger.info(f"SIMILARITY: Truncated vector from {current_dim} to {EXPECTED_DIMENSION} dimensions")
            
        # Log incoming parameters for debugging
        logger.info(
            "SIMILARITY: Starting vector query execution",
            cursor_type=type(cursor).__name__,
            embedding_length=len(cv_embedding),
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
            offset,
            applied_job_ids=applied_job_ids # Pass parameter
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