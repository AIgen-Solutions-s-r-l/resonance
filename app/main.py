from typing import Dict
from fastapi import FastAPI
from loguru import logger
from app.core.config import settings
from app.core.logging_config import (
    setup_logging,
    get_logger_context,
    LoggingConfig,
)
from app.routers.jobs_matched_router import router as jobs_router

logging_config = LoggingConfig(
    service_name=settings.service_name,
    log_level=settings.log_level,
    logstash_host=settings.logstash_host,
    logstash_port=settings.logstash_port,
    enable_file_logging=True,
    enable_console_logging=True,
    enable_logstash=settings.enable_logstash,
    environment=settings.environment,
)


setup_logging(logging_config)


if settings.enable_logstash:

    from app.core.logging_config import test_logstash_connection

    if test_logstash_connection(settings.logstash_host, settings.logstash_port):
        logger.info("Logstash connection successful")
    else:
        logger.warning(
            "Logstash connection failed, continuing with local logging only")


async def lifespan(app: FastAPI):
    """
    Manages application startup and shutdown.

    Args:
        app: FastAPI application instance
    """
    context = get_logger_context(action="lifespan")

    try:
        logger.info("Starting application", context)
        yield
        logger.info("Shutting down application", context)
    except Exception as e:
        context["error"] = str(e)
        logger.error("Application lifecycle error", context)
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
    context = get_logger_context(action="health_check")
    logger.info("Health check requested", context)
    return {"message": "Matching Service is running!"}

from app.routers.healthcheck_router import router as healthcheck_router
app.include_router(healthcheck_router)