from app.log.logging import logger
from app.routers.healthchecks.fastapi_healthcheck.service import HealthCheckBase
from app.routers.healthchecks.fastapi_healthcheck.enum import HealthCheckStatusEnum
from app.routers.healthchecks.fastapi_healthcheck.domain import HealthCheckInterface
from typing import List, Optional
import requests


class HealthCheckLlmApi(HealthCheckBase, HealthCheckInterface):
    _api_key: str
    _llm_base_url: str
    _llm_model_name: str

    def __init__(
        self,

        api_key: str,
        llm_base_url: str,
        llm_model_name: str,
        alias: str,
        tags: Optional[List[str]] = None,
    ) -> None:
        self._api_key = api_key
        self._llm_base_url = llm_base_url
        self._llm_model_name = llm_model_name
        self._alias = alias
        self._tags = tags

    async def __checkHealth__(self) -> HealthCheckStatusEnum:
        res: HealthCheckStatusEnum = HealthCheckStatusEnum.UNHEALTHY
        try:
            headers = {
                'Authorization': f'Bearer {self._api_key}',
                'Content-Type': 'application/json'
            }
            data = {
                'model': self._llm_model_name,
                'messages': [
                    {
                        'role': 'user',
                        'content': 'answer randomly with only one letter'
                    }
                ],
                'temperature': 1
            }
            response = requests.post(f'{self._llm_base_url}/chat/completions', headers=headers, json=data)
            if response.status_code == 200:
                res = HealthCheckStatusEnum.HEALTHY
            else:
                logger.error(f"LLM on {self._llm_base_url} health check failed: {response.status_code}")
        except Exception as e:
            logger.error(f"LLM on {self._llm_base_url} health check failed: {e}")
        return res