from fastapi import APIRouter
from app.routers.healthchecks.fastapi_healthcheck import HealthCheckFactory, healthCheckRoute
from app.routers.healthchecks.fastapi_healthcheck_sqlalchemy import HealthCheckSQLAlchemy
from app.routers.healthchecks.fastapi_healthcheck_mongodb import HealthCheckMongoDB
from app.routers.healthchecks.fastapi_healthcheck_llmapi import HealthCheckLlmApi
from app.core.config import settings
from fastapi import HTTPException

router = APIRouter(tags=["healthcheck"])

@router.get(
    "/healthcheck",
    description="Health check endpoint",
    responses={
        200: {"description": "Health check passed"},
        500: {"description": "Health check failed"}
    }
)
async def health_check():
    
    _healthChecks = HealthCheckFactory()
    _healthChecks.add(
        HealthCheckSQLAlchemy(
            connection_uri=settings.database_url,
            alias='postgres db',
            tags=('postgres', 'db', 'sql01')
        )
    )
    _healthChecks.add(
        HealthCheckMongoDB(
            connection_uri=settings.mongodb,
            alias='mongo db',
            tags=('mongo', 'db')
        )
    )
    _healthChecks.add(
        HealthCheckLlmApi(
            api_key=settings.openai_api_key,
            llm_base_url=settings.llm_base_url,
            llm_model_name=settings.llm_model_name,
            alias='llm api',
            tags=('llm', 'api')
        )
    )
    
    try:
        return await healthCheckRoute(factory=_healthChecks)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
