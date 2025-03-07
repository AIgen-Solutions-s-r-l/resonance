"""
Metrics backends package.

This package contains backends for different metrics systems.
"""

# Import backends for easy access
from app.metrics.backends.statsd import StatsDBackend
from app.metrics.backends.prometheus import PrometheusBackend, setup_metrics_endpoint