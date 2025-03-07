"""
FastAPI middleware for collecting API metrics.

This module provides middleware for FastAPI applications to automatically
collect metrics for all API requests, including response times, request counts,
error rates, and concurrent request tracking.
"""

import time
import re
from typing import Dict, Callable, List, Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import (
    MetricNames,
    report_timing,
    report_gauge,
    increment_counter
)


# Track concurrent requests
_concurrent_requests = 0


class MetricsMiddleware(BaseHTTPMiddleware):
    """
    Middleware for collecting API metrics.
    
    This middleware tracks:
    - Request duration by endpoint and method
    - Request count by endpoint and method
    - Error rate by endpoint, method, and status code
    - Concurrent request count
    """
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[List[str]] = None
    ):
        """
        Initialize the metrics middleware.
        
        Args:
            app: The ASGI application
            exclude_paths: Optional list of path patterns to exclude from metrics
        """
        super().__init__(app)
        self.exclude_patterns = []
        if exclude_paths:
            self.exclude_patterns = [re.compile(pattern) for pattern in exclude_paths]
        
        # Patterns to normalize paths with IDs
        self.path_patterns = [
            (re.compile(r'/jobs/[0-9a-fA-F]+(?:/|$)'), '/jobs/{id}'),
            (re.compile(r'/users/[0-9a-fA-F]+(?:/|$)'), '/users/{id}'),
            (re.compile(r'/companies/[0-9a-fA-F]+(?:/|$)'), '/companies/{id}'),
            (re.compile(r'/resumes/[0-9a-fA-F]+(?:/|$)'), '/resumes/{id}'),
            # Add more patterns as needed
        ]
    
    def _should_skip_path(self, path: str) -> bool:
        """
        Check if the path should be excluded from metrics.
        
        Args:
            path: The request path
        
        Returns:
            True if the path should be excluded, False otherwise
        """
        # Skip static files and excluded paths
        if path.startswith(("/static/", "/docs/", "/redoc/", "/openapi.json")):
            return True
        
        # Check against exclude patterns
        for pattern in self.exclude_patterns:
            if pattern.match(path):
                return True
        
        return False
    
    def _normalize_path(self, path: str) -> str:
        """
        Normalize paths to prevent cardinality explosion.
        
        Converts paths like /jobs/123 to /jobs/{id}
        
        Args:
            path: The original request path
        
        Returns:
            Normalized path
        """
        normalized_path = path
        
        # Apply normalization patterns
        for pattern, replacement in self.path_patterns:
            normalized_path = pattern.sub(replacement, normalized_path)
        
        return normalized_path
    
    def _get_path_for_metrics(self, request: Request) -> str:
        """
        Get the normalized path for metrics reporting.
        
        Args:
            request: The request object
        
        Returns:
            Normalized path for metrics
        """
        path = request.url.path
        return self._normalize_path(path)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and collect metrics.
        
        Args:
            request: The request to process
            call_next: Function to call the next middleware or route handler
        
        Returns:
            Response from the next middleware or route handler
        """
        # Skip metrics for certain paths
        if not settings.metrics_enabled or self._should_skip_path(request.url.path):
            return await call_next(request)
        
        global _concurrent_requests
        
        # Get normalized path for metrics
        path = self._get_path_for_metrics(request)
        method = request.method
        
        # Basic tags for all metrics
        tags = {
            "path": path,
            "method": method
        }
        
        # Track concurrent requests
        _concurrent_requests += 1
        report_gauge(MetricNames.API_CONCURRENT_REQUESTS, _concurrent_requests)
        
        # Time the request processing
        start_time = time.time()
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Record request duration
            duration = time.time() - start_time
            status_code = response.status_code
            
            # Add status code to tags
            tags["status_code"] = str(status_code)
            
            # Log request details at debug level
            logger.debug(
                "API request",
                path=path,
                method=method,
                status_code=status_code,
                duration=duration
            )
            
            # Report timing metric
            report_timing(MetricNames.API_REQUEST_DURATION, duration, tags)
            
            # Count requests
            increment_counter(MetricNames.API_REQUEST_COUNT, tags)
            
            # Count errors (4xx and 5xx responses)
            if status_code >= 400:
                increment_counter(MetricNames.API_ERROR_RATE, tags)
                
                # Log client and server errors appropriately
                if status_code >= 500:
                    logger.error(
                        "Server error in API request",
                        path=path,
                        method=method,
                        status_code=status_code,
                        duration=duration
                    )
                else:
                    logger.warning(
                        "Client error in API request",
                        path=path,
                        method=method,
                        status_code=status_code,
                        duration=duration
                    )
            
            return response
        
        except Exception as e:
            # Record request duration for exceptions
            duration = time.time() - start_time
            
            # Add error tags
            tags["status_code"] = "500"
            tags["error"] = str(e.__class__.__name__)
            
            # Report timing for failed requests
            report_timing(MetricNames.API_REQUEST_DURATION, duration, tags)
            
            # Count requests
            increment_counter(MetricNames.API_REQUEST_COUNT, tags)
            
            # Count errors
            increment_counter(MetricNames.API_ERROR_RATE, tags)
            
            # Log the error
            logger.exception(
                "Exception in API request",
                path=path,
                method=method,
                error=str(e),
                duration=duration
            )
            
            # Re-raise the exception
            raise
        
        finally:
            # Decrement concurrent requests counter
            _concurrent_requests -= 1
            report_gauge(MetricNames.API_CONCURRENT_REQUESTS, _concurrent_requests)


def add_metrics_middleware(app, exclude_paths: Optional[List[str]] = None) -> None:
    """
    Add metrics middleware to a FastAPI application.
    
    Args:
        app: The FastAPI application
        exclude_paths: Optional list of path patterns to exclude from metrics
        
    Example:
        app = FastAPI()
        add_metrics_middleware(app, exclude_paths=[r'^/health$'])
    """
    if settings.metrics_enabled:
        # Log that we're adding metrics middleware
        logger.info(
            "Adding metrics middleware to FastAPI application",
            exclude_paths=exclude_paths
        )
        
        # Add the middleware
        app.add_middleware(MetricsMiddleware, exclude_paths=exclude_paths)