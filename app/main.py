from typing import Dict
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from jose import jwt

from app.log.logging import logger
from app.routers.jobs_matched_router_async import router as jobs_router
from app.core.config import settings
from app.metrics import setup_metrics
from app.metrics.system import collect_system_metrics
from app.tasks.job_processor import setup_task_manager, teardown_task_manager
from app.utils.db_utils import get_connection_pool, close_all_connection_pools
from app.libs.redis.factory import RedisCacheFactory
from app.libs.job_matcher.cache import initialize_cache as initialize_job_matcher_cache


class AuthDebugMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request details
        path = request.url.path
        
        # Only log auth-related details for endpoints that need authentication
        if path.startswith("/jobs/"):
            # Extract and log authorization header (if present)
            auth_header = request.headers.get("Authorization", "")
            token_preview = ""
            if auth_header:
                # Extract token from "Bearer <token>"
                parts = auth_header.split()
                if len(parts) == 2 and parts[0].lower() == "bearer":
                    token = parts[1]
                    token_preview = token[:10] + "..." if len(token) > 10 else token
                    
                    # Try to decode token without verification for debugging
                    try:
                        # Don't verify signature here, just decode to see payload
                        # But still need to provide the key parameter
                        decoded = jwt.decode(token, settings.secret_key, options={"verify_signature": False})
                        logger.info(
                            "Auth header present for {path}. Token preview: {token_preview}. Decoded token: {decoded}",
                            path=path,
                            token_preview=token_preview,
                            decoded=decoded
                        )
                    except Exception as e:
                        logger.exception("Could not decode token for debugging")
                else:
                    logger.debug(
                        "Malformed Authorization header for {path}: {auth_header}",
                        path=path,
                        auth_header=auth_header
                    )
            else:
                logger.debug("No Authorization header present for {path}", path=path)
        
        # Process the request and get response
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response status for auth issues
        if response.status_code == 401:
            logger.debug(
                "401 Unauthorized response for {path}",
                path=path
            )
            if path.startswith("/jobs/"):
                # Log the configured secret key (partial)
                secret_preview = settings.secret_key[:3] + "..." if settings.secret_key else "Not set"
                logger.debug(
                    "Auth configuration: algorithm={algorithm}, "
                    "secret_key_preview={secret_preview}",
                    algorithm=settings.algorithm,
                    secret_preview=secret_preview
                )
        
        return response


async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.

    Args:
        app: FastAPI application instance
    """

    try:
        logger.info("Starting application")
        
        # Only start collection threads and report metrics
        # (middleware already added before app creation)
        from app.metrics.core import initialize_metrics
        from app.metrics.tasks import start_metrics_collection
        
        # Initialize metrics core if needed
        initialize_metrics()
        
        # Start collection threads
        if settings.metrics_collection_enabled:
            start_metrics_collection()
        
        # Report initial system metrics
        collect_system_metrics()
        
        # Initialize task manager for background job processing
        await setup_task_manager()
        logger.info("Task manager initialized")
        
        # Initialize database connection pools
        logger.info("Initializing database connection pools")
        await get_connection_pool("default")  # Create the default connection pool
        logger.info("Database connection pools initialized")
        
        # Initialize Redis cache
        logger.info("Initializing Redis cache")
        try:
            await RedisCacheFactory.initialize()
            await initialize_job_matcher_cache()
            logger.info("Redis cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Redis cache: {str(e)}")
            logger.info("Job matching will use in-memory cache as fallback")
        
        logger.info("Application started successfully")
        
        yield
        
        # Application shutdown
        logger.info("Shutting down application")
        
        # Stop metrics collection
        from app.metrics import stop_metrics_collection
        stop_metrics_collection()
        
        # Cleanup task manager
        await teardown_task_manager()
        logger.info("Task manager shutdown completed")
        # Close database connection pools
        logger.info("Closing database connection pools")
        await close_all_connection_pools()
        logger.info("Database connection pools closed")
        
        # Close Redis connections
        logger.info("Closing Redis connections")
        try:
            await RedisCacheFactory.close()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.error(f"Error closing Redis connections: {str(e)}")
        
        
        logger.info("Application shut down successfully")
        
    except Exception as e:
        logger.exception("Application lifecycle error: {error}", error=str(e))
        raise


# Create the app first before any middleware is added
from fastapi import FastAPI

# Create the app
app = FastAPI(
    lifespan=lifespan,
    title="Job Matching API",
    description="API for matching jobs with user resumes.",
    version="1.0.0",
)

# Now initialize metrics
from app.metrics import setup_metrics, setup_all_middleware
from app.metrics.middleware import MetricsMiddleware, add_timing_header_middleware
from app.core.config import settings

# Add metrics middleware manually
if settings.metrics_enabled:
    try:
        # Add metrics middleware directly
        app.add_middleware(MetricsMiddleware)
        logger.info("Added metrics middleware to application")
        
        # Add timing header middleware if configured
        if settings.include_timing_header:
            # Call the function instead of directly adding the middleware class
            add_timing_header_middleware(app)
    except Exception as e:
        logger.warning(
            "Failed to add metrics middleware",
            error=str(e)
        )

# Add auth debugging middleware
#app.add_middleware(AuthDebugMiddleware)

app.include_router(jobs_router)


@app.get("/")
async def root() -> Dict[str, str]:
    """
    Health check endpoint.

    Returns:
        Dict containing the service status message
    """
    return {"message": "Matching Service is running!"}


from app.routers.healthcheck_router import router as healthcheck_router

app.include_router(healthcheck_router)

from app.routers.cronrouters import router as cronrouter

app.include_router(cronrouter)

from app.routers.rejections_router import router as rejections_router

app.include_router(rejections_router)
