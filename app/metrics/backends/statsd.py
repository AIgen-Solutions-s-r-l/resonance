"""
StatsD metrics backend.

This module provides a backend for sending metrics to a StatsD server.
"""

import random
import socket
from typing import Dict, Optional, Union

from app.core.config import settings
from app.log.logging import logger


class StatsdMetricsBackend:
    """
    Backend for sending metrics to a StatsD server.
    
    This backend supports the following metric types:
    - Counters
    - Gauges
    - Timers
    - Histograms
    """
    
    def __init__(self) -> None:
        """Initialize the StatsD backend."""
        # Get settings
        self.host = settings.metrics_statsd_host
        self.port = settings.metrics_statsd_port
        self.default_sample_rate = settings.metrics_sample_rate
        
        # Create socket
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Maximum UDP packet size (safe default)
        self.max_packet_size = 512
        
        logger.info(
            f"StatsD metrics backend initialized",
            host=self.host,
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
            sample_rate: Sample rate
        """
        # Only send if we pass the sample rate check
        if not self._should_send(sample_rate):
            return
        
        # Create StatsD line
        line = f"{name}:{value}|c"
        
        # Add sample rate if not 1.0
        if sample_rate < 1.0:
            line += f"|@{sample_rate}"
            
        # Add tags if present
        if tags:
            tags_str = self._format_tags(tags)
            line += f"|#{tags_str}"
        
        # Send metric
        self._send(line)
    
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
            sample_rate: Sample rate
        """
        # Only send if we pass the sample rate check
        if not self._should_send(sample_rate):
            return
        
        # Create StatsD line
        line = f"{name}:{value}|g"
        
        # Add tags if present
        if tags:
            tags_str = self._format_tags(tags)
            line += f"|#{tags_str}"
        
        # Send metric
        self._send(line)
    
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
            sample_rate: Sample rate
        """
        # Only send if we pass the sample rate check
        if not self._should_send(sample_rate):
            return
        
        # Create StatsD line
        line = f"{name}:{value}|ms"
        
        # Add sample rate if not 1.0
        if sample_rate < 1.0:
            line += f"|@{sample_rate}"
            
        # Add tags if present
        if tags:
            tags_str = self._format_tags(tags)
            line += f"|#{tags_str}"
        
        # Send metric
        self._send(line)
    
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
            sample_rate: Sample rate
        """
        # Only send if we pass the sample rate check
        if not self._should_send(sample_rate):
            return
        
        # Create StatsD line
        line = f"{name}:{value}|h"
        
        # Add sample rate if not 1.0
        if sample_rate < 1.0:
            line += f"|@{sample_rate}"
            
        # Add tags if present
        if tags:
            tags_str = self._format_tags(tags)
            line += f"|#{tags_str}"
        
        # Send metric
        self._send(line)
    
    def _should_send(self, sample_rate: float) -> bool:
        """
        Check if we should send a metric based on sample rate.
        
        Args:
            sample_rate: Sample rate (0.0 to 1.0)
            
        Returns:
            True if we should send, False otherwise
        """
        # Always send if sample rate is 1.0
        if sample_rate >= 1.0:
            return True
        
        # Random check based on sample rate
        return random.random() < sample_rate
    
    def _format_tags(self, tags: Dict[str, str]) -> str:
        """
        Format tags for StatsD.
        
        Args:
            tags: Dictionary of tags
            
        Returns:
            Formatted tags string
        """
        return ",".join(f"{k}:{v}" for k, v in tags.items())
    
    def _send(self, line: str) -> None:
        """
        Send a metric line to StatsD.
        
        Args:
            line: StatsD metric line
        """
        try:
            # Encode and send
            bytes_to_send = line.encode("utf-8")
            
            # Check packet size
            if len(bytes_to_send) > self.max_packet_size:
                logger.warning(
                    "StatsD packet exceeds max size, truncating",
                    packet_size=len(bytes_to_send),
                    max_size=self.max_packet_size
                )
                bytes_to_send = bytes_to_send[:self.max_packet_size]
            
            # Send packet
            self.socket.sendto(bytes_to_send, (self.host, self.port))
            
        except Exception as e:
            logger.error(
                f"Error sending StatsD metric",
                error=str(e),
                line=line
            )