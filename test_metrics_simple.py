#!/usr/bin/env python
"""
Simplified Metrics Test Script

A standalone script to test the metrics system without depending on the full application config.
"""

import random
import time
import socket
import os
import json
from typing import Dict, Any, Optional, List, Union

# Configure metrics directly
METRICS_ENABLED = True
METRICS_PREFIX = "matching_service"
STATSD_HOST = "127.0.0.1"
STATSD_PORT = 8125

# Simple StatsD client
class SimpleStatsDClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 8125, prefix: str = ""):
        self.host = host
        self.port = port
        self.prefix = prefix
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    def send(self, stat: str, value: Union[int, float], metric_type: str, 
             tags: Optional[Dict[str, str]] = None, sample_rate: float = 1.0):
        """Send a metric to StatsD."""
        if not METRICS_ENABLED:
            return
            
        # Add prefix if set
        if self.prefix:
            stat = f"{self.prefix}.{stat}"
            
        # Format sample rate if not 1.0
        rate_string = ""
        if sample_rate < 1.0:
            rate_string = f"|@{sample_rate}"
            
        # Format tags if provided
        tag_string = ""
        if tags:
            tag_string = "|#" + ",".join(f"{k}:{v}" for k, v in tags.items())
            
        # Create the full metric string
        metric = f"{stat}:{value}|{metric_type}{rate_string}{tag_string}"
        
        # Send via UDP
        try:
            self.socket.sendto(metric.encode('utf-8'), (self.host, self.port))
            print(f"Sent metric: {metric}")
        except Exception as e:
            print(f"Error sending metric: {e}")
    
    def timing(self, stat: str, value: float, tags: Optional[Dict[str, str]] = None, 
               sample_rate: float = 1.0):
        """Send a timing metric (in milliseconds)."""
        # Convert to milliseconds if value appears to be in seconds
        if value < 1000:  # Likely in seconds
            value = value * 1000
        self.send(stat, value, "ms", tags, sample_rate)
    
    def increment(self, stat: str, tags: Optional[Dict[str, str]] = None, 
                  sample_rate: float = 1.0):
        """Increment a counter."""
        self.send(stat, 1, "c", tags, sample_rate)
    
    def gauge(self, stat: str, value: Union[int, float], tags: Optional[Dict[str, str]] = None):
        """Send a gauge value."""
        self.send(stat, value, "g", tags)

# Create client instance
statsd = SimpleStatsDClient(STATSD_HOST, STATSD_PORT, METRICS_PREFIX)

# Simulation functions
def simulate_api_request():
    """Simulate an API request with timing."""
    print("Processing API request...")
    start_time = time.time()
    
    # Simulate processing time
    time.sleep(random.uniform(0.1, 0.3))
    
    duration = time.time() - start_time
    statsd.timing("api.request_duration", duration, {"endpoint": "/jobs/matches"})
    print(f"API request completed in {duration:.3f} seconds")

def simulate_matching_algorithm(num_jobs=10):
    """Simulate the matching algorithm."""
    print(f"Running matching algorithm for {num_jobs} jobs...")
    start_time = time.time()
    
    # Choose algorithm path
    algorithm_choice = random.choice(["vector_similarity", "cosine_distance", "l2_distance"])
    statsd.increment(f"algorithm.path.{algorithm_choice}", {"source": "test"})
    
    # Simulate processing time
    time.sleep(random.uniform(0.2, 0.5))
    
    # Generate random match scores
    scores = [random.uniform(0.3, 1.0) for _ in range(num_jobs)]
    
    duration = time.time() - start_time
    statsd.timing("algorithm.duration", duration, {"algorithm": algorithm_choice})
    statsd.gauge("algorithm.match_count", len(scores), {"source": "test"})
    
    # Report score distribution
    if scores:
        statsd.gauge("algorithm.score.avg", sum(scores) / len(scores), {"source": "test"})
        statsd.gauge("algorithm.score.min", min(scores), {"source": "test"})
        statsd.gauge("algorithm.score.max", max(scores), {"source": "test"})
    
    print(f"Matching completed with {len(scores)} results in {duration:.3f} seconds")
    return scores

def run_tests():
    """Run a series of tests to generate metrics."""
    print("=== Starting Metrics Test ===")
    
    # Test API timing
    for _ in range(3):
        simulate_api_request()
    
    # Test algorithm metrics
    for _ in range(2):
        scores = simulate_matching_algorithm(random.randint(5, 15))
    
    # Test direct metrics
    statsd.timing("database.query_time", random.uniform(0.05, 0.2), {"operation": "SELECT"})
    statsd.gauge("system.memory_usage", random.uniform(50, 80), {"unit": "percent"})
    statsd.increment("api.requests_total", {"endpoint": "/jobs/matches"})
    
    print("=== Metrics Test Completed ===")
    print("Check the StatsD server output to see the collected metrics")

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"Error in metrics test: {e}")
        raise