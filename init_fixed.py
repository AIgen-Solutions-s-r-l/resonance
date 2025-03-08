#!/usr/bin/env python
# Fixed version of app/scripts/init_db.py

import asyncio
import sys
from pathlib import Path

# Add the project root directory to Python path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.config import settings  # Import from config instead

# Import the Base and models from job.py
from app.core.base import Base
from app.models.job import Company, Location, Job, Country
from app.log.logging import logger
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import asyncpg


async def create_database_if_not_exists() -> None:
    """
    Create the database if it doesn't exist.
    """
    # Parse the database URL to get database name and connection details
    db_url = settings.database_url.replace(
        "+asyncpg", ""
    )  # Remove the asyncpg prefix if present
    db_name = db_url.split("/")[-1]  # Get database name
    postgres_url = (
        db_url.rsplit("/", 1)[0] + "/postgres"
    )  # Create URL for postgres database

    try:
        # Connect to the default postgres database
        conn = await asyncpg.connect(postgres_url)

        # Check if our database exists
        result = await conn.fetch(
            "SELECT 1 FROM pg_database WHERE datname = $1", db_name
        )

        if not result:
            logger.info(f"Creating database {db_name}", db_name=db_name)
            # Create database if it doesn't exist
            await conn.execute(f'CREATE DATABASE "{db_name}"')
            logger.info(f"Database {db_name} created successfully", db_name=db_name)
        else:
            logger.info(f"Database {db_name} already exists", db_name=db_name)

        await conn.close()

    except Exception as e:
        logger.exception(f"Error while creating database: {str(e)}", error=str(e))
        raise


async def init_database() -> None:
    """
    Initialize the database and create all tables asynchronously.
    """
    engine = None
    try:
        logger.info("Starting database initialization...")

        # First ensure database exists
        await create_database_if_not_exists()

        # Explicitly use asyncpg dialect
        db_url = settings.database_url
        if not db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

        logger.info(f"Using database URL: {db_url}")

        # Create async engine with the proper URL
        engine = create_async_engine(db_url, echo=False)

        # Create all tables
        async with engine.begin() as conn:
            logger.info("Dropping all existing tables...")
            await conn.run_sync(Base.metadata.drop_all)
            logger.info("Creating all tables...")
            await conn.run_sync(Base.metadata.create_all)

        logger.info("Database initialized successfully.")

    except Exception as e:
        logger.exception(
            f"An error occurred while initializing the database: {str(e)}", error=str(e)
        )
        raise
    finally:
        if engine:
            await engine.dispose()


async def verify_database() -> None:
    """
    Verify database connection and basic functionality.
    """
    # Explicitly use asyncpg dialect
    db_url = settings.database_url
    if not db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")
        
    engine = create_async_engine(db_url, echo=False)
    
    try:
        logger.info("Verifying database connection...")
        async with engine.connect() as conn:
            # Check connection
            result = await conn.execute(
                text("SELECT current_database(), current_timestamp")
            )
            db_info = result.first()  # No await here - this is not an awaitable
            logger.info(
                f"Successfully connected to database: {db_info[0]}", db_name=db_info[0]
            )
            logger.info(f"Current server time: {db_info[1]}", server_time=db_info[1])

            # Check if tables exist
            result = await conn.execute(
                text(
                    """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name;
                """
                )
            )
            tables = result.fetchall()  # No await here
            if tables:
                logger.info("Verified tables in database:")
                for table in tables:
                    # Get column information for each table
                    columns_result = await conn.execute(
                        text(
                            f"""
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_name = '{table[0]}'
                            ORDER BY ordinal_position;
                        """
                        )
                    )
                    columns = columns_result.fetchall()  # No await here

                    logger.info(f"\n  Table: {table[0]}", table=table[0])
                    for column in columns:
                        nullable = "NULL" if column[2] == "YES" else "NOT NULL"
                        logger.info(
                            f"    - {column[0]}: {column[1]} {nullable}",
                            column=column[0],
                            data_type=column[1],
                            nullable=nullable,
                        )
            else:
                logger.warning("No tables found in the database")

        logger.info("Database verification completed successfully.")
    except Exception as e:
        logger.exception(f"Database verification failed: {str(e)}", exception=str(e))
        raise
    finally:
        await engine.dispose()


async def main():
    logger.info("=== Starting Database Setup ===")
    await init_database()
    await verify_database()
    logger.info("=== Database Setup Completed ===")


if __name__ == "__main__":
    asyncio.run(main())