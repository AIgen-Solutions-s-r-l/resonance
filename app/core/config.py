# app/core/config.py

import os
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Configuration class for environment variables and service settings.

    This class defines the settings for the application, including connections
    to external services like RabbitMQ and PostgreSQL. The settings are primarily
    loaded from environment variables, with default values provided for local development
    or testing environments.

    Attributes:
        rabbitmq_url (str): The connection URL for RabbitMQ.
            Default: "amqp://guest:guest@localhost:5672/"
            Example: "amqp://user:password@hostname:port/vhost"

        service_name (str): The name of the service.
            Default: "authService"
            Used for logging, monitoring, and other service identification purposes.

        database_url (str): The connection URL for the main PostgreSQL database.
            Default: "postgresql+asyncpg://user:password@localhost:5432/main_db"
            Example: "postgresql+asyncpg://username:password@hostname:port/dbname"

        test_database_url (str): The connection URL for the test PostgreSQL database.
            Default: "postgresql+asyncpg://user:password@localhost:5432/test_db"
            Used for testing purposes to isolate data changes and run tests against a dedicated
            test database. Automatically used when tests are run.

    Usage:
        The settings can be overridden by creating a `.env` file in the root directory
        with the necessary environment variables. Alternatively, environment variables
        can be set directly in the operating system.

        Example:
            .env file content:
            RABBITMQ_URL="amqp://guest:guest@localhost:5672/"
            DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/main_db"
            TEST_DATABASE_URL="postgresql+asyncpg://user:password@localhost:5432/test_db"
    """

    service_name: str = "matching_service"
        # MongoDB settings
    mongodb_host: str = "localhost"
    mongodb_port: int = 27017
    mongodb_username: str = "appUser"
    mongodb_password: str = "password123"
    mongodb_database: str = "resumes"
    mongodb_auth_source: str = "main_db"

    # Authentication settings
    secret_key: str = "your-secret-key-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    # Construct MongoDB URI with auth source
    @property
    def mongodb_uri(self) -> str:
        return f"mongodb://{self.mongodb_username}:{self.mongodb_password}@{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_database}?authSource={self.mongodb_auth_source}"

    database_url: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://testuser:testpassword@localhost:5432/matching")
    test_database_url: str = os.getenv("TEST_DATABASE_URL",
                                       "postgresql+asyncpg://testuser:testpassword@localhost:5432/test_matching")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "sk-tSeHC_UQYlf-5gaww6ZZKYrl8Mg2F_lqZ9TamxtfdMT3BlbkFJCrcgPy_EN-4pwJk8DKMhYV6PYrKoTkHjgRJ87IobkA")
    db_name: str = os.getenv("DBNAME", "matching")
    db_user: str = os.getenv("DBUSER", "testuser")
    db_password: str = os.getenv("DBPASSWORD", "testpassword")
    db_host: str = os.getenv("DBHOST", "localhost")
    db_port: str = os.getenv("DBPORT", "5432")
    # Logging settings
    log_level: str = "DEBUG"
    logstash_host: Optional[str] = 'localhost'
    logstash_port: Optional[int] = 5141
    enable_logstash: bool = True
    environment: str = "development"

    model_config = SettingsConfigDict(env_file=".env")


    __all__ = ["Settings"]