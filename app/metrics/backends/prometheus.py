"""
Prometheus metrics backend.

This module provides a backend for exposing metrics to Prometheus.
"""

from typing import Dict, Optional, Union, Set, Any
import threading

from prometheus_client import Counter, Gauge, Histogram, Summary, REGISTRY
from prometheus_client import start_http_server, exposition

from app.core.config import settings
from app.log.logging import logger


class PrometheusMetricsBackend:
    """
    Backend for exposing metrics to Prometheus.
    
    This backend supports the following metric types:
    - Counters
    - Gauges
    - Histograms
    - Timings (implemented as Summaries)
    """
    
    def __init__(self) -> None:
        """Initialize the Prometheus backend."""
        # Get settings
        self.prefix = settings.metrics_prefix or "app"
        self.port = settings.metrics_prometheus_port
        self.enabled = settings.metrics_enabled
        
        # Storage for metrics
        self._counters: Dict[str, Counter] = {}
        self._gauges: Dict[str, Gauge] = {}
        self._histograms: Dict[str, Histogram] = {}
        self._summaries: Dict[str, Summary] = {}
        
        # Track registered metric names to avoid duplicates
        self._registered_metrics: Set[str] = set()
        
        # Track tag keys for each metric
        self._metric_tag_keys: Dict[str, Set[str]] = {}
        
        # Lock for thread safety
        self._lock = threading.RLock()
        
        # Start HTTP server if enabled
        if self.enabled and self.port > 0:
            try:
                start_http_server(self.port)
                logger.info(
                    f"Prometheus metrics HTTP server started",
                    port=self.port
                )
            except Exception as e:
                logger.error(
                    f"Failed to start Prometheus metrics HTTP server",
                    error=str(e),
                    port=self.port
                )
        else:
            logger.info(
                f"Prometheus metrics HTTP server disabled",
                enabled=self.enabled,
                port=self.port
            )
    
    def increment_counter(
        self,
        name: str,
        tags: Optional[Dict[str, str]],
        value: int,
        sample_rate: float
    ) -> None:
        """
        Increment a counter metric.
        
        Args:
            name: Metric name
            tags: Optional tags
            value: Value to increment by
            sample_rate: Sample rate (ignored for Prometheus)
        """
        # Convert tags to label names and values
        label_names, label_values = self._get_labels(name, tags)
        
        # Get or create counter
        counter = self._get_counter(name, label_names)
        
        # Increment counter with labels
        counter.labels(*label_values).inc(value)
    
    def report_gauge(
        self,
        name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]],
        sample_rate: float
    ) -> None:
        """
        Report a gauge metric.
        
        Args:
            name: Metric name
            value: Gauge value
            tags: Optional tags
            sample_rate: Sample rate (ignored for Prometheus)
        """
        # Convert tags to label names and values
        label_names, label_values = self._get_labels(name, tags)
        
        # Get or create gauge
        gauge = self._get_gauge(name, label_names)
        
        # Set gauge with labels
        gauge.labels(*label_values).set(value)
    
    def report_timing(
        self,
        name: str,
        value: float,
        tags: Optional[Dict[str, str]],
        sample_rate: float
    ) -> None:
        """
        Report a timing metric.
        
        Args:
            name: Metric name
            value: Timing value in milliseconds
            tags: Optional tags
            sample_rate: Sample rate (ignored for Prometheus)
        """
        # Convert tags to label names and values
        label_names, label_values = self._get_labels(name, tags)
        
        # Get or create summary
        summary = self._get_summary(name, label_names)
        
        # Observe timing with labels (convert ms to seconds for Prometheus)
        summary.labels(*label_values).observe(value / 1000.0)
    
    def report_histogram(
        self,
        name: str,
        value: Union[int, float],
        tags: Optional[Dict[str, str]],
        sample_rate: float
    ) -> None:
        """
        Report a histogram metric.
        
        Args:
            name: Metric name
            value: Histogram value
            tags: Optional tags
            sample_rate: Sample rate (ignored for Prometheus)
        """
        # Convert tags to label names and values
        label_names, label_values = self._get_labels(name, tags)
        
        # Get or create histogram
        histogram = self._get_histogram(name, label_names)
        
        # Observe value with labels
        histogram.labels(*label_values).observe(value)
    
    def _get_labels(
        self,
        name: str,
        tags: Optional[Dict[str, str]]
    ) -> tuple[list[str], list[str]]:
        """
        Convert tags to Prometheus labels.
        
        Args:
            name: Metric name
            tags: Optional tags
            
        Returns:
            Tuple of (label_names, label_values)
        """
        if not tags:
            return [], []
        
        # Sort tag keys for consistent ordering
        label_names = sorted(tags.keys())
        label_values = [tags[k] for k in label_names]
        
        # Update tag keys for this metric
        with self._lock:
            if name not in self._metric_tag_keys:
                self._metric_tag_keys[name] = set(label_names)
            else:
                # Ensure we have all tag keys ever used with this metric
                self._metric_tag_keys[name].update(label_names)
        
        return label_names, label_values
    
    def _sanitize_name(self, name: str) -> str:
        """
        Sanitize a metric name for Prometheus.
        
        Args:
            name: Raw metric name
            
        Returns:
            Sanitized metric name
        """
        # Replace dots and hyphens with underscores
        name = name.replace(".", "_").replace("-", "_")
        
        # Add prefix
        if self.prefix and not name.startswith(f"{self.prefix}_"):
            name = f"{self.prefix}_{name}"
        
        return name
    
    def _get_counter(self, name: str, label_names: list[str]) -> Counter:
        """
        Get or create a Counter metric.
        
        Args:
            name: Metric name
            label_names: Label names
            
        Returns:
            Counter metric
        """
        with self._lock:
            # Sanitize name
            prom_name = self._sanitize_name(name)
            
            # Check if counter exists
            if prom_name in self._counters:
                return self._counters[prom_name]
            
            # Create new counter
            counter = Counter(
                prom_name,
                f"Counter for {name}",
                label_names
            )
            
            # Register counter
            self._counters[prom_name] = counter
            self._registered_metrics.add(prom_name)
            
            return counter
    
    def _get_gauge(self, name: str, label_names: list[str]) -> Gauge:
        """
        Get or create a Gauge metric.
        
        Args:
            name: Metric name
            label_names: Label names
            
        Returns:
            Gauge metric
        """
        with self._lock:
            # Sanitize name
            prom_name = self._sanitize_name(name)
            
            # Check if gauge exists
            if prom_name in self._gauges:
                return self._gauges[prom_name]
            
            # Create new gauge
            gauge = Gauge(
                prom_name,
                f"Gauge for {name}",
                label_names
            )
            
            # Register gauge
            self._gauges[prom_name] = gauge
            self._registered_metrics.add(prom_name)
            
            return gauge
    
    def _get_histogram(self, name: str, label_names: list[str]) -> Histogram:
        """
        Get or create a Histogram metric.
        
        Args:
            name: Metric name
            label_names: Label names
            
        Returns:
            Histogram metric
        """
        with self._lock:
            # Sanitize name
            prom_name = self._sanitize_name(name)
            
            # Check if histogram exists
            if prom_name in self._histograms:
                return self._histograms[prom_name]
            
            # Create new histogram with default buckets
            histogram = Histogram(
                prom_name,
                f"Histogram for {name}",
                label_names
            )
            
            # Register histogram
            self._histograms[prom_name] = histogram
            self._registered_metrics.add(prom_name)
            
            return histogram
    
    def _get_summary(self, name: str, label_names: list[str]) -> Summary:
        """
        Get or create a Summary metric.
        
        Args:
            name: Metric name
            label_names: Label names
            
        Returns:
            Summary metric
        """
        with self._lock:
            # Sanitize name
            prom_name = self._sanitize_name(name)
            
            # Check if summary exists
            if prom_name in self._summaries:
                return self._summaries[prom_name]
            
            # Create new summary
            summary = Summary(
                prom_name,
                f"Summary for {name}",
                label_names
            )
            
            # Register summary
            self._summaries[prom_name] = summary
            self._registered_metrics.add(prom_name)
            
            return summary

    @classmethod
    def generate_latest(cls) -> bytes:
        """
        Generate latest metrics output for all registered collectors.
        
        Returns:
            Metrics output as bytes
        """
        return exposition.generate_latest(REGISTRY)


def setup_metrics_endpoint(app: Any) -> None:
    """
    Set up a metrics endpoint for Prometheus.
    
    Args:
        app: FastAPI application
    """
    if not settings.metrics_enabled:
        return
    
    # Only import FastAPI if metrics are enabled
    from fastapi import FastAPI, Response
    
    if not isinstance(app, FastAPI):
        logger.error(
            "Cannot set up metrics endpoint: app is not a FastAPI instance",
            app_type=type(app)
        )
        return
    
    @app.get("/metrics")
    async def metrics() -> Response:
        """
        Expose Prometheus metrics endpoint.
        
        Returns:
            Response containing Prometheus metrics
        """
        return Response(
            content=PrometheusMetricsBackend.generate_latest(),
            media_type="text/plain"
        )
    
    logger.info("Prometheus metrics endpoint set up at /metrics")