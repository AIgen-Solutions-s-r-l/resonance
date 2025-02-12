"""
Database migration script for quality tracking tables.

This script creates the necessary database tables for the quality tracking system.
It can be run independently to set up the database schema.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent.parent))

from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database import engine
from app.models.quality_tracking import Base
from app.core.config import settings


async def create_extensions():
    """Create required PostgreSQL extensions."""
    try:
        async with engine.begin() as conn:
            # Create UUID extension if not exists
            await conn.execute(
                text("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")
            )
            logger.info("UUID extension created or already exists")
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to create extensions: {str(e)}")
        raise


async def create_tables():
    """Create all quality tracking tables."""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.success("Quality tracking tables created successfully")
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to create tables: {str(e)}")
        raise


async def create_indexes():
    """Create indexes for better query performance."""
    try:
        async with engine.begin() as conn:
            # Index for match quality evaluations
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_match_quality_resume_id 
                ON match_quality_evaluations (resume_id);
                
                CREATE INDEX IF NOT EXISTS idx_match_quality_job_id 
                ON match_quality_evaluations (job_id);
                
                CREATE INDEX IF NOT EXISTS idx_match_quality_scores 
                ON match_quality_evaluations (
                    quality_score,
                    skill_alignment_score,
                    experience_match_score
                );
            """))
            
            # Index for metrics history
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_metrics_history_name_time 
                ON evaluation_metrics_history (metric_name, recorded_at);
            """))
            
            # Index for manual feedback
            await conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_feedback_evaluation_time 
                ON manual_feedback (evaluation_id, created_at);
            """))
            
            logger.success("Database indexes created successfully")
            
    except SQLAlchemyError as e:
        logger.error(f"Failed to create indexes: {str(e)}")
        raise


async def main():
    """Main migration function."""
    try:
        logger.info("Starting database migration for quality tracking system")
        
        # Create extensions first
        await create_extensions()
        
        # Create tables
        await create_tables()
        
        # Create indexes
        await create_indexes()
        
        logger.success("Database migration completed successfully")
        
    except Exception as e:
        logger.error(f"Migration failed: {str(e)}")
        sys.exit(1)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    logger.info(f"Using database: {settings.db_name} at {settings.db_host}")
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.warning("Migration interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        sys.exit(1)