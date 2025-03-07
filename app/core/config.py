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
    log_level: str = os.getenv("LOG_LEVEL", "DEBUG")
    
    # Override log level for development
    if environment == "development":
        log_level = "DEBUG"
    syslog_host: str = os.getenv("SYSLOG_HOST", "172.17.0.1")
    syslog_port: int = int(os.getenv("SYSLOG_PORT", "5141"))
    json_logs: bool = os.getenv("JSON_LOGS", "True").lower() == "true"
    log_retention: str = os.getenv("LOG_RETENTION", "7 days")
    enable_logstash: bool = os.getenv("ENABLE_LOGSTASH", "True").lower() == "true"

    # MongoDB settings
    mongodb: str = os.getenv("MONGODB", "mongodb://localhost:27017")
    mongodb_database: str = os.getenv("MONGODB_DATABASE", "resumes")

    # RabbitMQ settings
    rabbitmq_url: str = os.getenv("RABBITMQ_URL", "amqp://guest:guest@localhost:5672/")
    job_to_apply_queue: str = os.getenv("MATCHING_QUEUE", "job_to_apply_queue")

    # PostgreSQL settings
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://testuser:testpassword@localhost:5432/matching",
    )
    
    # Authentication settings
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(
        os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    )

    # OpenAI API key
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "your-openai-api-key")
    llm_base_url: str = os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1")
    llm_model_name: str = os.getenv("LLM_MODEL_NAME", "openai/gpt-4o-mini")
    
    # Metrics settings
    metrics_enabled: bool = os.getenv("METRICS_ENABLED", "True").lower() == "true"
    datadog_api_key: Optional[str] = os.getenv("DD_API_KEY")
    datadog_app_key: Optional[str] = os.getenv("DD_APP_KEY")
    metrics_sample_rate: float = float(os.getenv("METRICS_SAMPLE_RATE", "1.0"))
    metrics_host: str = os.getenv("METRICS_HOST", "127.0.0.1")
    metrics_port: int = int(os.getenv("METRICS_PORT", "8125"))

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()

__all__ = ["Settings"]
