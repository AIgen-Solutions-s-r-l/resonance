"""
Analyze GIS functions in the database.

This script connects to the database and:
1. Lists all available PostGIS functions
2. Identifies which functions are being used in the codebase
3. Provides recommendations for optimization
"""

import asyncio
import sys
from loguru import logger
import re
import os
from pathlib import Path

from app.utils.db_utils import get_db_cursor
from app.core.config import settings


async def get_postgis_functions():
    """Get all PostGIS functions from the database."""
    logger.info("Getting PostGIS functions...")
    
    try:
        async with get_db_cursor() as cursor:
            # Query to get all PostGIS functions
            await cursor.execute("""
            SELECT routine_name, routine_type
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            AND (
                routine_name LIKE 'st\\_%' OR 
                routine_name LIKE 'postgis\\_%' OR
                routine_name LIKE 'geography\\_%' OR
                routine_name LIKE 'geometry\\_%'
            )
            ORDER BY routine_name
            """)
            
            functions = await cursor.fetchall()
            logger.info(f"Found {len(functions)} PostGIS functions")
            return functions
            
    except Exception as e:
        logger.error(f"Error getting PostGIS functions: {e}")
        return []


def scan_codebase_for_gis_functions(functions):
    """Scan the codebase for usage of PostGIS functions."""
    logger.info("Scanning codebase for GIS function usage...")
    
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent
    
    # Dictionary to track function usage
    function_usage = {func["routine_name"].lower(): 0 for func in functions}
    
    # Files to scan
    files_scanned = 0
    
    # Walk through the project directory
    for root, dirs, files in os.walk(root_dir):
        # Skip virtual environments, node_modules, etc.
        if any(excluded in root for excluded in ['.venv', 'node_modules', '.git']):
            continue
            
        for file in files:
            # Only scan Python, SQL, and migration files
            if file.endswith(('.py', '.sql', '.pgsql')):
                file_path = os.path.join(root, file)
                
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read().lower()
                        files_scanned += 1
                        
                        # Check for each function
                        for func_name in function_usage.keys():
                            # Look for the function name in SQL context
                            pattern = r'\b' + re.escape(func_name) + r'\s*\('
                            matches = re.findall(pattern, content)
                            function_usage[func_name] += len(matches)
                except Exception as e:
                    logger.error(f"Error scanning file {file_path}: {e}")
    
    logger.info(f"Scanned {files_scanned} files for GIS function usage")
    
    # Filter to only used functions
    used_functions = {name: count for name, count in function_usage.items() if count > 0}
    
    return used_functions


async def analyze_gis_functions():
    """Analyze GIS functions in the database and codebase."""
    logger.info("Analyzing GIS functions...")
    
    # Get all PostGIS functions
    functions = await get_postgis_functions()
    
    if not functions:
        logger.error("No PostGIS functions found")
        return False
        
    # Scan codebase for function usage
    used_functions = scan_codebase_for_gis_functions(functions)
    
    # Print results
    logger.info(f"Found {len(used_functions)} PostGIS functions used in the codebase:")
    
    # Sort by usage count (descending)
    sorted_functions = sorted(used_functions.items(), key=lambda x: x[1], reverse=True)
    
    for func_name, count in sorted_functions:
        logger.info(f"  {func_name}: {count} occurrences")
    
    # Identify key spatial functions
    key_functions = [
        'st_dwithin',
        'st_makepoint',
        'st_setsrid',
        'st_distance',
        'st_transform',
        'st_contains'
    ]
    
    logger.info("\nKey spatial functions usage:")
    for func in key_functions:
        count = used_functions.get(func, 0)
        logger.info(f"  {func}: {count} occurrences")
    
    # Check for optimization opportunities
    logger.info("\nOptimization recommendations:")
    
    # Check if ST_DWithin is being used with geography type
    if used_functions.get('st_dwithin', 0) > 0:
        logger.info("  - Ensure ST_DWithin is used with ::geography cast for accurate distance calculations")
    
    # Check if spatial indexes are likely being used
    if used_functions.get('st_dwithin', 0) > 0 or used_functions.get('st_contains', 0) > 0:
        logger.info("  - Verify GiST indexes exist on geometry columns for optimal performance")
    
    # Check for potential coordinate transformations
    if used_functions.get('st_transform', 0) > 0:
        logger.info("  - Consider standardizing on a single coordinate system to minimize transformations")
    
    return True


async def main():
    """Main function."""
    success = await analyze_gis_functions()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())