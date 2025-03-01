from fastapi import APIRouter
from app.routers.healthchecks.fastapi_healthcheck import (
    HealthCheckFactory,
    healthCheckRoute,
)
from app.routers.healthchecks.fastapi_healthcheck_mongodb import HealthCheckMongoDB
from app.core.config import settings
from app.log.logging import logger
from fastapi import HTTPException

from app.routers.healthchecks.fastapi_healthcheck_postgres.service import HealthCheckPostgres

router = APIRouter(tags=["healthcheck"])


@router.get(
    "/healthcheck",
    description="Health check endpoint",
    responses={
        200: {"description": "Health check passed"},
        500: {"description": "Health check failed"},
    },
)
async def health_check(withlog: bool = False):
    if withlog:
        logger.debug("healthcheck debug log")
        logger.info("healthcheck info log")
        logger.warning("healthcheck warning log")
        logger.error("healthcheck error log")
        logger.critical("healthcheck critical log")

    _healthChecks = HealthCheckFactory()
    _healthChecks.add(
        HealthCheckPostgres(
            connection_uri=settings.database_url,
            alias="postgres db",
            tags=("postgres", "db", "sql01"),
        )
    )
    _healthChecks.add(
        HealthCheckMongoDB(
            connection_uri=settings.mongodb, alias="mongo db", tags=("mongo", "db")
        )
    )

    try:
        return await healthCheckRoute(factory=_healthChecks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
