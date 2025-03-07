"""
FastAPI metrics middleware.

This module provides middleware for collecting HTTP request metrics in FastAPI.
"""

import time
from typing import Any, Awaitable, Callable, Dict, Optional

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import increment_counter, report_timing


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting HTTP request metrics."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list[str]] = None
    ) -> None:
        """
        Initialize the metrics middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from metrics
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/ping"]
    
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        """
        Process a request and collect metrics.
        
        Args:
            request: FastAPI request
            call_next: Function to call next middleware
            
        Returns:
            FastAPI response
        """
        # Skip if metrics disabled
        if not settings.metrics_enabled:
            return await call_next(request)
        
        # Get request path
        path = request.url.path
        
        # Skip excluded paths
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            return await call_next(request)
        
        # Create tags
        tags = {
            "method": request.method,
            "path": path
        }
        
        # Get route
        route = getattr(request, "route", None)
        route_path = getattr(route, "path", "") if route else ""
        if route_path:
            tags["route"] = route_path
        
        # Add app name if available
        app_name = settings.metrics_app_name or settings.app_name
        if app_name:
            tags["app"] = app_name
        
        # Start timing
        start_time = time.time()
        
        # Increment request counter
        increment_counter("http.requests", tags)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Get status code
            status_code = response.status_code
            
            # Update tags with status code
            tags["status"] = str(status_code)
            
            # Add status code range
            status_range = f"{status_code // 100}xx"
            tags["status_range"] = status_range
            
            # Calculate request duration
            duration = time.time() - start_time
            duration_ms = duration * 1000.0
            
            # Report request duration
            report_timing("http.request.duration", duration_ms, tags)
            
            # Increment status counter
            increment_counter("http.status", tags)
            
            return response
            
        except Exception as e:
            # Calculate request duration
            duration = time.time() - start_time
            duration_ms = duration * 1000.0
            
            # Update tags for error
            tags["status"] = "500"
            tags["status_range"] = "5xx"
            tags["error"] = e.__class__.__name__
            
            # Report request duration with error tags
            report_timing("http.request.duration", duration_ms, tags)
            
            # Increment error counter
            increment_counter("http.errors", tags)
            
            # Re-raise the exception
            raise


def add_metrics_middleware(app: FastAPI) -> None:
    """
    Add metrics middleware to a FastAPI application.
    
    Args:
        app: FastAPI application
    """
    if not settings.metrics_enabled:
        return
    
    try:
        # Add middleware
        app.add_middleware(MetricsMiddleware)
        
        logger.info("Metrics middleware added to FastAPI application")
        
    except Exception as e:
        logger.error(
            "Failed to add metrics middleware",
            error=str(e)
        )


def add_timing_header_middleware(app: FastAPI) -> None:
    """
    Add middleware to include request timing in response headers.
    
    Args:
        app: FastAPI application
    """
    if not settings.metrics_enabled or not settings.include_timing_header:
        return
    
    try:
        # Create middleware
        @app.middleware("http")
        async def add_timing_header(request: Request, call_next: Callable) -> Response:
            # Start timing
            start_time = time.time()
            
            # Process request
            response = await call_next(request)
            
            # Calculate request duration
            duration = time.time() - start_time
            duration_ms = duration * 1000.0
            
            # Add timing header
            response.headers["X-Request-Time-Ms"] = f"{duration_ms:.2f}"
            
            return response
        
        logger.info("Timing header middleware added to FastAPI application")
        
    except Exception as e:
        logger.error(
            "Failed to add timing header middleware",
            error=str(e)
        )


def setup_all_middleware(app: FastAPI) -> None:
    """
    Set up all metrics middleware for a FastAPI application.
    
    Args:
        app: FastAPI application
    """
    add_metrics_middleware(app)
    add_timing_header_middleware(app)