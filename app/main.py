from typing import Dict
from fastapi import FastAPI

from app.log.logging import logger
from app.routers.jobs_matched_router import router as jobs_router


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
