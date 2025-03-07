#!/usr/bin/env python
import asyncio
import psycopg
import os
import sys
from pathlib import Path

# Add project root to path
project_root = str(Path(__file__).parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from app.core.config import settings
from app.log.logging import logger

print("Starting pgvector setup...")

async def setup_pgvector():
    """
    Set up pgvector extension in the PostgreSQL database.
    """
    print("Setting up pgvector extension")
    logger.info("Setting up pgvector extension")
    
    conn = None
    try:
        # Connect to database
        print(f"Connecting to database with URL: {settings.database_url}")
        conn = await psycopg.AsyncConnection.connect(settings.database_url)
        
        # Create cursor
        async with conn.cursor() as cursor:
            # Check if pgvector extension exists
            print("Checking for pgvector extension...")
            await cursor.execute("SELECT * FROM pg_available_extensions WHERE name = 'vector'")
            result = await cursor.fetchone()
            
            if not result:
                print("pgvector extension is not available in this PostgreSQL installation")
                print("Please install pgvector extension in PostgreSQL first:")
                print("  - For Debian/Ubuntu: sudo apt install postgresql-14-pgvector")
                print("  - For manual installation: https://github.com/pgvector/pgvector#installation")
                return
            
            print("pgvector extension is available")
            
            # Create extension if it exists but isn't installed
            print("Creating extension if not exists...")
            await cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
            await conn.commit()
            
            # Verify extension is installed
            print("Verifying extension installation...")
            await cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector'")
            result = await cursor.fetchone()
            
            if result:
                print("pgvector extension is successfully installed")
                
                # Check version
                await cursor.execute("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
                version = await cursor.fetchone()
                if version:
                    print(f"pgvector version: {version[0]}")
                
                # Create a simple test vector
                try:
                    await cursor.execute("SELECT '[1,2,3]'::vector")
                    await cursor.fetchone()
                    print("Vector data type is working correctly")
                except Exception as e:
                    print(f"Vector data type test failed: {str(e)}")
            else:
                print("Failed to install pgvector extension")
                
    except Exception as e:
        print(f"Error setting up pgvector: {str(e)}")
        if conn:
            await conn.rollback()
    
    finally:
        if conn:
            await conn.close()
        print("pgvector setup completed")

if __name__ == "__main__":
    asyncio.run(setup_pgvector())
    print("Script execution completed")