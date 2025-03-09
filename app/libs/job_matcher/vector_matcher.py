"""
Vector matching functionality for job matcher.

This module provides the main interface for vector similarity job matching.
"""

from typing import List, Optional
from loguru import logger
from time import time

from app.schemas.location import LocationFilter
from app.core.config import settings
from app.utils.db_utils import get_db_cursor, get_filtered_job_count
from app.metrics.algorithm import async_matching_algorithm_timer

from app.libs.job_matcher.models import JobMatch
from app.libs.job_matcher.query_builder import query_builder
from app.libs.job_matcher.similarity_searcher import SimilaritySearcher
from app.libs.job_matcher.exceptions import VectorSimilarityError


class VectorMatcher:
    """Core vector similarity matching functionality."""
    
    def __init__(self):
        """Initialize the vector matcher."""
        self.similarity_searcher = SimilaritySearcher()
        logger.info("VectorMatcher initialized")
    
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
        start_time = time()
        try:
            # Build filter conditions
            where_clauses, query_params = query_builder.build_filter_conditions(
                location, keywords
            )
            
            logger.debug(
                "Starting vector similarity match",
                filter_count=len(where_clauses),
                params_count=len(query_params),
                offset=offset,
                limit=limit
            )
            
            async with get_db_cursor("default") as cursor:
                # Check row count using a lighter query
                count_start = time()
                row_count = await get_filtered_job_count(cursor, where_clauses, query_params)
                count_elapsed = time() - count_start
                
                logger.debug(
                    "Row count check completed",
                    row_count=row_count,
                    elapsed_time=f"{count_elapsed:.6f}s"
                )
                
                # For very small result sets, use simpler query
                if row_count <= 5:
                    logger.info(
                        "Using fallback strategy due to small result set",
                        row_count=row_count
                    )
                    
                    return await self.similarity_searcher._execute_fallback_query(
                        cursor, where_clauses, query_params, limit
                    )
                
                # Execute optimized vector similarity query
                return await self.similarity_searcher._execute_vector_query(
                    cursor, cv_embedding, where_clauses, query_params, limit, offset
                )
        
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "Error in vector similarity matching",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise VectorSimilarityError(f"Error in vector similarity matching: {str(e)}")


# Singleton instance
vector_matcher = VectorMatcher()