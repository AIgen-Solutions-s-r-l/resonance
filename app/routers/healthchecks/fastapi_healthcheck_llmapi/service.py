from app.log.logging import logger
from app.routers.healthchecks.fastapi_healthcheck.service import HealthCheckBase
from app.routers.healthchecks.fastapi_healthcheck.enum import HealthCheckStatusEnum
from app.routers.healthchecks.fastapi_healthcheck.domain import HealthCheckInterface
from typing import List, Optional
from openai import OpenAI


class HealthCheckLlmApi(HealthCheckBase, HealthCheckInterface):
    _api_key: str

    def __init__(
        self,
        api_key: str,
        alias: str,
        tags: Optional[List[str]] = None,
    ) -> None:
        self._api_key = api_key
        self._alias = alias
        self._tags = tags
        self.client = OpenAI(api_key=self._api_key)

    async def __checkHealth__(self) -> HealthCheckStatusEnum:
        res: HealthCheckStatusEnum = HealthCheckStatusEnum.UNHEALTHY
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        'role': 'user',
                        'content': 'answer randomly with only one letter'
                    }
                ],
                temperature=1
            )
            if response.choices and response.choices[0].message:
                res = HealthCheckStatusEnum.HEALTHY
            else:
                logger.error("OpenAI health check failed: No response")
        except Exception as e:
            logger.error(f"OpenAI health check failed: {e}")
        return res