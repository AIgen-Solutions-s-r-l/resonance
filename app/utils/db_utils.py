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
T = TypeVar("T")

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
    logger.debug(f"Requesting connection pool: {pool_name}")
    async with _pool_lock:
        if pool_name not in _connection_pools:
            logger.info("Creating new connection pool", pool_name=pool_name)

            try:
                # Create connection pool with optimal settings
                pool = AsyncConnectionPool(
                    conninfo=settings.database_url,
                    min_size=settings.db_pool_min_size,
                    max_size=settings.db_pool_max_size,
                    timeout=settings.db_pool_timeout,
                    max_idle=settings.db_pool_max_idle,
                    # Use dictionary row factory
                    kwargs={"row_factory": dict_row},
                    open=False,  # Don't open in constructor to avoid deprecation warning
                )

                logger.debug(
                    f"Connection pool created with URL: {settings.database_url[:10]}..., now opening"
                )

                # Explicitly open the pool
                await pool.open()

                _connection_pools[pool_name] = pool

                logger.info(
                    "Connection pool created successfully",
                    pool_name=pool_name,
                    min_size=settings.db_pool_min_size,
                    max_size=settings.db_pool_max_size,
                )
            except Exception as e:
                logger.exception(f"Error creating connection pool: {str(e)}")
                raise

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
    logger.debug(f"Acquiring connection from pool: {pool_name}")
    start_time = time.time()

    try:
        pool = await get_connection_pool(pool_name)
        conn = await pool.getconn()
        logger.debug(f"Connection acquired in {time.time() - start_time:.6f}s")

        try:
            yield conn
        finally:
            logger.debug("Returning connection to pool")
            await pool.putconn(conn)
    except Exception as e:
        logger.exception(f"Error in database connection management: {str(e)}")
        raise


@asynccontextmanager
async def get_db_cursor(pool_name: str = "default"):
    """
    Get a database cursor from a pooled connection.

    Args:
        pool_name: Name of the connection pool

    Yields:
        A database cursor
    """
    logger.debug(f"Getting cursor from pool: {pool_name}")
    start_time = time.time()

    try:
        async with get_db_connection(pool_name) as conn:
            logger.debug("Creating cursor")
            async with conn.cursor(row_factory=dict_row) as cursor:
                logger.debug(f"Cursor created in {time.time() - start_time:.6f}s")
                yield cursor
    except Exception as e:
        logger.exception(f"Error getting database cursor: {str(e)}")
        raise


@async_sql_query_timer("vector_similarity_query")
async def execute_vector_similarity_query(
    cursor: psycopg.AsyncCursor,
    cv_embedding: List[float],
    where_clauses: List[str],
    query_params: List[Any],
    limit: int = 50,
    offset: int = 0,
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
    start_time = time.time()

    # Build WHERE clause
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # Create a separate sql_params list for the query
    # This ensures we include the vector embeddings in the correct positions
    sql_params = []

    # Simpler query that should execute faster for troubleshooting
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
        j.portal AS portal,
        0.0 AS score

    FROM "Jobs" j
    LEFT JOIN "Companies" c ON j.company_id = c.company_id
    LEFT JOIN "Locations" l ON j.location_id = l.location_id
    LEFT JOIN "Countries" co ON l.country = co.country_id
    {where_sql}
    ORDER BY embedding <=> %s::vector
    LIMIT %s OFFSET %s
    """

    # Simplified parameter handling
    # Add filter params for the WHERE clause
    sql_params.extend(query_params)

    # Just one embedding parameter for cosine similarity
    sql_params.append(cv_embedding)

    # Add limit and offset
    sql_params.append(limit)
    sql_params.append(offset)

    # Log parameter structure for debugging
    logger.info(
        "DB_UTILS: Simplified parameter structure",
        embedding_count=1,
        where_params_count=len(query_params),
        total_params=len(sql_params),
        country_filter=[p for p in query_params if isinstance(p, str)],
    )

    # Log query for debugging
    logger.info(
        "DB_UTILS: Executing vector similarity query",
        param_count=len(sql_params),
        where_clause_count=len(where_clauses),
        has_filter=bool(where_clauses),
        embedding_length=(
            len(cv_embedding) if isinstance(cv_embedding, list) else "unknown"
        ),
        query_size=len(query),
    )

    # Detailed parameter breakdown for debugging
    logger.info(
        "DB_UTILS: Parameter structure analysis",
        where_clauses=where_clauses,
        query_params=(
            str(query_params)[:100] + "..."
            if len(str(query_params)) > 100
            else query_params
        ),
        query_param_types=[type(p).__name__ for p in query_params],
        sql_params_count=len(sql_params),
        first_few_params=str(sql_params[:2])[:50] + "...",
    )

    try:
        logger.info("DB_UTILS: Executing database query - starting")
        logger.info("Check1")
        logger.info(f"DB_UTILS: Query: {query}")
        query_start = time.time()
        # is relative important the consistency, important is resolve when hight concurrency
        await cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
        # specific for diskann
        await cursor.execute("SET LOCAL enable_seqscan TO OFF")
        await cursor.execute(query, sql_params)
        query_time = time.time() - query_start
        logger.debug(
            f"Query execution completed in {query_time:.6f}s, now fetching results"
        )

        fetch_start = time.time()
        results = await cursor.fetchall()
        fetch_time = time.time() - fetch_start

        logger.debug(
            "Query results fetched",
            result_count=len(results),
            query_time=f"{query_time:.6f}s",
            fetch_time=f"{fetch_time:.6f}s",
            total_time=f"{time.time() - start_time:.6f}s",
        )
        return results
    except Exception as e:
        logger.error(
            "Error executing vector similarity query",
            error=str(e),
            error_type=type(e).__name__,
            where_clauses=where_clauses,
            param_count=len(sql_params),
            elapsed_time=f"{time.time() - start_time:.6f}s",
        )
        raise


@async_sql_query_timer("simple_count_query")
async def get_filtered_job_count(
    cursor: psycopg.AsyncCursor,
    where_clauses: List[str],
    query_params: List[Any],
    fast: bool = False,
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
    start_time = time.time()

    # Build WHERE clause
    where_sql = ""
    if where_clauses:
        where_sql = "WHERE " + " AND ".join(where_clauses)

    # In case of large datasets, we can use a faster query to quickly determine if there are more than 5 elements.
    # This helps in deciding the next steps and which query to use subsequently.
    count_query = f"""
        WITH JobData AS (
            SELECT 1
            FROM "Jobs" j
            LEFT JOIN "Companies" c ON j.company_id = c.company_id
            LEFT JOIN "Locations" l ON j.location_id = l.location_id
            LEFT JOIN "Countries" co ON l.country = co.country_id
            {where_sql}
            LIMIT 6
        )
        SELECT
            COUNT(*) AS count
        FROM JobData
        """

    if not fast:
        count_query = f"""
        SELECT COUNT(*) AS count
        FROM "Jobs" j
        LEFT JOIN "Companies" c ON j.company_id = c.company_id
        LEFT JOIN "Locations" l ON j.location_id = l.location_id
        LEFT JOIN "Countries" co ON l.country = co.country_id
        {where_sql}
        """

    logger.debug(
        "Executing count query",
        where_clause_count=len(where_clauses),
        has_filter=bool(where_clauses),
        param_count=len(query_params),
    )

    try:
        query_start = time.time()
        await cursor.execute(count_query, query_params)
        query_time = time.time() - query_start

        fetch_start = time.time()
        result = await cursor.fetchone()
        fetch_time = time.time() - fetch_start

        count = result["count"] if result else 0

        logger.debug(
            "Count query completed",
            count=count,
            query_time=f"{query_time:.6f}s",
            fetch_time=f"{fetch_time:.6f}s",
            total_time=f"{time.time() - start_time:.6f}s",
        )

        return count
    except Exception as e:
        logger.error(
            "Error executing count query",
            error=str(e),
            error_type=type(e).__name__,
            where_clauses=where_clauses,
            param_count=len(query_params),
            elapsed_time=f"{time.time() - start_time:.6f}s",
        )
        raise


async def close_all_connection_pools():
    """Close all connection pools."""
    logger.debug("Closing all connection pools")
    start_time = time.time()

    try:
        async with _pool_lock:
            for pool_name, pool in _connection_pools.items():
                logger.info("Closing connection pool", pool_name=pool_name)
                await pool.close()

            _connection_pools.clear()
            logger.debug(
                f"All connection pools closed in {time.time() - start_time:.6f}s"
            )
    except Exception as e:
        logger.exception(f"Error closing connection pools: {str(e)}")
        raise
