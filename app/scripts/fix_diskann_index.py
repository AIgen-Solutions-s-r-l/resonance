"""
Script to fix diskann indices issues.

This script provides options to:
1. Upgrade existing diskann indices to version 2 using upgrade_diskann_index()
2. Recreate the indices using REINDEX if the upgrade fails
3. Drop and recreate the indices from scratch if needed
"""

import argparse
import asyncio
import psycopg
from psycopg.sql import SQL, Identifier

from app.core.config import settings
from app.log.logging import logger


async def fix_diskann_indices(mode="upgrade", force=False):
    """
    Fix diskann indices issues.
    
    Args:
        mode: The fix mode - "upgrade", "reindex", or "recreate"
        force: Whether to force the operation without confirmation
    """
    logger.info(f"Fixing diskann indices using mode: {mode}")
    
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
                    diskann_indices.append((idx_name, idx_def))
            
            if not diskann_indices:
                logger.warning("No diskann indices found. The error might be related to another index type.")
                
                # Check for other vector index types
                for idx_name, idx_def in existing_indices:
                    if any(x in idx_def.lower() for x in ["vector", "embedding", "similarity"]):
                        logger.info(f"Found vector-related index: {idx_name}")
                        
                        if mode == "reindex" or mode == "recreate":
                            if not force:
                                confirmation = input(f"Do you want to {mode} the index {idx_name}? (y/n): ")
                                if confirmation.lower() != 'y':
                                    logger.info(f"Skipping {idx_name}")
                                    continue
                            
                            if mode == "reindex":
                                logger.info(f"Reindexing {idx_name}")
                                await cursor.execute(SQL("REINDEX INDEX {}").format(
                                    SQL("\"") + SQL(idx_name) + SQL("\"")
                                ))
                            elif mode == "recreate":
                                logger.info(f"Recreating {idx_name} is not supported automatically.")
                                logger.info("Please use the create_vector_indices.py script to recreate all indices.")
                return
            
            logger.info(f"Found {len(diskann_indices)} diskann indices to fix")
            
            # Process each diskann index based on the selected mode
            for idx_name, idx_def in diskann_indices:
                if mode == "upgrade":
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
                        logger.warning("If the error persists, try using --mode=reindex or --mode=recreate")
                
                elif mode == "reindex":
                    logger.info(f"Reindexing {idx_name}")
                    try:
                        await cursor.execute(SQL("REINDEX INDEX {}").format(
                            SQL("\"") + SQL(idx_name) + SQL("\"")
                        ))
                        logger.success(f"Successfully reindexed {idx_name}")
                    except Exception as e:
                        logger.error(f"Error reindexing {idx_name}: {str(e)}")
                        logger.warning("If the error persists, try using --mode=recreate")
                
                elif mode == "recreate":
                    if not force:
                        confirmation = input(f"Do you want to drop and recreate the index {idx_name}? (y/n): ")
                        if confirmation.lower() != 'y':
                            logger.info(f"Skipping {idx_name}")
                            continue
                    
                    logger.info(f"Dropping index {idx_name}")
                    try:
                        await cursor.execute(SQL("DROP INDEX IF EXISTS {}").format(
                            SQL("\"") + SQL(idx_name) + SQL("\"")
                        ))
                        logger.info(f"Successfully dropped {idx_name}")
                        logger.info("Please use the create_vector_indices.py script to recreate the index")
                    except Exception as e:
                        logger.error(f"Error dropping index {idx_name}: {str(e)}")
            
            await conn.commit()
            logger.success(f"Diskann index {mode} process completed")
            
    except Exception as e:
        logger.error(f"Error fixing diskann indices: {str(e)}")
        if conn:
            await conn.rollback()
        raise
    
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fix diskann indices issues")
    parser.add_argument(
        "--mode", 
        choices=["upgrade", "reindex", "recreate"],
        default="upgrade",
        help="Fix mode: upgrade (use upgrade_diskann_index), reindex (use REINDEX), or recreate (drop and recreate)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force operations without confirmation"
    )
    
    args = parser.parse_args()
    
    asyncio.run(fix_diskann_indices(mode=args.mode, force=args.force))