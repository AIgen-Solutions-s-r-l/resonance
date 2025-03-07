"""
Metrics backends package.

This package contains backends for different metrics systems.
"""

# Import backends for easy access
from app.metrics.backends.statsd import StatsdMetricsBackend
from app.metrics.backends.prometheus import PrometheusMetricsBackend, setup_metrics_endpoint