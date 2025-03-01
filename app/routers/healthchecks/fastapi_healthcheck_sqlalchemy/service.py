import psycopg
from app.log.logging import logger
from app.routers.healthchecks.fastapi_healthcheck.service import HealthCheckBase
from app.routers.healthchecks.fastapi_healthcheck.enum import HealthCheckStatusEnum
from app.routers.healthchecks.fastapi_healthcheck.domain import HealthCheckInterface
from typing import List
class HealthCheckPostgres(HealthCheckBase, HealthCheckInterface):
    _connection_uri: str
    _tags: List[str]

    def __init__(self, connection_uri: str, alias: str, tags: List[str]) -> None:
        self._connection_uri = connection_uri
        self._alias = alias
        self._tags = tags
        self._engine = psycopg.connect(self._connection_uri, autocommit=True)

    async def __checkHealth__(self) -> HealthCheckStatusEnum:
        res = HealthCheckStatusEnum.UNHEALTHY
        try:
            # Use AsyncConnection for asynchronous operations
            async with await psycopg.AsyncConnection.connect(self._connection_uri, autocommit=True) as conn:
                async with conn.cursor() as cursor:
                    await cursor.execute("SELECT 1")
                    result = await cursor.fetchone()
                    if result and result[0] == 1:
                        res = HealthCheckStatusEnum.HEALTHY
        except Exception as e:
            logger.error(f"Database health check failed: {str(e)}", error=str(e))
        return res
