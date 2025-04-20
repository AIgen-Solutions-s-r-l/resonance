"""
Run Alembic migrations to update the database schema.

This script runs Alembic migrations to update the database schema,
including adding PostGIS support and updating the schema.
"""

import asyncio
import os
import sys
from loguru import logger
import subprocess
from pathlib import Path


def run_alembic_migration():
    """Run Alembic migration."""
    logger.info("Running Alembic migration...")
    
    try:
        # Get the path to the alembic.ini file
        alembic_dir = Path(__file__).parent.parent / "alembic" / "alembic"
        alembic_ini = alembic_dir / "alembic.ini"
        
        if not alembic_ini.exists():
            logger.error(f"Alembic configuration file not found: {alembic_ini}")
            return False
        
        # Change to the directory containing alembic.ini
        os.chdir(alembic_dir)
        
        # Run the migration
        logger.info(f"Running migration from directory: {os.getcwd()}")
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            logger.info("Migration successful")
            logger.info(f"Output: {result.stdout}")
            return True
        else:
            logger.error(f"Migration failed with return code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            logger.error(f"Output: {result.stdout}")
            return False
            
    except Exception as e:
        logger.error(f"Error running Alembic migration: {e}")
        return False


async def main():
    """Main function."""
    success = run_alembic_migration()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())