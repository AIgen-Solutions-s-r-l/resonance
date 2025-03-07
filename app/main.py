from typing import Dict
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from jose import jwt

from app.log.logging import logger
from app.routers.jobs_matched_router import router as jobs_router
from app.core.config import settings
from app.metrics import setup_metrics
from app.metrics.system import collect_system_metrics


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
                    logger.error(
                        "Malformed Authorization header for {path}: {auth_header}",
                        path=path,
                        auth_header=auth_header
                    )
            else:
                logger.error("No Authorization header present for {path}", path=path)
        
        # Process the request and get response
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response status for auth issues
        if response.status_code == 401:
            logger.error(
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

    Args:
        app: FastAPI application instance
    """

    try:
        logger.info("Starting application")
        
        # Report initial system metrics
        collect_system_metrics()
        
        logger.info("Application started successfully")
        
        yield
        
        # Application shutdown
        logger.info("Shutting down application")
        
        # Stop metrics collection
        from app.metrics import stop_metrics_collection
        stop_metrics_collection()
        
        logger.info("Application shut down successfully")
        
    except Exception as e:
        logger.exception("Application lifecycle error: {error}", error=str(e))
        raise


app = FastAPI(
    lifespan=lifespan,
    title="Job Matching API",
    description="API for matching jobs with user resumes.",
    version="1.0.0",
)

# Setup metrics (must be done before other middleware)
try:
    setup_metrics(app)
except Exception as e:
    logger.error(
        "Failed to set up metrics system",
        error=str(e)
    )

# Add auth debugging middleware
app.add_middleware(AuthDebugMiddleware)

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
