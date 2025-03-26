"""
Script to upgrade diskann indices to version 2.

This script upgrades existing diskann indices to version 2 as recommended
in the error message when the vector dimension, max_neighbors, and l_value_ib
parameters haven't changed.
"""

import argparse
import asyncio
import psycopg
from psycopg.sql import SQL, Identifier

from app.core.config import settings
from app.log.logging import logger


async def upgrade_diskann_indices():
    """Upgrade diskann indices to version 2."""
    logger.info("Upgrading diskann indices to version 2")
    
    conn = None
    try:
        # Connect to database
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        
        # Create cursor
        async with conn.cursor() as cursor:
            # Check existing indices
            await cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'Jobs' AND indexdef LIKE '%embedding%'
            """)
            existing_indices = await cursor.fetchall()
            
            if not existing_indices:
                logger.warning("No vector indices found on Jobs table")
                return
            
            logger.info(f"Found {len(existing_indices)} existing vector indices:")
            for idx_name, idx_def in existing_indices:
                logger.info(f"  {idx_name}: {idx_def}")
            
            # Check if the indices are diskann type
            diskann_indices = []
            for idx_name, idx_def in existing_indices:
                if "diskann" in idx_def.lower():
                    diskann_indices.append(idx_name)
            
            if not diskann_indices:
                logger.warning("No diskann indices found. The error might be related to another index type.")
                logger.info("You might need to recreate the indices using the create_vector_indices.py script.")
                return
            
            logger.info(f"Found {len(diskann_indices)} diskann indices to upgrade")
            
            # Upgrade each diskann index
            for idx_name in diskann_indices:
                logger.info(f"Upgrading diskann index: {idx_name}")
                try:
                    # Use the upgrade_diskann_index() function as suggested in the error message
                    await cursor.execute(
                        SQL("SELECT upgrade_diskann_index({})").format(
                            SQL("\"") + SQL(idx_name) + SQL("\"")
                        )
                    )
                    logger.success(f"Successfully upgraded index {idx_name}")
                except Exception as e:
                    logger.error(f"Error upgrading index {idx_name}: {str(e)}")
                    logger.warning("If the error persists, you may need to recreate the index using REINDEX")
                    logger.warning("Example: REINDEX INDEX \"" + idx_name + "\"")
            
            await conn.commit()
            logger.success("Diskann index upgrade process completed")
            
    except Exception as e:
        logger.error(f"Error upgrading diskann indices: {str(e)}")
        if conn:
            await conn.rollback()
        raise
    
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upgrade diskann indices to version 2")
    
    args = parser.parse_args()
    
    asyncio.run(upgrade_diskann_indices())