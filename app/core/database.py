# app/core/database.py
import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.core.config import settings
from app.log.logging import logger

logger.info("Using database URL: {database_url}", database_url=settings.database_url)

# Create the asynchronous engine for connecting to the PostgreSQL database
engine = create_async_engine(settings.database_url, echo=True)

# Define an asynchronous session factory bound to the engine
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,  # Prevents objects from expiring after each commit
)


async def get_db():
    """
    Dependency to obtain a new database session for each request.

    `get_db` is an asynchronous function that provides a new database session
    using the `AsyncSessionLocal` factory, which is automatically closed after use.

    Yields:
        AsyncSession: An asynchronous database session for interacting with the database.
    """
    async with AsyncSessionLocal() as session:
        yield session
