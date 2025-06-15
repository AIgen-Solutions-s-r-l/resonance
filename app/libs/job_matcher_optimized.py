"""
Optimized job matcher implementation with performance enhancements.

This module provides an optimized implementation of the job matching functionality
with connection pooling, vector similarity optimizations, and caching.

DEPRECATED: This file is maintained for backward compatibility only.
Please use the app.libs.job_matcher module instead.
"""

from loguru import logger

# Log deprecation warning
logger.warning(
    "Using deprecated job_matcher_optimized.py module. "
    "Please import from app.libs.job_matcher instead."
)

# Re-export from the refactored module
from app.libs.job_matcher import (
    JobMatch,
    OptimizedJobMatcher,
    optimized_job_matcher
)

# Re-export database utilities needed by tests
from app.utils.db_utils import (
    get_db_cursor,
    execute_vector_similarity_query
)

# For backward compatibility
__all__ = [
    'JobMatch',
    'OptimizedJobMatcher',
    'get_db_cursor',
    'execute_vector_similarity_query'
]