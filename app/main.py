from typing import Dict
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
import json
from jose import jwt

from app.log.logging import logger
from app.routers.jobs_matched_router import router as jobs_router
from app.core.config import settings


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
                        logger.debug(
                            f"Auth header present for {path}. Token preview: {token_preview}",
                            decoded_payload=str(decoded),
                            path=path
                        )
                    except Exception as e:
                        logger.warning(
                            f"Could not decode token for debugging: {str(e)}",
                            token_preview=token_preview,
                            path=path,
                            error=str(e)
                        )
                else:
                    logger.warning(
                        f"Malformed Authorization header for {path}: {auth_header}",
                        path=path
                    )
            else:
                logger.warning(f"No Authorization header present for {path}", path=path)
        
        # Process the request and get response
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log response status for auth issues
        if response.status_code == 401:
            logger.warning(
                f"401 Unauthorized response for {path}. Process time: {process_time:.4f}s",
                path=path,
                status_code=response.status_code,
                process_time=f"{process_time:.4f}"
            )
            if path.startswith("/jobs/"):
                # Log the configured secret key (partial)
                secret_preview = settings.secret_key[:3] + "..." if settings.secret_key else "Not set"
                logger.debug(
                    f"Auth configuration: algorithm={settings.algorithm}, "
                    f"secret_key_preview={secret_preview}"
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
        yield
        logger.info("Shutting down application")
    except Exception as e:
        logger.error(f"Application lifecycle error: {str(e)}", error=str(e))
        raise


app = FastAPI(
    lifespan=lifespan,
    title="Job Matching API",
    description="API for matching jobs with user resumes.",
    version="1.0.0",
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
