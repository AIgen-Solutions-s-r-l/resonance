"""
FastAPI middleware for metrics collection.

This module provides middleware for collecting metrics related
to HTTP requests and responses in FastAPI applications.
"""

import time
from typing import Callable, Dict, Optional, Union

from fastapi import FastAPI, Request, Response
from fastapi.responses import Response as FastAPIResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

from app.core.config import settings
from app.log.logging import logger
from app.metrics.core import increment_counter, report_gauge, report_timing


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware for collecting request/response metrics."""
    
    def __init__(
        self,
        app: ASGIApp,
        exclude_paths: Optional[list[str]] = None
    ) -> None:
        """
        Initialize metrics middleware.
        
        Args:
            app: FastAPI application
            exclude_paths: List of paths to exclude from metrics collection
        """
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/metrics", "/health", "/healthcheck"]
        
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Process a request and collect metrics.
        
        Args:
            request: HTTP request
            call_next: Next middleware or route handler
            
        Returns:
            HTTP response
        """
        # Skip if metrics are disabled
        if not settings.metrics_enabled:
            return await call_next(request)
        
        # Check if path should be excluded
        path = request.url.path
        if any(path.startswith(exclude) for exclude in self.exclude_paths):
            return await call_next(request)
        
        # Extract route information
        route = getattr(request.scope.get("route"), "path", "unknown")
        method = request.method
        
        # Prepare tags
        tags = {
            "method": method,
            "route": route,
            "path": path
        }
        
        # Start timer
        start_time = time.time()
        
        # Track request size
        try:
            content_length = request.headers.get("content-length")
            if content_length:
                request_size = int(content_length)
                report_gauge("http.request.size", request_size, tags)
        except (ValueError, TypeError):
            pass
        
        # Increment request counter
        increment_counter("http.requests", tags)
        
        try:
            # Process request
            response = await call_next(request)
            
            # Calculate duration
            duration = time.time() - start_time
            duration_ms = duration * 1000.0
            
            # Add status code tag
            status_code = response.status_code
            status_range = f"{status_code // 100}xx"
            
            tags.update({
                "status_code": str(status_code),
                "status_range": status_range
            })
            
            # Report timing
            report_timing("http.request.duration", duration_ms, tags)
            
            # Track slow requests
            if duration_ms > settings.slow_request_threshold_ms:
                # Create detailed tags for slow requests
                slow_tags = tags.copy()
                slow_tags["slow"] = "true"
                slow_tags["duration_range"] = f"{int(duration_ms / 1000)}s" # Duration in seconds range
                
                # Add request details as tags
                try:
                    # Extract query parameters
                    query_params = dict(request.query_params)
                    if query_params:
                        slow_tags["has_query_params"] = "true"
                except Exception:
                    pass
                
                # Record slow request counter with detailed tags
                increment_counter("http.requests.slow", slow_tags)
                
                # Record actual duration of slow request as a gauge
                report_gauge("http.requests.slow.duration_ms", duration_ms, slow_tags)
                
                # Record detailed information about the slow request
                logger.warning(
                    "Slow HTTP request",
                    path=path,
                    route=route,
                    method=method,
                    duration_ms=duration_ms,
                    duration_seconds=duration_ms/1000,
                    threshold_ms=settings.slow_request_threshold_ms,
                    request_id=request.headers.get("x-request-id", "unknown"),
                    query_params=dict(request.query_params)
                )
            
            # Track response size
            try:
                resp_content_length = response.headers.get("content-length")
                if resp_content_length:
                    response_size = int(resp_content_length)
                    report_gauge("http.response.size", response_size, tags)
            except (ValueError, TypeError):
                pass
            
            # Add timing header if enabled
            if settings.include_timing_header:
                response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"
            
            return response
            
        except Exception as e:
            # Calculate duration for errors
            duration = time.time() - start_time
            duration_ms = duration * 1000.0
            
            # Add error tags
            error_tags = tags.copy()
            error_tags.update({
                "status_code": "500",
                "status_range": "5xx",
                "error": "true",
                "error_type": e.__class__.__name__
            })
            
            # Report timing for errors
            report_timing("http.request.duration", duration_ms, error_tags)
            
            # Increment error counter
            increment_counter("http.errors", error_tags)
            
            # Log error
            logger.error(
                "Error processing HTTP request",
                path=path,
                route=route,
                method=method,
                error=str(e),
                error_type=e.__class__.__name__
            )
            
            # Re-raise the exception
            raise


def add_metrics_middleware(app: FastAPI) -> None:
    """
    Add metrics middleware to FastAPI application.
    
    Args:
        app: FastAPI application
    """
    if not settings.metrics_enabled:
        logger.info("Metrics collection is disabled")
        return
    
    try:
        # Add metrics middleware
        app.add_middleware(MetricsMiddleware)
        
        logger.info("Added metrics middleware to application")
        
    except RuntimeError as e:
        # Check for the specific "app already started" error
        if "after an application has started" in str(e):
            logger.warning(
                "Application has already started - metrics middleware will not be added. "
                "This is expected during application lifecycle events.",
                error=str(e)
            )
        else:
            # Re-raise other RuntimeErrors
            logger.error(
                "Failed to add metrics middleware: unexpected runtime error",
                error=str(e)
            )
            raise
    except Exception as e:
        logger.error(
            "Failed to add metrics middleware",
            error=str(e)
        )


class RouteMetrics:
    """Helper for collecting route-specific metrics."""
    
    @staticmethod
    def track_request(
        route_name: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Track an API request.
        
        Args:
            route_name: Name of the route
            tags: Additional tags
        """
        if not settings.metrics_enabled:
            return
        
        try:
            # Create tags
            metric_tags = {
                "route": route_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment request counter
            increment_counter("http.routes.requests", metric_tags)
            
        except Exception as e:
            if settings.metrics_debug:
                logger.error(
                    "Failed to track route request",
                    error=str(e)
                )
    
    @staticmethod
    def record_timing(
        route_name: str,
        duration_ms: float,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Record route timing.
        
        Args:
            route_name: Name of the route
            duration_ms: Duration in milliseconds
            tags: Additional tags
        """
        if not settings.metrics_enabled:
            return
        
        try:
            # Create tags
            metric_tags = {
                "route": route_name
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Report timing
            report_timing("http.routes.duration", duration_ms, metric_tags)
            
            # Track slow requests
            if duration_ms > settings.slow_request_threshold_ms:
                slow_tags = metric_tags.copy()
                slow_tags["slow"] = "true"
                
                increment_counter("http.routes.slow", slow_tags)
                
                logger.warning(
                    "Slow route execution",
                    route=route_name,
                    duration_ms=duration_ms,
                    threshold_ms=settings.slow_request_threshold_ms
                )
            
        except Exception as e:
            if settings.metrics_debug:
                logger.error(
                    "Failed to record route timing",
                    error=str(e)
                )
    
    @staticmethod
    def track_error(
        route_name: str,
        error_type: str,
        tags: Optional[Dict[str, str]] = None
    ) -> None:
        """
        Track a route error.
        
        Args:
            route_name: Name of the route
            error_type: Type of error
            tags: Additional tags
        """
        if not settings.metrics_enabled:
            return
        
        try:
            # Create tags
            metric_tags = {
                "route": route_name,
                "error_type": error_type
            }
            
            # Add custom tags
            if tags:
                metric_tags.update(tags)
            
            # Increment error counter
            increment_counter("http.routes.errors", metric_tags)
            
        except Exception as e:
            if settings.metrics_debug:
                logger.error(
                    "Failed to track route error",
                    error=str(e)
                )


def route_metrics_timer(
    route_name: str,
    tags: Optional[Dict[str, str]] = None
) -> Callable:
    """
    Decorator for tracking route timing.
    
    Args:
        route_name: Name of the route
        tags: Additional tags
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Skip if metrics disabled
            if not settings.metrics_enabled:
                return await func(*args, **kwargs)
            
            # Record start time
            start_time = time.time()
            
            try:
                # Track request
                RouteMetrics.track_request(route_name, tags)
                
                # Execute function
                result = await func(*args, **kwargs)
                
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Record timing
                RouteMetrics.record_timing(route_name, duration_ms, tags)
                
                return result
                
            except Exception as e:
                # Calculate duration
                duration = time.time() - start_time
                duration_ms = duration * 1000.0
                
                # Record timing with error
                error_tags = tags.copy() if tags else {}
                error_tags["error"] = "true"
                
                RouteMetrics.record_timing(route_name, duration_ms, error_tags)
                
                # Track error
                RouteMetrics.track_error(route_name, e.__class__.__name__, tags)
                
                # Re-raise the exception
                raise
                
        return wrapper
    return decorator


def add_timing_header_middleware(app: FastAPI) -> None:
    """
    Add middleware that adds timing information to response headers.
    
    Args:
        app: FastAPI application
    """
    if not settings.metrics_enabled:
        logger.info("Timing header middleware is disabled (metrics disabled)")
        return
    
    class TimingHeaderMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
            start_time = time.time()
            response = await call_next(request)
            process_time = time.time() - start_time
            process_time_ms = process_time * 1000
            
            # Add timing header to response
            response.headers["X-Process-Time"] = f"{process_time_ms:.2f}ms"
            
            # Report timing metric
            if settings.metrics_enabled:
                tags = {
                    "method": request.method,
                    "path": request.url.path
                }
                report_timing("http.request.processing_time", process_time_ms, tags)
                
            return response
    
    try:
        app.add_middleware(TimingHeaderMiddleware)
        logger.info("Added timing header middleware to application")
    except RuntimeError as e:
        # Check for the specific "app already started" error
        if "after an application has started" in str(e):
            logger.warning(
                "Application has already started - timing header middleware will not be added. "
                "This is expected during application lifecycle events.",
                error=str(e)
            )
        else:
            # Re-raise other RuntimeErrors
            logger.error(
                "Failed to add timing header middleware: unexpected runtime error",
                error=str(e)
            )
            raise
    except Exception as e:
        logger.error(
            "Failed to add timing header middleware",
            error=str(e)
        )


def setup_all_middleware(app: FastAPI) -> None:
    """
    Set up all metrics-related middleware for the application.
    
    This function adds all metrics middleware components to the
    FastAPI application in the correct order.
    
    Args:
        app: FastAPI application
    """
    if not settings.metrics_enabled:
        logger.info("Metrics middleware setup skipped (metrics disabled)")
        return
    
    try:
        # Add standard metrics middleware
        add_metrics_middleware(app)
        
        # Add timing header middleware if configured
        if settings.include_timing_header:
            add_timing_header_middleware(app)
            
        logger.info("All metrics middleware setup complete")
    except Exception as e:
        logger.error(
            "Failed to set up metrics middleware",
            error=str(e)
        )