"""
Vector similarity search functionality.

This module provides optimized vector similarity search for job matching.
"""

from typing import List, Optional, Dict, Any
from app.log.logging import logger
from time import time

from app.schemas.job_match import ManyToManyFilter
from app.schemas.location import LocationFilter
from app.core.config import settings
from app.utils.db_utils import execute_simple_query, execute_vector_similarity_query
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

    async def _execute_query(
        self,
        cursor: Any,
        many_to_many_filters: List[ManyToManyFilter],
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
            applied_job_ids: Optional list of job IDs to exclude.

        Returns:
            List of JobMatch objects
        """
        start_time = time()
         
        # Log incoming parameters for debugging
        logger.info(
            "SIMILARITY: Starting vector query execution",
            cursor_type=type(cursor).__name__,
            where_count=len(where_clauses),
            many_to_many=len(many_to_many_filters),
            params_count=len(query_params),
            param_types=[type(p).__name__ for p in query_params],
            param_values=str(query_params)[:100] + "..." if len(str(query_params)) > 100 else query_params,
            limit=limit,
            offset=offset
        )
        
        vector_start = time()
        logger.info("SIMILARITY: Calling execute_simple_query")
        results = await execute_simple_query(
            cursor,
            many_to_many_filters,
            where_clauses,
            query_params,
            limit,
            offset
        )
        vector_elapsed = time() - vector_start
        
        logger.debug(
            "Simple query execution completed",
            results_count=len(results),
            elapsed_time=f"{vector_elapsed:.6f}s"
        )
        
        job_matches_dict: Dict[int, JobMatch] = {}
        for row in results:
            id = row.get("id", None)
            if not id:
                logger.warning("Got JobMatch row with null id", row=row)
                continue
            if id not in job_matches_dict.keys():
                job_match = job_validator.create_job_match(row)
                if job_match:
                    job_matches_dict[id] = job_match
            else:
                job_root_field, job_sub_field = job_validator.extract_fields(row)
                if job_root_field:
                    job_matches_dict[id].root_fields.add(job_root_field)
                if job_sub_field:
                    job_matches_dict[id].sub_fields.add(job_sub_field)

                
        job_matches = list(job_matches_dict.values())
        
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
            "Simple query process completed",
            matches_found=len(job_matches),
            elapsed_time=f"{elapsed:.6f}s"
        )
        
        return job_matches
    
    async def _execute_vector_query(
        self,
        cursor: Any,
        user_id: int,
        cv_embedding: List[float],
        many_to_many_filters: List[ManyToManyFilter],
        where_clauses: List[str],
        query_params: List[Any],
        limit: int,
        offset: int,
        blacklisted_job_ids: Optional[List[int]] = None,
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
         
        # Log incoming parameters for debugging
        logger.info(
            "SIMILARITY: Starting vector query execution",
            cursor_type=type(cursor).__name__,
            embedding_length=len(cv_embedding),
            where_count=len(where_clauses),
            many_to_many=len(many_to_many_filters),
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
            user_id,
            cv_embedding,
            many_to_many_filters,
            where_clauses,
            query_params,
            limit,
            offset,
            blacklisted_job_ids=blacklisted_job_ids # Pass parameter
        )
        vector_elapsed = time() - vector_start
        
        logger.debug(
            "Vector similarity query execution completed",
            results_count=len(results),
            elapsed_time=f"{vector_elapsed:.6f}s"
        )
        
        job_matches_dict: Dict[int, JobMatch] = {}
        for row in results:
            id = row.get("id", None)
            if not id:
                logger.warning("Got JobMatch row with null id", row=row)
                continue
            if id not in job_matches_dict.keys():
                job_match = job_validator.create_job_match(row)
                if job_match:
                    job_matches_dict[id] = job_match
            else:
                job_root_field, job_sub_field = job_validator.extract_fields(row)
                if job_root_field:
                    job_matches_dict[id].root_fields.add(job_root_field)
                if job_sub_field:
                    job_matches_dict[id].sub_fields.add(job_sub_field)

                
        job_matches = list(job_matches_dict.values())
        
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