"""
Metrics system for the matching service.

This package provides a comprehensive metrics system for tracking API performance,
database operations, and matching algorithm efficiency. It exposes decorators,
context managers, and direct reporting functions for easy integration.
"""

# Core metrics functionality
from app.metrics.core import (
    # Constants
    MetricNames,
    
    # Decorators
    timer,
    async_timer,
    
    # Context managers
    Timer,
    ProcessingTimer,
    
    # Direct reporting functions
    report_timing,
    report_gauge,
    increment_counter,
    report_statistical_metrics,
)

# Algorithm-specific metrics
from app.metrics.algorithm import (
    # Decorators
    matching_algorithm_timer,
    async_matching_algorithm_timer,
    
    # Direct reporting functions
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count,
)

# Database-specific metrics
from app.metrics.database import (
    # Decorators
    sql_query_timer,
    async_sql_query_timer,
    mongo_operation_timer,
    async_mongo_operation_timer,
    vector_operation_timer,
    async_vector_operation_timer,
    
    # Direct reporting functions
    report_connection_pool_metrics,
)

# API middleware
from app.metrics.middleware import add_metrics_middleware

__all__ = [
    # Core metrics
    "MetricNames",
    "timer",
    "async_timer",
    "Timer",
    "ProcessingTimer",
    "report_timing",
    "report_gauge",
    "increment_counter",
    "report_statistical_metrics",
    
    # Algorithm metrics
    "matching_algorithm_timer",
    "async_matching_algorithm_timer",
    "report_match_score_distribution",
    "report_algorithm_path",
    "report_match_count",
    
    # Database metrics
    "sql_query_timer",
    "async_sql_query_timer",
    "mongo_operation_timer",
    "async_mongo_operation_timer",
    "vector_operation_timer",
    "async_vector_operation_timer",
    "report_connection_pool_metrics",
    
    # API middleware
    "add_metrics_middleware",
]