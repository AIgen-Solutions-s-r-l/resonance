"""
Script to create optimized vector indices for PostgreSQL.

This script creates the necessary vector indices on the embedding column
to significantly improve query performance for vector similarity operations.
"""

import argparse
import asyncio
import psycopg
from psycopg.sql import SQL

from app.core.config import settings
from app.log.logging import logger


async def create_vector_indices():
    """Create vector indices for the Jobs table."""
    logger.info("Creating vector indices on Jobs table")
    
    conn = None
    try:
        # Connect to database
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        
        # Create cursor
        async with conn.cursor() as cursor:
            # Check if pgvector extension is installed
            await cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
            result = await cursor.fetchone()
            
            if not result:
                logger.warning("pgvector extension not found, attempting to create it")
                await cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
                await conn.commit()
            
            # Check which index types are supported
            supported_index_types = []
            try:
                # Check for IVFFLAT support
                await cursor.execute("SELECT proname FROM pg_proc WHERE proname = 'ivfflat_handler'")
                if await cursor.fetchone():
                    supported_index_types.append('ivfflat')
                
                # Check for HNSW support
                await cursor.execute("SELECT proname FROM pg_proc WHERE proname = 'hnsw_handler'")
                if await cursor.fetchone():
                    supported_index_types.append('hnsw')
            except Exception as e:
                logger.warning(f"Error checking for supported index types: {str(e)}")
            
            logger.info(f"Supported vector index types: {supported_index_types}")
            
            # Check existing indices
            await cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'Jobs' AND indexdef LIKE '%embedding%'
            """)
            existing_indices = await cursor.fetchall()
            
            if existing_indices:
                logger.info(f"Found {len(existing_indices)} existing vector indices:")
                for idx_name, idx_def in existing_indices:
                    logger.info(f"  {idx_name}: {idx_def}")
                    
                # Ask for confirmation to drop existing indices
                if not settings.debug:  # In production, ask for confirmation
                    confirmation = input("Do you want to drop existing indices and recreate? (y/n): ")
                    if confirmation.lower() != 'y':
                        logger.info("Operation cancelled by user")
                        return
                
                # Drop existing indices
                for idx_name, _ in existing_indices:
                    logger.info(f"Dropping index {idx_name}")
                    await cursor.execute(f"DROP INDEX IF EXISTS \"{idx_name}\"")
                
                await conn.commit()
            
            # Create the appropriate index based on configuration
            index_type = settings.vector_index_type.lower()
            
            if index_type == 'ivfflat' and 'ivfflat' in supported_index_types:
                logger.info(f"Creating IVFFLAT index with {settings.vector_ivf_lists} lists")
                
                await cursor.execute(f"""
                    CREATE INDEX ON "Jobs" 
                    USING ivfflat (embedding vector_l2_ops)
                    WITH (lists = {settings.vector_ivf_lists})
                """)
                
                # Set probes parameter - needs to be done after index creation
                await cursor.execute(f"""
                    ALTER INDEX "Jobs_embedding_idx" 
                    SET (probes = {settings.vector_ivf_probes})
                """)
                
            elif index_type == 'hnsw' and 'hnsw' in supported_index_types:
                logger.info(f"Creating HNSW index with m={settings.vector_hnsw_m}, ef_construction={settings.vector_hnsw_ef_construction}")
                
                await cursor.execute(f"""
                    CREATE INDEX ON "Jobs" 
                    USING hnsw (embedding vector_l2_ops)
                    WITH (
                        m = {settings.vector_hnsw_m}, 
                        ef_construction = {settings.vector_hnsw_ef_construction}
                    )
                """)
                
                # Set ef_search parameter - needs to be done after index creation
                await cursor.execute(f"""
                    ALTER INDEX "Jobs_embedding_idx" 
                    SET (ef_search = {settings.vector_hnsw_ef_search})
                """)
                
            else:
                logger.warning(f"Index type {index_type} not supported, falling back to basic index")
                # Create a basic GIN index as fallback
                await cursor.execute("""
                    CREATE INDEX ON "Jobs" USING gin(embedding)
                """)
            
            await conn.commit()
            
            # Create additional useful indices
            logger.info("Creating additional useful indices")
            
            # Index on country and city for location filtering
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS "Locations_country_city_idx" 
                ON "Locations" (country, city)
            """)
            
            # Index for text search on job title and description
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS "Jobs_title_description_idx" 
                ON "Jobs" USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')))
            """)
            
            await conn.commit()
            
            logger.success("Vector indices created successfully")
            
    except Exception as e:
        logger.error(f"Error creating vector indices: {str(e)}")
        if conn:
            await conn.rollback()
        raise
    
    finally:
        if conn:
            await conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create vector indices for PostgreSQL")
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Force recreation of indices without confirmation"
    )
    
    args = parser.parse_args()
    
    # Override debug setting if --force is used
    if args.force:
        settings.debug = True
    
    asyncio.run(create_vector_indices())