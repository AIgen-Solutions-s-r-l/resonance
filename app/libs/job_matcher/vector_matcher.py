"""
Vector matching functionality for job matcher.

This module provides the main interface for vector similarity job matching.
"""

from typing import List, Optional
from app.log.logging import logger
from time import time

from app.schemas.location import LocationFilter
from app.utils.db_utils import get_db_cursor
from app.metrics.algorithm import async_matching_algorithm_timer

from app.libs.job_matcher.models import JobMatch
from app.core.config import settings
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
        fields: Optional[List[int]] = None,
        offset: int = 0,
        limit: int = settings.CACHE_SIZE,
        experience: Optional[List[str]] = None,
        applied_job_ids: Optional[List[int]] = None,
        is_remote_only: Optional[bool] = None, # Add new parameter
    ) -> List[JobMatch]:
        """
        Get top matching jobs using optimized vector similarity.

        Args:
            cv_embedding: Resume vector embedding
            location: Optional location filter
            keywords: Optional keyword filter
            offset: Results offset
            limit: Results limit
            experience: Optional experience level filter. Allowed values: Intern, Entry, Mid, Executive
            applied_job_ids: Optional list of job IDs to exclude.
            is_remote_only: Optional filter for remote jobs only.

        Returns:
            List of JobMatch objects
        """
        start_time = time()
        try:
            logger.info(
                f"VECTOR_MATCH: Starting with params: loc={location != None}, keywords={keywords != None}, offset={offset}")

            # Build filter conditions
            logger.info("VECTOR_MATCH: Building filter conditions")
            many_to_many_filters, where_clauses, query_params = query_builder.build_filter_conditions(
                location=location, keywords=keywords, fields=fields, experience=experience, is_remote_only=is_remote_only # Pass new parameter
            )

            logger.info(
                "VECTOR_MATCH: Filter conditions built",
                filter_count=len(where_clauses),
                params_count=len(query_params)
            )

            logger.info("VECTOR_MATCH: Acquiring database cursor")
            async with get_db_cursor("default") as cursor:
                logger.info("VECTOR_MATCH: Database cursor acquired")

                # Execute optimized vector similarity query
                logger.info(
                    "VECTOR_MATCH: Executing optimized vector similarity query"
                )
                try:
                    # Define the expected vector dimension
                    # We should probably NOT define this here
                    EXPECTED_DIMENSION = 1024
                    
                    # Validate and normalize embedding format
                    if isinstance(cv_embedding, str):
                        logger.warning(
                            f"VECTOR_MATCH: Received string embedding instead of list, attempting to convert")
                        try:
                            # Remove brackets and split by commas
                            cleaned = cv_embedding.strip('[]').split(',')
                            cv_embedding = [float(x.strip()) for x in cleaned if x.strip()]
                            logger.info(f"VECTOR_MATCH: Successfully converted string to list of {len(cv_embedding)} floats")
                        except Exception as e:
                            logger.error(f"VECTOR_MATCH: Failed to convert string embedding: {str(e)}")
                            raise ValueError(f"Invalid embedding format: {cv_embedding[:50]}...")
                    
                    # Ensure it's a list
                    if not isinstance(cv_embedding, list):
                        raise ValueError(f"Embedding must be a list of floats, got {type(cv_embedding).__name__}")
                    
                    # Check and fix vector dimensions
                    current_dim = len(cv_embedding)
                    if current_dim != EXPECTED_DIMENSION:
                        logger.warning(f"VECTOR_MATCH: Vector dimension mismatch: got {current_dim}, expected {EXPECTED_DIMENSION}")
                        
                        if current_dim < EXPECTED_DIMENSION:
                            # Pad with zeros if too short
                            padding = [0.0] * (EXPECTED_DIMENSION - current_dim)
                            cv_embedding = cv_embedding + padding
                            logger.info(f"VECTOR_MATCH: Padded vector from {current_dim} to {EXPECTED_DIMENSION} dimensions")
                        else:
                            # Truncate if too long
                            cv_embedding = cv_embedding[:EXPECTED_DIMENSION]
                            logger.info(f"VECTOR_MATCH: Truncated vector from {current_dim} to {EXPECTED_DIMENSION} dimensions")
                        
                    # Log embedding dimensions for troubleshooting
                    embedding_len = len(cv_embedding)
                    logger.info(
                        f"VECTOR_MATCH: Using embedding of length {embedding_len}")

                    # Detailed logging of query parameters
                    logger.info(
                        "VECTOR_MATCH: Query parameters detail",
                        cursor_type=type(cursor).__name__,
                        embedding_sample=str(cv_embedding[:3]) + "..." if isinstance(
                            cv_embedding, list) and len(cv_embedding) > 3 else cv_embedding,
                        where_clauses=where_clauses,
                        query_params=query_params,
                        query_params_types=[
                            type(p).__name__ for p in query_params],
                        limit=limit,
                        offset=offset
                    )

                    result = await self.similarity_searcher._execute_vector_query(
                        cursor, cv_embedding, many_to_many_filters, where_clauses, query_params, limit, offset, applied_job_ids=applied_job_ids  # Pass parameter
                    )
                    logger.info(
                        f"VECTOR_MATCH: Vector query returned {len(result)} results")
                    return result
                except Exception as e:
                    logger.error(
                        f"VECTOR_MATCH ERROR: Vector query failed: {str(e)}")
                    raise

        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "VECTOR_MATCH ERROR: Matching failed",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise VectorSimilarityError(
                f"Error in vector similarity matching: {str(e)}")


# Singleton instance
vector_matcher = VectorMatcher()
