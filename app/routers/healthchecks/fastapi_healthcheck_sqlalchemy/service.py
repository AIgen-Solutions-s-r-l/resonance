import psycopg
from app.log.logging import logger
from app.routers.healthchecks.fastapi_healthcheck.service import HealthCheckBase
from app.routers.healthchecks.fastapi_healthcheck.enum import HealthCheckStatusEnum
from app.routers.healthchecks.fastapi_healthcheck.domain import HealthCheckInterface
from typing import List
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text


class HealthCheckSQLAlchemy(HealthCheckBase, HealthCheckInterface):
    _connection_uri: str
    _tags: List[str]

    def __init__(self, connection_uri: str, alias: str, tags: List[str]) -> None:
        self._connection_uri = connection_uri
        self._alias = alias
        self._tags = tags
        #self._engine = create_async_engine(self._connection_uri, future=True)
        self._engine = psycopg.connect(self._connection_uri, autocommit=True)

    def __checkHealth__(self) -> HealthCheckStatusEnum:
        res = HealthCheckStatusEnum.UNHEALTHY
        with self._engine.cursor() as cursor:
            try:
                cursor.execute("SELECT 1")
                res = HealthCheckStatusEnum.HEALTHY
            except Exception as e:
                logger.error(f"Database health check failed: {str(e)}", error=str(e))
        return res
