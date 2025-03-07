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
    
    # Application name for metrics
    app_name: str = os.getenv("APP_NAME", "matching_service")

    # Metrics settings
    metrics_enabled: bool = os.getenv("METRICS_ENABLED", "True").lower() == "true"
    metrics_debug: bool = os.getenv("METRICS_DEBUG", "False").lower() == "true"
    metrics_prefix: str = os.getenv("METRICS_PREFIX", "matching_service")
    metrics_app_name: str = os.getenv("METRICS_APP_NAME", "")
    metrics_environment: str = os.getenv("METRICS_ENVIRONMENT", os.getenv("ENVIRONMENT", "development"))
    metrics_sample_rate: float = float(os.getenv("METRICS_SAMPLE_RATE", "1.0"))
    metrics_collection_enabled: bool = os.getenv("METRICS_COLLECTION_ENABLED", "True").lower() == "true"
    include_timing_header: bool = os.getenv("INCLUDE_TIMING_HEADER", "False").lower() == "true"
    metrics_backend: str = os.getenv("METRICS_BACKEND", "statsd")  # For test compatibility (logging, statsd, prometheus)
    
    # StatsD backend settings
    metrics_statsd_enabled: bool = os.getenv("METRICS_STATSD_ENABLED", "True").lower() == "true"
    metrics_statsd_host: str = os.getenv("METRICS_STATSD_HOST", "127.0.0.1")
    metrics_statsd_port: int = int(os.getenv("METRICS_STATSD_PORT", "8125"))
    
    # Prometheus backend settings
    metrics_prometheus_enabled: bool = os.getenv("METRICS_PROMETHEUS_ENABLED", "False").lower() == "true"
    metrics_prometheus_port: int = int(os.getenv("METRICS_PROMETHEUS_PORT", "9091"))
    
    # System metrics settings
    system_metrics_enabled: bool = os.getenv("SYSTEM_METRICS_ENABLED", "True").lower() == "true"
    system_metrics_interval: int = int(os.getenv("SYSTEM_METRICS_INTERVAL", "60"))
    
    # Performance thresholds
    slow_request_threshold_ms: float = float(os.getenv("SLOW_REQUEST_THRESHOLD_MS", "1000.0"))
    slow_query_threshold_ms: float = float(os.getenv("SLOW_QUERY_THRESHOLD_MS", "500.0"))
    slow_operation_threshold_ms: float = float(os.getenv("SLOW_OPERATION_THRESHOLD_MS", "2000.0"))
    
    # Metrics retention
    metrics_retention_days: int = int(os.getenv("METRICS_RETENTION_DAYS", "7"))

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()

__all__ = ["Settings"]
