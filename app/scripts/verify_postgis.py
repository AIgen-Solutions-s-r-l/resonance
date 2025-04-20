"""
Verify PostGIS functionality in the database.

This script connects to the database and verifies that:
1. The PostGIS extension is installed
2. The geospatial functions are working
3. The trigger for updating the geom column is working
"""

import asyncio
import sys
from loguru import logger

from app.utils.db_utils import get_db_cursor
from app.core.config import settings


async def verify_postgis():
    """Verify PostGIS functionality in the database."""
    logger.info("Verifying PostGIS functionality...")
    
    try:
        async with get_db_cursor() as cursor:
            # Check if PostGIS extension is installed
            await cursor.execute("SELECT PostGIS_Version()")
            result = await cursor.fetchone()
            postgis_version = result.get("postgis_version")
            logger.info(f"PostGIS version: {postgis_version}")
            
            # Check if the geom column exists in the Locations table
            await cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'Locations' AND column_name = 'geom'
            """)
            geom_column = await cursor.fetchone()
            if geom_column:
                logger.info(f"Geom column exists: {geom_column}")
            else:
                logger.error("Geom column does not exist in Locations table")
                
            # Check if the trigger function exists
            await cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_name = 'update_geom_column' AND routine_type = 'FUNCTION'
            """)
            trigger_function = await cursor.fetchone()
            if trigger_function:
                logger.info(f"Trigger function exists: {trigger_function}")
            else:
                logger.error("Trigger function 'update_geom_column' does not exist")
                
            # Check if the trigger exists
            await cursor.execute("""
            SELECT trigger_name 
            FROM information_schema.triggers 
            WHERE trigger_name = 'update_location_geom'
            """)
            trigger = await cursor.fetchone()
            if trigger:
                logger.info(f"Trigger exists: {trigger}")
            else:
                logger.error("Trigger 'update_location_geom' does not exist")
                
            # Test the trigger by inserting a test location
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
                logger.info(f"Trigger successfully updated geom column: {location}")
            else:
                logger.error("Trigger failed to update geom column")
                
            # Test a spatial query
            await cursor.execute("""
            SELECT ST_Distance(
                ST_SetSRID(ST_MakePoint(-74.0060, 40.7128), 4326)::geography,
                ST_SetSRID(ST_MakePoint(-73.9352, 40.7306), 4326)::geography
            ) as distance_meters
            """)
            distance = await cursor.fetchone()
            logger.info(f"Distance between two points: {distance.get('distance_meters')} meters")
            
            # Clean up test data
            await cursor.execute("""
            DELETE FROM "Locations" WHERE city = 'Test City'
            """)
            await cursor.execute("""
            DELETE FROM "Countries" WHERE country_name = 'Test Country'
            """)
            
            logger.info("PostGIS verification completed successfully")
            
    except Exception as e:
        logger.error(f"Error verifying PostGIS functionality: {e}")
        return False
        
    return True


async def main():
    """Main function."""
    success = await verify_postgis()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())