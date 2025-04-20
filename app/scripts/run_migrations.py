"""
Run database migrations using Alembic.

This script runs database migrations using Alembic, with additional safety checks:
1. Verifies database connection
2. Checks current migration state
3. Performs a dry run to validate migrations
4. Backs up the database schema (if requested)
5. Applies migrations with proper error handling
6. Verifies the database state after migration
"""

import asyncio
import sys
import subprocess
import os
from datetime import datetime
from loguru import logger
import argparse
from pathlib import Path

from app.utils.db_utils import get_db_cursor
from app.core.config import settings


async def check_database_connection():
    """Check if the database connection is working."""
    logger.info("Checking database connection...")
    
    try:
        async with get_db_cursor() as cursor:
            await cursor.execute("SELECT 1")
            result = await cursor.fetchone()
            if result and result.get('?column?') == 1:
                logger.info("✅ Database connection successful")
                return True
            else:
                logger.error("❌ Database connection failed")
                return False
    except Exception as e:
        logger.error(f"❌ Error connecting to database: {e}")
        return False


async def check_postgis_extension():
    """Check if PostGIS extension is installed."""
    logger.info("Checking PostGIS extension...")
    
    try:
        async with get_db_cursor() as cursor:
            await cursor.execute("SELECT extname, extversion FROM pg_extension WHERE extname = 'postgis'")
            result = await cursor.fetchone()
            if result:
                logger.info(f"✅ PostGIS extension is installed (version {result['extversion']})")
                return True
            else:
                logger.warning("⚠️ PostGIS extension is not installed")
                return False
    except Exception as e:
        logger.error(f"❌ Error checking PostGIS extension: {e}")
        return False


async def get_current_revision():
    """Get the current Alembic revision from the database."""
    logger.info("Getting current Alembic revision...")
    
    try:
        async with get_db_cursor() as cursor:
            # Check if alembic_version table exists
            await cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'alembic_version'
            )
            """)
            table_exists = (await cursor.fetchone())['exists']
            
            if not table_exists:
                logger.warning("⚠️ alembic_version table does not exist - database may not be initialized")
                return None
            
            await cursor.execute("SELECT version_num FROM alembic_version")
            result = await cursor.fetchone()
            if result:
                revision = result.get('version_num')
                logger.info(f"✅ Current Alembic revision: {revision}")
                return revision
            else:
                logger.warning("⚠️ No Alembic revision found in database")
                return None
    except Exception as e:
        logger.error(f"❌ Error getting Alembic revision: {e}")
        return None


def run_alembic_command(command, capture_output=True):
    """Run an Alembic command.
    
    Args:
        command: The Alembic command to run
        capture_output: Whether to capture and return command output
        
    Returns:
        Tuple of (success, stdout, stderr)
    """
    logger.info(f"Running Alembic command: {command}")
    
    try:
        # Get the path to the alembic.ini file
        alembic_dir = Path(__file__).parent.parent / "alembic" / "alembic"
        alembic_ini = alembic_dir / "alembic.ini"
        
        if not alembic_ini.exists():
            logger.error(f"Alembic configuration file not found: {alembic_ini}")
            return False, None, None
        
        # Change to the directory containing alembic.ini
        original_dir = os.getcwd()
        os.chdir(alembic_dir)
        
        try:
            # Run the command
            if capture_output:
                result = subprocess.run(
                    ["alembic"] + command.split(),
                    check=True,
                    capture_output=True,
                    text=True
                )
                return True, result.stdout, result.stderr
            else:
                # Run with output directly to console
                result = subprocess.run(
                    ["alembic"] + command.split(),
                    check=True
                )
                return True, None, None
        finally:
            # Change back to the original directory
            os.chdir(original_dir)
            
    except subprocess.CalledProcessError as e:
        if capture_output:
            logger.error(f"❌ Alembic command failed: {e}")
            logger.error(f"Error output:\n{e.stderr}")
            return False, e.stdout, e.stderr
        else:
            logger.error(f"❌ Alembic command failed with exit code {e.returncode}")
            return False, None, None


async def backup_database_schema(backup_dir="./backups"):
    """Backup the database schema.
    
    Args:
        backup_dir: Directory to store the backup
        
    Returns:
        Path to the backup file or None if backup failed
    """
    logger.info("Backing up database schema...")
    
    # Create backup directory if it doesn't exist
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"schema_backup_{timestamp}.sql")
    
    try:
        # Construct pg_dump command
        pg_dump_cmd = (
            f"PGPASSWORD='{settings.POSTGRES_PASSWORD}' "
            f"pg_dump -h {settings.POSTGRES_HOST} "
            f"-p {settings.POSTGRES_PORT} "
            f"-U {settings.POSTGRES_USER} "
            f"-d {settings.POSTGRES_DB} "
            f"--schema-only "
            f"-f {backup_file}"
        )
        
        # Run pg_dump
        result = subprocess.run(
            pg_dump_cmd,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        
        logger.info(f"✅ Database schema backed up to {backup_file}")
        return backup_file
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Database backup failed: {e}")
        logger.error(f"Error output:\n{e.stderr}")
        return None


async def verify_migration_result():
    """Verify the database state after migration."""
    logger.info("Verifying database state after migration...")
    
    # Check database connection
    if not await check_database_connection():
        logger.error("❌ Database connection failed after migration")
        return False
    
    # Check PostGIS extension
    if not await check_postgis_extension():
        logger.warning("⚠️ PostGIS extension not found after migration")
    
    # Check Alembic revision
    if await get_current_revision() is None:
        logger.error("❌ Could not verify Alembic revision after migration")
        return False
    
    # Additional checks could be added here
    
    logger.info("✅ Database state verification completed")
    return True


async def run_migrations(dry_run=False, backup=False, verbose=False):
    """Run database migrations.
    
    Args:
        dry_run: If True, only show what migrations would be applied without actually applying them
        backup: If True, backup the database schema before applying migrations
        verbose: If True, show detailed output
        
    Returns:
        True if migrations were successful, False otherwise
    """
    logger.info(f"Running database migrations (dry_run={dry_run}, backup={backup})...")
    
    # Check database connection
    if not await check_database_connection():
        logger.error("❌ Database connection failed, aborting migrations")
        return False
    
    # Get current revision
    current_revision = await get_current_revision()
    
    # Check what migrations need to be applied
    success, stdout, stderr = run_alembic_command("upgrade --sql head")
    if not success:
        logger.error("❌ Failed to generate migration SQL")
        return False
    
    # If no migrations needed
    if stdout and "No upgrade operations detected." in stdout:
        logger.info("✅ Database already at latest revision")
        return True
    
    # Show migration plan
    success, stdout, stderr = run_alembic_command("history -i --verbose")
    if success and stdout:
        logger.info(f"Migration history:\n{stdout}")
    
    # If dry run, stop here
    if dry_run:
        logger.info("✅ Dry run completed, no changes applied")
        return True
    
    # Backup database schema if requested
    if backup:
        backup_file = await backup_database_schema()
        if not backup_file:
            logger.error("❌ Database backup failed, aborting migrations")
            return False
    
    # Run migrations
    if verbose:
        # Run with output directly to console for better visibility
        success, _, _ = run_alembic_command("upgrade head", capture_output=False)
    else:
        success, stdout, stderr = run_alembic_command("upgrade head")
    
    if not success:
        logger.error("❌ Migrations failed")
        return False
    
    # Get new revision
    new_revision = await get_current_revision()
    
    if current_revision != new_revision:
        logger.info(f"✅ Database migrated from {current_revision} to {new_revision}")
    else:
        logger.info("✅ Database already at latest revision")
    
    # Verify migration result
    if not await verify_migration_result():
        logger.warning("⚠️ Migration verification had issues")
    
    return True


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Run database migrations")
    parser.add_argument("--dry-run", action="store_true", help="Show what migrations would be applied without applying them")
    parser.add_argument("--backup", action="store_true", help="Backup database schema before applying migrations")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    return parser.parse_args()


async def main():
    """Main function."""
    args = parse_args()
    success = await run_migrations(
        dry_run=args.dry_run,
        backup=args.backup,
        verbose=args.verbose
    )
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())