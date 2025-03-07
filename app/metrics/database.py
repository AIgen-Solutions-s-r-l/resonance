"""
Database-specific metrics collection and reporting.

This module provides specialized metrics tools for database operations,
including timing decorators for SQL queries, MongoDB operations, and
vector database interactions, as well as connection pool monitoring.
"""

import functools
import time
from typing import Dict, List, Optional, Callable, Any, TypeVar, cast, Union

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import (
    MetricNames,
    timer,
    async_timer,
    report_timing,
    report_gauge,
    increment_counter
)

# Type variable for function return values
T = TypeVar('T')


def sql_query_timer(query_type: str, operation: str = "unknown") -> Callable:
    """
    Decorator to time SQL query execution.
    
    Args:
        query_type: Type of SQL query (select, insert, update, delete, etc.)
        operation: Optional name of the database operation
        
    Returns:
        Decorated function that reports SQL timing metrics
        
    Example:
        @sql_query_timer("select", "get_jobs")
        def get_jobs_from_db(cursor, params):
            # Database query code
    """
    return timer(
        MetricNames.DB_QUERY_DURATION,
        {"type": query_type, "operation": operation, "database": "postgres"}
    )


def async_sql_query_timer(query_type: str, operation: str = "unknown") -> Callable:
    """
    Decorator to time async SQL query execution.
    
    Args:
        query_type: Type of SQL query (select, insert, update, delete, etc.)
        operation: Optional name of the database operation
        
    Returns:
        Decorated async function that reports SQL timing metrics
        
    Example:
        @async_sql_query_timer("select", "get_jobs_async")
        async def get_jobs_from_db_async(cursor, params):
            # Async database query code
    """
    return async_timer(
        MetricNames.DB_QUERY_DURATION,
        {"type": query_type, "operation": operation, "database": "postgres"}
    )


def mongo_operation_timer(operation_type: str, collection: str = "unknown") -> Callable:
    """
    Decorator to time MongoDB operation execution.
    
    Args:
        operation_type: Type of MongoDB operation (find, insert, update, etc.)
        collection: Name of the MongoDB collection
        
    Returns:
        Decorated function that reports MongoDB timing metrics
        
    Example:
        @mongo_operation_timer("find", "job_matches")
        def find_job_matches(query):
            # MongoDB query code
    """
    return timer(
        MetricNames.DB_QUERY_DURATION,
        {"type": operation_type, "collection": collection, "database": "mongodb"}
    )


def async_mongo_operation_timer(operation_type: str, collection: str = "unknown") -> Callable:
    """
    Decorator to time async MongoDB operation execution.
    
    Args:
        operation_type: Type of MongoDB operation (find, insert, update, etc.)
        collection: Name of the MongoDB collection
        
    Returns:
        Decorated async function that reports MongoDB timing metrics
        
    Example:
        @async_mongo_operation_timer("find", "job_matches")
        async def find_job_matches_async(query):
            # Async MongoDB query code
    """
    return async_timer(
        MetricNames.DB_QUERY_DURATION,
        {"type": operation_type, "collection": collection, "database": "mongodb"}
    )


def vector_operation_timer(operation_type: str, index: str = "unknown") -> Callable:
    """
    Decorator to time vector database operation execution.
    
    Args:
        operation_type: Type of vector operation (similarity, knn, etc.)
        index: Name of the vector index
        
    Returns:
        Decorated function that reports vector database timing metrics
        
    Example:
        @vector_operation_timer("similarity", "job_embeddings")
        def find_similar_jobs(embedding):
            # Vector similarity search code
    """
    return timer(
        MetricNames.DB_VECTORDB_OPERATION_DURATION,
        {"type": operation_type, "index": index, "database": "vectordb"}
    )


def async_vector_operation_timer(operation_type: str, index: str = "unknown") -> Callable:
    """
    Decorator to time async vector database operation execution.
    
    Args:
        operation_type: Type of vector operation (similarity, knn, etc.)
        index: Name of the vector index
        
    Returns:
        Decorated async function that reports vector database timing metrics
        
    Example:
        @async_vector_operation_timer("similarity", "job_embeddings")
        async def find_similar_jobs_async(embedding):
            # Async vector similarity search code
    """
    return async_timer(
        MetricNames.DB_VECTORDB_OPERATION_DURATION,
        {"type": operation_type, "index": index, "database": "vectordb"}
    )


def report_connection_pool_metrics(
    pool_name: str,
    used_connections: int,
    total_connections: int,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report connection pool utilization metrics.
    
    Args:
        pool_name: Name of the connection pool
        used_connections: Number of used connections
        total_connections: Total number of connections in the pool
        tags: Additional tags to include with the metrics
        
    Example:
        report_connection_pool_metrics(
            "postgres_main",
            5,
            10,
            {"database": "postgres"}
        )
    """
    if not settings.metrics_enabled:
        return
    
    # Calculate utilization percentage
    utilization_pct = 0
    if total_connections > 0:
        utilization_pct = (used_connections / total_connections) * 100
    
    # Combine tags
    combined_tags = {"pool": pool_name}
    if tags:
        combined_tags.update(tags)
    
    # Report metrics
    report_gauge(f"{MetricNames.DB_CONNECTION_POOL_USAGE}.used", used_connections, combined_tags)
    report_gauge(f"{MetricNames.DB_CONNECTION_POOL_USAGE}.total", total_connections, combined_tags)
    report_gauge(f"{MetricNames.DB_CONNECTION_POOL_USAGE}.percent", utilization_pct, combined_tags)
    
    # Log high utilization
    if utilization_pct > 80:
        logger.warning(
            "High database connection pool utilization",
            pool=pool_name,
            used=used_connections,
            total=total_connections,
            percent=utilization_pct
        )