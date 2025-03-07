#!/usr/bin/env python
"""
Fixed script to create optimized vector indices for PostgreSQL.

This script creates the necessary vector indices on the embedding column
to significantly improve query performance for vector similarity operations.
"""

import asyncio
import psycopg
from psycopg.sql import SQL, Identifier
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.config import settings
from app.log.logging import logger

print("Starting vector indices creation...")

async def create_vector_indices():
    """Create vector indices for the Jobs table."""
    print("Creating vector indices on Jobs table")
    logger.info("Creating vector indices on Jobs table")
    
    conn = None
    try:
        # Connect to database
        print(f"Connecting to database: {settings.database_url}")
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        
        # Create cursor
        async with conn.cursor() as cursor:
            # Check existing indices
            print("Checking existing indices...")
            await cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'Jobs' AND indexdef LIKE '%embedding%'
            """)
            existing_indices = await cursor.fetchall()
            
            if existing_indices:
                print(f"Found {len(existing_indices)} existing vector indices:")
                for idx_name, idx_def in existing_indices:
                    print(f"  {idx_name}: {idx_def}")
                    
                # Drop existing indices
                for idx_name, _ in existing_indices:
                    print(f"Dropping index {idx_name}")
                    await cursor.execute(f"DROP INDEX IF EXISTS \"{idx_name}\"")
                
                await conn.commit()
            
            # Check which vector index types are supported
            print("Checking supported vector index types...")
            await cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
            if not await cursor.fetchone():
                print("ERROR: vector extension not installed")
                return

            # Try IVFFLAT index first (best for performance)
            try:
                print("Creating IVFFLAT index on embedding column...")
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
                print("IVFFLAT index created successfully!")
                
            except Exception as e:
                print(f"Failed to create IVFFLAT index: {str(e)}")
                print("Trying fallback to vector_ops index...")
                
                try:
                    # Create a basic vector index as fallback
                    await cursor.execute("""
                        CREATE INDEX ON "Jobs" USING ivfflat(embedding vector_l2_ops)
                    """)
                    print("Basic vector index created successfully")
                except Exception as e:
                    print(f"Failed to create basic vector index: {str(e)}")
                    raise
            
            await conn.commit()
            
            # Create additional useful indices
            print("Creating additional useful indices...")
            
            # Index on country and city for location filtering
            await cursor.execute("""
                CREATE INDEX IF NOT EXISTS "Locations_country_city_idx" 
                ON "Locations" (country, city)
            """)
            
            # Index for text search on job title and description
            try:
                await cursor.execute("""
                    CREATE INDEX IF NOT EXISTS "Jobs_title_description_idx" 
                    ON "Jobs" USING gin(to_tsvector('english', title || ' ' || COALESCE(description, '')))
                """)
                print("Text search index created successfully")
            except Exception as e:
                print(f"Failed to create text search index: {str(e)} - continuing anyway")
            
            await conn.commit()
            
            # Verify the indices
            print("Verifying indices...")
            await cursor.execute("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'Jobs'
                ORDER BY indexname
            """)
            all_indices = await cursor.fetchall()
            
            print(f"Total indices on Jobs table: {len(all_indices)}")
            for idx_name, idx_def in all_indices:
                print(f"  {idx_name}: {idx_def}")
            
            print("Vector indices created successfully")
            
    except Exception as e:
        print(f"Error creating vector indices: {str(e)}")
        if conn:
            await conn.rollback()
        raise
    
    finally:
        if conn:
            await conn.close()
        print("Vector indices creation completed")

if __name__ == "__main__":
    asyncio.run(create_vector_indices())
    print("Script execution completed")