"""
Optimized job matcher module.

This module provides an optimized implementation of the job matching functionality
with connection pooling, vector similarity optimizations, and caching.
"""

from app.log.logging import logger
import sys
import os

logger.info("Initializing Job Matcher module")

# Import main components
from app.libs.job_matcher.models import JobMatch
from app.libs.job_matcher.exceptions import (
    JobMatcherError, 
    VectorSimilarityError,
    CacheError,
    PersistenceError,
    ValidationError,
    QueryBuildingError
)

# Import implementation components
from app.libs.job_matcher.cache import cache
from app.libs.job_matcher.query_builder import query_builder
from app.libs.job_matcher.persistence import persistence
from app.libs.job_matcher.job_validator import job_validator
from app.libs.job_matcher.similarity_searcher import SimilaritySearcher
from app.libs.job_matcher.vector_matcher import vector_matcher


# Combined implementation class
class OptimizedJobMatcher:
    """
    Complete job matcher implementation that brings together all components.
    Maintains the same interface as the original implementation for compatibility.
    """
    
    def __init__(self):
        """Initialize the optimized job matcher."""
        from app.core.config import settings
        self.settings = settings
        self._vector_matcher = vector_matcher
        logger.info("OptimizedJobMatcher initialized")
    
    async def process_job(self, *args, **kwargs):
        """Delegate to the actual implementation."""
        from app.libs.job_matcher.matcher import JobMatcher
        matcher = JobMatcher()
        return await matcher.process_job(*args, **kwargs)
    
    async def get_top_jobs_by_vector_similarity(self, *args, **kwargs):
        """Delegate to the vector similarity matcher."""
        return await self._vector_matcher.get_top_jobs_by_vector_similarity(*args, **kwargs)
    
    async def save_matches(self, *args, **kwargs):
        """Delegate to the persistence component."""
        return await persistence.save_matches(*args, **kwargs)


# Create singleton instance for app usage
optimized_job_matcher = OptimizedJobMatcher()

__all__ = [
    'JobMatch',
    'OptimizedJobMatcher',
    'optimized_job_matcher',
    'JobMatcherError', 
    'VectorSimilarityError',
    'CacheError',
    'PersistenceError',
    'ValidationError',
    'QueryBuildingError',
]

logger.success("Job Matcher module initialized successfully")