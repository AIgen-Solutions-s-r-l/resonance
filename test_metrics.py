#!/usr/bin/env python
"""
Test Metrics Script

A simplified script to test the metrics configuration and see immediate results in the StatsD server.
"""

import time
import random
from app.metrics import (
    timer,
    report_timing,
    report_gauge,
    increment_counter,
    matching_algorithm_timer,
    report_match_score_distribution,
    report_algorithm_path,
    report_match_count
)
from app.core.config import settings
from app.log.logging import logger

# Enable metrics for testing
settings.metrics_enabled = True
settings.metrics_debug = True

@timer("api.request_duration")
def simulate_api_request():
    """Simulate an API request with timing."""
    logger.info("Processing API request...")
    # Simulate processing time
    time.sleep(random.uniform(0.1, 0.3))
    logger.info("API request completed")

@matching_algorithm_timer("vector_similarity")
def simulate_matching_algorithm(num_jobs=10):
    """Simulate the matching algorithm."""
    logger.info(f"Running matching algorithm for {num_jobs} jobs...")
    
    # Choose algorithm path
    algorithm_choice = random.choice(["vector_similarity", "cosine_distance", "l2_distance"])
    report_algorithm_path(algorithm_choice, {"source": "test"})
    
    # Simulate processing time
    time.sleep(random.uniform(0.2, 0.5))
    
    # Generate random match scores
    scores = [random.uniform(0.3, 1.0) for _ in range(num_jobs)]
    
    logger.info(f"Matching completed with {len(scores)} results")
    return scores

def run_tests():
    """Run a series of tests to generate metrics."""
    logger.info("=== Starting Metrics Test ===")
    
    # Test API timing
    for _ in range(3):
        simulate_api_request()
    
    # Test algorithm metrics
    for _ in range(2):
        scores = simulate_matching_algorithm(random.randint(5, 15))
        report_match_score_distribution(scores, {"source": "test"})
        report_match_count(len(scores), {"source": "test"})
    
    # Test direct metrics
    report_timing("database.query_time", random.uniform(0.05, 0.2), {"operation": "SELECT"})
    report_gauge("system.memory_usage", random.uniform(50, 80), {"unit": "percent"})
    increment_counter("api.requests_total", {"endpoint": "/jobs/matches"})
    
    logger.info("=== Metrics Test Completed ===")
    logger.info("Check the StatsD server output to see the collected metrics")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        logger.error(f"Error in metrics test: {e}")
        raise