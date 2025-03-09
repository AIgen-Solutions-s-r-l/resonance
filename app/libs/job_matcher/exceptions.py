"""
Custom exceptions for the job matcher module.

This module defines custom exceptions for better error handling in the job matching functionality.
"""

class JobMatcherError(Exception):
    """Base exception for job matcher errors."""
    pass


class VectorSimilarityError(JobMatcherError):
    """Exception raised for errors in vector similarity operations."""
    pass


class CacheError(JobMatcherError):
    """Exception raised for errors in caching operations."""
    pass


class PersistenceError(JobMatcherError):
    """Exception raised for errors in persistence operations."""
    pass


class ValidationError(JobMatcherError):
    """Exception raised for data validation errors."""
    pass


class QueryBuildingError(JobMatcherError):
    """Exception raised for errors in query building."""
    pass