#!/usr/bin/env python
"""
Metrics Demo Script

This script demonstrates how to use the metrics system in the matching service.
It simulates different operations and shows how to use various metrics components.

Usage:
    python demo_metrics.py
"""

import random
import time
from typing import List, Dict, Any
import asyncio

from app.metrics import (
    # Core metrics
    MetricNames,
    timer,
    Timer,
    report_timing,
    report_gauge,
    increment_counter,
    
    # Algorithm metrics
    matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count,
    
    # Database metrics
    sql_query_timer,
    mongo_operation_timer,
)
from app.core.config import settings
from app.log.logging import logger


# Enable metrics for demo
settings.metrics_enabled = True


@timer("demo.simple_operation")
def simple_operation() -> None:
    """Demonstrate a simple timed operation using the timer decorator."""
    logger.info("Starting simple operation...")
    time.sleep(random.uniform(0.1, 0.3))
    logger.info("Simple operation completed")


@timer("demo.complex_operation", {"operation_type": "complex"})
def complex_operation(iterations: int) -> None:
    """Demonstrate a more complex timed operation with tags."""
    logger.info(f"Starting complex operation with {iterations} iterations...")
    
    for i in range(iterations):
        # Report progress as a gauge
        report_gauge("demo.progress", i, {"operation": "complex", "total": str(iterations)})
        
        # Simulate varying operation times
        time.sleep(random.uniform(0.05, 0.15))
        
        # Increment a counter for each iteration
        increment_counter("demo.iterations", {"operation": "complex"})
    
    logger.info("Complex operation completed")


@matching_algorithm_timer("vector_similarity")
def simulate_matching_algorithm(num_jobs: int) -> List[float]:
    """Simulate a matching algorithm and return match scores."""
    logger.info(f"Simulating matching algorithm with {num_jobs} jobs...")
    
    # Choose algorithm path
    if random.random() > 0.7:
        report_algorithm_path("cosine_similarity", {"reason": "sparse_vectors"})
    else:
        report_algorithm_path("euclidean_distance", {"reason": "dense_vectors"})
    
    # Simulate processing time
    time.sleep(random.uniform(0.2, 0.5))
    
    # Generate random match scores (typically 0.0 to 1.0)
    scores = [random.uniform(0.3, 1.0) for _ in range(num_jobs)]
    
    logger.info(f"Matching algorithm completed with average score: {sum(scores)/len(scores):.2f}")
    return scores


@sql_query_timer("SELECT")
def simulate_database_query() -> List[Dict[str, Any]]:
    """Simulate a database query."""
    logger.info("Executing database query...")
    
    # Simulate query execution time
    time.sleep(random.uniform(0.1, 0.4))
    
    # Simulate query results
    results = [
        {"id": i, "name": f"Result {i}", "score": random.uniform(0.5, 1.0)}
        for i in range(1, random.randint(5, 15))
    ]
    
    logger.info(f"Database query returned {len(results)} results")
    return results


@mongo_operation_timer("find")
def simulate_mongo_operation() -> Dict[str, Any]:
    """Simulate a MongoDB operation."""
    logger.info("Executing MongoDB operation...")
    
    # Simulate operation time
    time.sleep(random.uniform(0.05, 0.3))
    
    # Simulate document
    document = {
        "_id": f"doc_{random.randint(1000, 9999)}",
        "created_at": time.time(),
        "data": {
            "field1": random.randint(1, 100),
            "field2": "sample_text",
            "field3": [random.random() for _ in range(5)]
        }
    }
    
    logger.info("MongoDB operation completed")
    return document


def demonstrate_timer_context_manager() -> None:
    """Demonstrate using Timer as a context manager."""
    logger.info("Demonstrating Timer context manager...")
    
    with Timer("demo.context_manager", {"method": "with_statement"}):
        time.sleep(random.uniform(0.1, 0.3))
    
    logger.info("Timer context manager demo completed")


def run_demo() -> None:
    """Run the complete metrics demo."""
    logger.info("=== Starting Metrics Demo ===")
    
    # Simple operation with timer decorator
    simple_operation()
    
    # Complex operation with timer decorator and tags
    complex_operation(5)
    
    # Timer as a context manager
    demonstrate_timer_context_manager()
    # Algorithm metrics
    scores = simulate_matching_algorithm(10)
    report_match_score_distribution(scores, {"algorithm": "vector_similarity"})
    report_match_count(len(scores), {"algorithm": "vector_similarity", "source": "demo"})
    
    
    # Database metrics
    simulate_database_query()
    simulate_mongo_operation()
    
    # Direct metric reporting
    report_timing("demo.manual_timing", random.uniform(0.1, 0.5), {"method": "direct"})
    report_gauge("demo.random_value", random.uniform(0, 100), {"source": "demo"})
    increment_counter("demo.completed", {"success": "true"})
    
    logger.info("=== Metrics Demo Completed ===")
    logger.info("Check your metrics backend for the collected metrics.")
    logger.info("If using Datadog, metrics will be prefixed with 'matching_service.'")


if __name__ == "__main__":
    try:
        run_demo()
    except Exception as e:
        logger.error(f"Error in metrics demo: {e}")
        raise