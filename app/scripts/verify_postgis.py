"""
Verify PostGIS and Vector Search functionality in the database.

This script connects to the database and verifies that:
1. Required extensions are installed (PostGIS, pgvector, pg_diskann, pg_trgm)
2. The geospatial columns and functions are working
3. The trigger for updating the geom column is working
4. Vector search functionality is working
5. Indexes are properly configured
"""

import asyncio
import sys
from loguru import logger

from app.utils.db_utils import get_db_cursor
from app.core.config import settings


async def verify_database_extensions():
    """Verify that all required extensions are installed."""
    logger.info("Verifying database extensions...")
    
    try:
        async with get_db_cursor() as cursor:
            # Check installed extensions
            await cursor.execute("SELECT extname, extversion FROM pg_extension ORDER BY extname")
            extensions = await cursor.fetchall()
            
            # Create a dictionary of extension names and versions
            ext_dict = {ext["extname"]: ext["extversion"] for ext in extensions}
            
            # Check for required extensions
            required_extensions = ["postgis", "vector", "pg_trgm"]
            optional_extensions = ["pg_diskann"]
            
            for ext in required_extensions:
                if ext in ext_dict:
                    logger.info(f"✅ {ext} extension is installed (version {ext_dict[ext]})")
                else:
                    logger.error(f"❌ {ext} extension is NOT installed")
                    return False
            
            for ext in optional_extensions:
                if ext in ext_dict:
                    logger.info(f"✅ {ext} extension is installed (version {ext_dict[ext]})")
                else:
                    logger.warning(f"⚠️ Optional {ext} extension is NOT installed")
            
            # Get PostgreSQL version
            await cursor.execute("SELECT version()")
            pg_version = (await cursor.fetchone())["version"]
            logger.info(f"PostgreSQL version: {pg_version}")
            
            return True
            
    except Exception as e:
        logger.error(f"Error verifying database extensions: {e}")
        return False


async def verify_postgis_setup():
    """Verify PostGIS setup and functionality."""
    logger.info("Verifying PostGIS setup...")
    
    try:
        async with get_db_cursor() as cursor:
            # Check PostGIS version
            await cursor.execute("SELECT PostGIS_Version()")
            result = await cursor.fetchone()
            postgis_version = result.get("postgis_version")
            logger.info(f"PostGIS version: {postgis_version}")
            
            # Check geometry column in Locations table
            await cursor.execute("""
            SELECT f_geometry_column, type, srid, coord_dimension
            FROM geometry_columns
            WHERE f_table_name = 'Locations'
            """)
            geom_column = await cursor.fetchone()
            if geom_column:
                logger.info(f"✅ Geometry column exists: {geom_column}")
            else:
                logger.error("❌ Geometry column does not exist in Locations table")
                return False
                
            # Check if the trigger function exists
            await cursor.execute("""
            SELECT routine_name, routine_definition
            FROM information_schema.routines
            WHERE routine_name = 'update_geom_column' AND routine_type = 'FUNCTION'
            """)
            trigger_function = await cursor.fetchone()
            if trigger_function:
                logger.info(f"✅ Trigger function exists: {trigger_function['routine_name']}")
                logger.debug(f"Trigger function definition: {trigger_function['routine_definition']}")
            else:
                logger.error("❌ Trigger function 'update_geom_column' does not exist")
                return False
                
            # Check if the trigger exists
            await cursor.execute("""
            SELECT trigger_name, event_manipulation, action_statement
            FROM information_schema.triggers
            WHERE trigger_name = 'update_location_geom'
            """)
            triggers = await cursor.fetchall()
            if triggers:
                for trigger in triggers:
                    logger.info(f"✅ Trigger exists: {trigger['trigger_name']} on {trigger['event_manipulation']}")
            else:
                logger.error("❌ Trigger 'update_location_geom' does not exist")
                return False
                
            # Check spatial index
            await cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE indexname = 'idx_locations_geom'
            """)
            spatial_index = await cursor.fetchone()
            if spatial_index:
                logger.info(f"✅ Spatial index exists: {spatial_index['indexname']}")
                logger.debug(f"Index definition: {spatial_index['indexdef']}")
            else:
                logger.error("❌ Spatial index 'idx_locations_geom' does not exist")
                return False
            
            # Test the trigger by inserting a test location
            await cursor.execute("BEGIN")  # Start transaction for rollback
            
            try:
                await cursor.execute("""
                INSERT INTO "Countries" (country_name)
                VALUES ('Test Country')
                RETURNING country_id
                """)
                country_id = (await cursor.fetchone())["country_id"]
                
                await cursor.execute("""
                INSERT INTO "Locations" (city, country, latitude, longitude)
                VALUES ('Test City', %s, 40.7128, -74.0060)
                RETURNING location_id, geom
                """, (country_id,))
                location = await cursor.fetchone()
                
                if location and location.get("geom"):
                    logger.info(f"✅ Trigger successfully updated geom column")
                else:
                    logger.error("❌ Trigger failed to update geom column")
                    await cursor.execute("ROLLBACK")
                    return False
                    
                # Test a spatial query
                await cursor.execute("""
                SELECT ST_Distance(
                    ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography,
                    ST_SetSRID(ST_MakePoint(-73.9352, 40.7306), 4326)::geography
                ) as distance_meters
                """)
                distance = await cursor.fetchone()
                logger.info(f"✅ Distance calculation works: {distance.get('distance_meters'):.2f} meters")
                
                # Test ST_DWithin for radius search
                await cursor.execute("""
                SELECT COUNT(*) FROM "Locations"
                WHERE ST_DWithin(
                    geom::geography,
                    ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography,
                    5000
                )
                """)
                radius_count = await cursor.fetchone()
                logger.info(f"✅ Radius search works: found {radius_count['count']} locations within 5km")
                
            finally:
                # Always rollback the test data
                await cursor.execute("ROLLBACK")
            
            logger.info("PostGIS verification completed successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error verifying PostGIS functionality: {e}")
        return False


async def verify_vector_search():
    """Verify vector search functionality."""
    logger.info("Verifying vector search functionality...")
    
    try:
        async with get_db_cursor() as cursor:
            # Check vector columns in Jobs table
            await cursor.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'Jobs' AND data_type = 'USER-DEFINED'
            AND (column_name = 'embedding' OR column_name = 'sparse_embeddings')
            """)
            vector_columns = await cursor.fetchall()
            
            if vector_columns:
                for col in vector_columns:
                    logger.info(f"✅ Vector column exists: {col['column_name']}")
            else:
                logger.error("❌ No vector columns found in Jobs table")
                return False
            
            # Check vector indexes
            await cursor.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'Jobs' AND indexdef LIKE '%vector%'
            """)
            vector_indexes = await cursor.fetchall()
            
            if vector_indexes:
                for idx in vector_indexes:
                    logger.info(f"✅ Vector index exists: {idx['indexname']}")
                    logger.debug(f"Index definition: {idx['indexdef']}")
            else:
                logger.warning("⚠️ No vector indexes found in Jobs table")
            
            # Check if we can perform a vector similarity search
            # This is a simple test with a random vector - it should at least not error
            try:
                # Create a random 1024-dimension vector (all zeros)
                test_vector = [0.0] * 1024
                
                await cursor.execute("BEGIN")  # Start transaction
                
                # Try a simple vector similarity search
                await cursor.execute("""
                SELECT id, title, embedding <=> %s::vector AS score
                FROM "Jobs"
                WHERE embedding IS NOT NULL
                ORDER BY score
                LIMIT 1
                """, (test_vector,))
                
                result = await cursor.fetchone()
                if result:
                    logger.info(f"✅ Vector similarity search works")
                else:
                    logger.warning("⚠️ Vector similarity search returned no results (but query executed)")
                
                await cursor.execute("ROLLBACK")  # End transaction
                
                return True
                
            except Exception as e:
                logger.error(f"❌ Vector similarity search failed: {e}")
                await cursor.execute("ROLLBACK")  # Ensure rollback on error
                return False
            
    except Exception as e:
        logger.error(f"Error verifying vector search functionality: {e}")
        return False


async def verify_database():
    """Verify all database functionality."""
    logger.info("Starting comprehensive database verification...")
    
    # Check extensions first
    extensions_ok = await verify_database_extensions()
    if not extensions_ok:
        logger.error("Database extensions verification failed")
        return False
    
    # Check PostGIS setup
    postgis_ok = await verify_postgis_setup()
    if not postgis_ok:
        logger.error("PostGIS setup verification failed")
        return False
    
    # Check vector search
    vector_ok = await verify_vector_search()
    if not vector_ok:
        logger.error("Vector search verification failed")
        return False
    
    logger.info("✅ All database verifications completed successfully")
    return True


async def main():
    """Main function."""
    success = await verify_database()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())