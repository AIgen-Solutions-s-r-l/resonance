"""
Algorithm-specific metrics collection and reporting.

This module provides specialized metrics tools for measuring matching algorithm
performance, including timing decorators, score distribution reporting, and
algorithm path tracking.
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
    increment_counter,
    report_statistical_metrics
)


# Type variable for function return values
T = TypeVar('T')


def matching_algorithm_timer(algorithm_name: str) -> Callable:
    """
    Decorator to time matching algorithm execution.
    
    Args:
        algorithm_name: Name of the matching algorithm
        
    Returns:
        Decorated function that reports algorithm timing metrics
        
    Example:
        @matching_algorithm_timer("vector_similarity")
        def match_with_vector_similarity(resume, jobs):
            # Algorithm code
    """
    return timer(
        MetricNames.ALGORITHM_MATCHING_DURATION,
        {"algorithm": algorithm_name}
    )


def async_matching_algorithm_timer(algorithm_name: str) -> Callable:
    """
    Decorator to time async matching algorithm execution.
    
    Args:
        algorithm_name: Name of the matching algorithm
        
    Returns:
        Decorated async function that reports algorithm timing metrics
        
    Example:
        @async_matching_algorithm_timer("vector_similarity")
        async def match_with_vector_similarity_async(resume, jobs):
            # Async algorithm code
    """
    return async_timer(
        MetricNames.ALGORITHM_MATCHING_DURATION,
        {"algorithm": algorithm_name}
    )


def report_match_score_distribution(
    scores: List[float],
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report statistical metrics for job match scores.
    
    Args:
        scores: List of job match scores (typically between 0 and 1)
        tags: Optional tags to include with the metrics
        
    Example:
        report_match_score_distribution(
            [0.75, 0.82, 0.91, 0.65],
            {"algorithm": "vector_similarity"}
        )
    """
    if not settings.metrics_enabled or not scores:
        return
    
    # Report statistical metrics
    report_statistical_metrics(MetricNames.ALGORITHM_MATCH_SCORE, scores, tags)
    
    # Report match count
    report_gauge(MetricNames.ALGORITHM_MATCH_COUNT, len(scores), tags)
    
    # Report bucketized score distribution
    # Create buckets for score ranges (0.0-0.1, 0.1-0.2, etc.)
    buckets = {f"{i/10:.1f}-{(i+1)/10:.1f}": 0 for i in range(10)}
    
    for score in scores:
        # Handle edge case of score exactly 1.0
        if score >= 1.0:
            bucket_key = "0.9-1.0"
        else:
            bucket_index = int(score * 10)
            bucket_key = f"{bucket_index/10:.1f}-{(bucket_index+1)/10:.1f}"
        
        buckets[bucket_key] += 1
    
    # Report counts for each bucket
    for bucket, count in buckets.items():
        bucket_tags = tags.copy() if tags else {}
        bucket_tags["bucket"] = bucket
        report_gauge(f"{MetricNames.ALGORITHM_MATCH_SCORE}.bucket", count, bucket_tags)


def report_algorithm_path(
    path_name: str,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report algorithm path usage metric.
    
    Use this to track which algorithm paths are being used in the matching
    process, which can be useful for understanding algorithm behavior
    and optimizing performance.
    
    Args:
        path_name: Name of the algorithm path
        tags: Optional tags to include with the metric
        
    Example:
        report_algorithm_path("cosine_distance", {"reason": "better_for_sparse_vectors"})
    """
    if not settings.metrics_enabled:
        return
    
    # Combine tags
    combined_tags = {"path": path_name}
    if tags:
        combined_tags.update(tags)
    
    # Report path usage
    increment_counter(MetricNames.ALGORITHM_PATH_USAGE, combined_tags)


def report_match_count(
    count: int,
    tags: Optional[Dict[str, str]] = None
) -> None:
    """
    Report the number of matches returned by an algorithm.
    
    Args:
        count: Number of job matches returned
        tags: Optional tags to include with the metric
        
    Example:
        report_match_count(12, {"algorithm": "vector_similarity"})
    """
    if not settings.metrics_enabled:
        return
    
    report_gauge(MetricNames.ALGORITHM_MATCH_COUNT, count, tags)