import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Configuration class for environment variables and service settings.
    """

    # Service settings
    service_name: str = os.getenv("SERVICE_NAME", "matching_service")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = os.getenv("DEBUG", "True").lower() == "true"

    # Logging settings
    # log_level: str = os.getenv("LOG_LEVEL", "DEBUG")
    # logstash_host: str = os.getenv("SYSLOG_HOST", "localhost")
    # logstash_port: int = int(os.getenv("SYSLOG_PORT", "5141"))
    # json_logs: bool = os.getenv("JSON_LOGS", "True").lower() == "true"
    # log_retention: str = os.getenv("LOG_RETENTION", "7 days")
    # enable_logstash: bool = os.getenv("ENABLE_LOGSTASH", "True").lower() == "true"

    # MongoDB settings
    mongodb: str = os.getenv("MONGODB", "mongodb://localhost:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "resumes")

    # PostgreSQL settings
    db_name: str = os.getenv("DBNAME", "matching")
    db_user: str = os.getenv("DBUSER", "testuser")
    db_password: str = os.getenv("DBPASSWORD", "testpassword")
    db_host: str = os.getenv("DBHOST", "localhost")
    db_port: str = os.getenv("DBPORT", "5432")

    # RabbitMQ settings
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    job_to_apply_queue: str = os.getenv("MATCHING_QUEUE", "job_to_apply_queue")

    # PostgreSQL settings
    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://testuser:testpassword@localhost:5432/matching")
    test_database_url: str = os.getenv("TEST_DATABASE_URL", "postgresql+asyncpg://testuser:testpassword@localhost:5432/test_matching")

    # Authentication settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    # OpenAI API key
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "openai/gpt-4o-mini")
    
    # Text Embedder
    text_embedder_model: str = "BAAI/bge-m3"
    text_embedder_base_url: str = "https://api.deepinfra.com/v1/openai"
    text_embedder_api_key: str = os.getenv("DEEPINFRA_TOKEN", "your-deepinfra-token")

    model_config = SettingsConfigDict(env_file=".env")

settings = Settings()

__all__ = ["Settings"]
