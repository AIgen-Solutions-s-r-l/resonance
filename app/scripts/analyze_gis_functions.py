"""
Analyze GIS and Vector Search functions in the database.

This script connects to the database and:
1. Lists all available PostGIS and vector search functions
2. Identifies which functions are being used in the codebase
3. Analyzes database indexes and their usage
4. Provides recommendations for optimization
"""

import asyncio
import sys
from app.log.logging import logger
import re
import os
from pathlib import Path
from typing import Dict, List, Any, Tuple

from app.utils.db_utils import get_db_cursor
from app.core.config import settings


async def get_database_functions(category: str) -> List[Dict[str, Any]]:
    """Get functions from the database by category.
    
    Args:
        category: The category of functions to get ('postgis', 'vector', 'all')
    
    Returns:
        List of function dictionaries with name and type
    """
    logger.info(f"Getting {category} functions from database...")
    
    try:
        async with get_db_cursor() as cursor:
            query = """
            SELECT routine_name, routine_type
            FROM information_schema.routines
            WHERE routine_schema = 'public'
            """
            
            if category == 'postgis':
                query += """
                AND (
                    routine_name LIKE 'st\\_%' OR
                    routine_name LIKE 'postgis\\_%' OR
                    routine_name LIKE 'geography\\_%' OR
                    routine_name LIKE 'geometry\\_%'
                )
                """
            elif category == 'vector':
                query += """
                AND (
                    routine_name LIKE 'vector\\_%' OR
                    routine_name LIKE 'ivfflat\\_%' OR
                    routine_name LIKE 'hnsw\\_%' OR
                    routine_name LIKE 'diskann\\_%'
                )
                """
            
            query += "ORDER BY routine_name"
            
            await cursor.execute(query)
            functions = await cursor.fetchall()
            
            logger.info(f"Found {len(functions)} {category} functions")
            return functions
            
    except Exception as e:
        logger.error(f"Error getting {category} functions: {e}")
        return []


async def get_database_indexes() -> List[Dict[str, Any]]:
    """Get all indexes from the database.
    
    Returns:
        List of index dictionaries with name, table, and definition
    """
    logger.info("Getting database indexes...")
    
    try:
        async with get_db_cursor() as cursor:
            await cursor.execute("""
            SELECT
                tablename,
                indexname,
                indexdef,
                pg_size_pretty(pg_relation_size(indexname::regclass)) as index_size
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY tablename, indexname
            """)
            
            indexes = await cursor.fetchall()
            logger.info(f"Found {len(indexes)} indexes")
            return indexes
            
    except Exception as e:
        logger.error(f"Error getting database indexes: {e}")
        return []


def scan_codebase_for_functions(functions: List[Dict[str, Any]], category: str) -> Dict[str, int]:
    """Scan the codebase for usage of database functions.
    
    Args:
        functions: List of function dictionaries with name and type
        category: The category of functions ('postgis', 'vector', 'all')
    
    Returns:
        Dictionary mapping function names to usage counts
    """
    logger.info(f"Scanning codebase for {category} function usage...")
    
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
    
    logger.info(f"Scanned {files_scanned} files for {category} function usage")
    
    # Filter to only used functions
    used_functions = {name: count for name, count in function_usage.items() if count > 0}
    
    return used_functions


async def analyze_postgis_functions() -> bool:
    """Analyze PostGIS functions in the database and codebase."""
    logger.info("Analyzing PostGIS functions...")
    
    # Get all PostGIS functions
    functions = await get_database_functions('postgis')
    
    if not functions:
        logger.error("No PostGIS functions found")
        return False
        
    # Scan codebase for function usage
    used_functions = scan_codebase_for_functions(functions, 'postgis')
    
    # Print results
    logger.info(f"Found {len(used_functions)} PostGIS functions used in the codebase:")
    
    # Sort by usage count (descending)
    sorted_functions = sorted(used_functions.items(), key=lambda x: x[1], reverse=True)
    
    for func_name, count in sorted_functions[:10]:  # Show top 10
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
    logger.info("\nPostGIS optimization recommendations:")
    
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


async def analyze_vector_functions() -> bool:
    """Analyze vector search functions in the database and codebase."""
    logger.info("Analyzing vector search functions...")
    
    # Get all vector functions
    functions = await get_database_functions('vector')
    
    if not functions:
        logger.warning("No vector functions found, this may be normal depending on the pgvector version")
    
    # Scan codebase for vector operators
    vector_operators = [
        '<->',  # L2 distance
        '<=>',  # Cosine distance
        '<#>',  # Inner product
    ]
    
    # Get the root directory of the project
    root_dir = Path(__file__).parent.parent.parent
    
    # Dictionary to track operator usage
    operator_usage = {op: 0 for op in vector_operators}
    
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
                        content = f.read()
                        files_scanned += 1
                        
                        # Check for each operator
                        for op in vector_operators:
                            # Escape special characters for regex
                            escaped_op = re.escape(op)
                            pattern = r'\b\w+\s*' + escaped_op + r'\s*\%s'
                            matches = re.findall(pattern, content)
                            operator_usage[op] += len(matches)
                except Exception as e:
                    logger.error(f"Error scanning file {file_path}: {e}")
    
    logger.info(f"Scanned {files_scanned} files for vector operator usage")
    
    # Print results
    logger.info("Vector operator usage:")
    for op, count in operator_usage.items():
        logger.info(f"  {op}: {count} occurrences")
    
    # Check vector indexes
    async with get_db_cursor() as cursor:
        await cursor.execute("""
        SELECT indexname, indexdef
        FROM pg_indexes
        WHERE indexdef LIKE '%vector%' OR indexdef LIKE '%diskann%'
        ORDER BY indexname
        """)
        
        vector_indexes = await cursor.fetchall()
        
        logger.info(f"\nFound {len(vector_indexes)} vector indexes:")
        for idx in vector_indexes:
            logger.info(f"  {idx['indexname']}")
            logger.debug(f"    {idx['indexdef']}")
    
    # Vector optimization recommendations
    logger.info("\nVector search optimization recommendations:")
    
    if any(count > 0 for count in operator_usage.values()):
        logger.info("  - Ensure vector columns have appropriate indexes for the distance operators used")
        logger.info("  - Consider using diskann indexes for large datasets (>100k vectors)")
        logger.info("  - For cosine similarity (<=>), normalize vectors before insertion for better performance")
    
    return True


async def analyze_database_indexes() -> bool:
    """Analyze database indexes and their usage."""
    logger.info("Analyzing database indexes...")
    
    # Get all indexes
    indexes = await get_database_indexes()
    
    if not indexes:
        logger.error("No indexes found")
        return False
    
    # Categorize indexes
    btree_indexes = []
    gist_indexes = []
    gin_indexes = []
    vector_indexes = []
    other_indexes = []
    
    for idx in indexes:
        if 'using btree' in idx['indexdef'].lower():
            btree_indexes.append(idx)
        elif 'using gist' in idx['indexdef'].lower():
            gist_indexes.append(idx)
        elif 'using gin' in idx['indexdef'].lower():
            gin_indexes.append(idx)
        elif 'vector' in idx['indexdef'].lower() or 'diskann' in idx['indexdef'].lower():
            vector_indexes.append(idx)
        else:
            other_indexes.append(idx)
    
    # Print index statistics
    logger.info(f"Index statistics:")
    logger.info(f"  Total indexes: {len(indexes)}")
    logger.info(f"  B-tree indexes: {len(btree_indexes)}")
    logger.info(f"  GiST indexes (spatial): {len(gist_indexes)}")
    logger.info(f"  GIN indexes (text search): {len(gin_indexes)}")
    logger.info(f"  Vector indexes: {len(vector_indexes)}")
    logger.info(f"  Other indexes: {len(other_indexes)}")
    
    # Print largest indexes
    sorted_by_size = sorted(indexes, key=lambda x: x['index_size'], reverse=True)
    logger.info("\nLargest indexes:")
    for idx in sorted_by_size[:5]:  # Top 5
        logger.info(f"  {idx['indexname']} ({idx['index_size']})")
    
    # Index optimization recommendations
    logger.info("\nIndex optimization recommendations:")
    logger.info("  - Consider analyzing index usage with pg_stat_user_indexes to identify unused indexes")
    logger.info("  - For vector indexes, ensure the index parameters (max_neighbors, l_value_ib) are optimized")
    logger.info("  - For spatial indexes, ensure the SRID is consistent across all geometry columns")
    
    return True


async def analyze_database():
    """Analyze all database functions and indexes."""
    logger.info("Starting comprehensive database analysis...")
    
    # Analyze PostGIS functions
    postgis_ok = await analyze_postgis_functions()
    
    # Analyze vector functions
    vector_ok = await analyze_vector_functions()
    
    # Analyze database indexes
    indexes_ok = await analyze_database_indexes()
    
    if postgis_ok and vector_ok and indexes_ok:
        logger.info("Database analysis completed successfully")
        return True
    else:
        logger.warning("Database analysis completed with some issues")
        return False


async def main():
    """Main function."""
    success = await analyze_database()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())