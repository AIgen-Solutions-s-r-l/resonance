#!/usr/bin/env python3
"""
Test script to verify database connectivity with the provided credentials
"""
import asyncio
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

async def test_connection():
    # Test connection with testuser/testpassword
    conn_string = "postgresql://testuser:testpassword@localhost:5432/postgres"
    print(f"Testing connection with: {conn_string}")
    
    try:
        pool = AsyncConnectionPool(
            conninfo=conn_string,
            min_size=1,
            max_size=2,
            kwargs={"row_factory": dict_row},
            open=False  # Don't open in constructor
        )
        
        # Explicitly open the pool
        await pool.open()
        print("✅ Connection pool opened successfully")
        
        # Test a simple query
        async with pool.connection() as conn:
            async with conn.cursor() as cursor:
                print("✅ Got cursor, running test query...")
                await cursor.execute("SELECT 1 as test")
                result = await cursor.fetchone()
                print(f"Query result: {result}")
        
        # Close the pool
        await pool.close()
        print("✅ Connection test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_connection())