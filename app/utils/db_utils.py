"""
Database utilities for optimized connection management and query execution.

This module provides utilities for database connection pooling, 
optimized query execution, and vector similarity operations.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Callable, TypeVar, Generic, Tuple
from contextlib import asynccontextmanager
import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

from app.core.config import settings
from app.log.logging import logger
from app.metrics.database import async_sql_query_timer

# Type variable for generic connection pool
T = TypeVar('T')

# Global connection pool
_connection_pools: Dict[str, AsyncConnectionPool] = {}
_pool_lock = asyncio.Lock()


async def get_connection_pool(pool_name: str = "default") -> AsyncConnectionPool:
    """
    Get or create a connection pool for the specified name.
    
    Args:
        pool_name: Name of the connection pool
        
    Returns:
        AsyncConnectionPool: The connection pool
    """
    async with _pool_lock:
        if pool_name not in _connection_pools:
            logger.info(
                "Creating new connection pool",
                pool_name=pool_name
            )
            
            # Create connection pool with optimal settings
            pool = AsyncConnectionPool(
                conninfo=settings.database_url,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size,
                timeout=settings.db_pool_timeout,
                max_idle=settings.db_pool_max_idle,
                kwargs={"row_factory": dict_row}  # Use dictionary row factory
            )
            
            # Initialize the pool by pre-connecting min_size connections
            await pool.wait()
            
            _connection_pools[pool_name] = pool
            
            logger.info(
                "Connection pool created successfully",
                pool_name=pool_name,
                min_size=settings.db_pool_min_size,
                max_size=settings.db_pool_max_size
            )
            
        return _connection_pools[pool_name]


@asynccontextmanager
async def get_db_connection(pool_name: str = "default"):
    """
    Get a database connection from the pool.
    
    Args:
        pool_name: Name of the connection pool
        
    Yields:
        A database connection from the pool
    """
    pool = await get_connection_pool(pool_name)
    conn = await pool.getconn()
    
    try:
        yield conn
    finally:
        await pool.putconn(conn)


@asynccontextmanager
async def get_db_cursor(pool_name: str = "default"):
    """
    Get a database cursor from a pooled connection.
    
    Args:
        pool_name: Name of the connection pool
        
    Yields:
        A database cursor
    """
    async with get_db_connection(pool_name) as conn:
        async with conn.cursor(row_factory=dict_row) as cursor:
            yield cursor


@async_sql_query_timer("vector_similarity_query")
async def execute_vector_similarity_query(
    cursor: psycopg.AsyncCursor,
    cv_embedding: List[float],
    where_clauses: List[str],
    query_params: List[Any],
    limit: int = 5,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """
    Execute an optimized vector similarity query.
    
    This function uses optimized query patterns for vector similarity search.
    
    Args:
        cursor: Database cursor
        cv_embedding: Resume vector embedding
        where_clauses: SQL WHERE clauses
        query_params: Query parameters
        limit: Maximum number of results to return
        offset: Number of results to skip
        
    Returns:
        List of matched job results
    """
    # Build WHERE clause
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    
    # Add vector embedding parameters to the beginning of params list
    params = [cv_embedding, cv_embedding, cv_embedding]
    params.extend(query_params)
    params.extend([limit, offset])
    
    # Optimized query using a direct approach for vector operations
    query = f"""
    SELECT
        j.id,
        j.title,
        j.description,
        j.workplace_type,
        j.short_description,
        j.field,
        j.experience,
        j.skills_required,
        j.posted_date,
        j.job_state,
        j.apply_link,
        co.country_name AS country,
        l.city,
        c.company_name,
        c.logo AS company_logo,
        'test_portal' AS portal,
        -- Calculate combined score directly without CTEs for better performance
        (
            -- L2 distance (weighted 0.4)
            (1 - (embedding <-> %s::vector) / 
                CASE WHEN (SELECT MAX(embedding <-> %s::vector) FROM "Jobs" j2 {where_sql}) = 0 
                THEN 1 ELSE (SELECT MAX(embedding <-> %s::vector) FROM "Jobs" j2 {where_sql}) END
            ) * 0.4
            +
            -- Cosine distance (weighted 0.4)
            (1 - embedding <=> %s::vector) * 0.4
            +
            -- Inner product (weighted 0.2)
            ((embedding <#> %s::vector) * -1 + 1) * 0.2
        ) AS score
    FROM "Jobs" j
    LEFT JOIN "Companies" c ON j.company_id = c.company_id
    LEFT JOIN "Locations" l ON j.location_id = l.location_id
    LEFT JOIN "Countries" co ON l.country = co.country_id
    {where_sql}
    ORDER BY score DESC
    LIMIT %s OFFSET %s
    """
    
    # Update params for the optimized query (we added two more cv_embedding parameters)
    params = [cv_embedding, cv_embedding, cv_embedding, cv_embedding, cv_embedding]
    params.extend(query_params)
    params.extend([limit, offset])
    
    await cursor.execute(query, params)
    results = await cursor.fetchall()
    
    return results


@async_sql_query_timer("simple_count_query")
async def get_filtered_job_count(
    cursor: psycopg.AsyncCursor,
    where_clauses: List[str],
    query_params: List[Any]
) -> int:
    """
    Get the count of jobs matching the filter criteria.
    
    Args:
        cursor: Database cursor
        where_clauses: SQL WHERE clauses
        query_params: Query parameters
        
    Returns:
        Number of matching jobs
    """
    # Build WHERE clause
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)
    
    count_query = f"""
    SELECT COUNT(*) AS count
    FROM "Jobs" j
    LEFT JOIN "Companies" c ON j.company_id = c.company_id
    LEFT JOIN "Locations" l ON j.location_id = l.location_id
    LEFT JOIN "Countries" co ON l.country = co.country_id
    {where_sql}
    """
    
    await cursor.execute(count_query, query_params)
    result = await cursor.fetchone()
    return result["count"] if result else 0


async def close_all_connection_pools():
    """Close all connection pools."""
    async with _pool_lock:
        for pool_name, pool in _connection_pools.items():
            logger.info(
                "Closing connection pool",
                pool_name=pool_name
            )
            await pool.close()
        
        _connection_pools.clear()