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
from app.schemas.job_match import ManyToManyFilter

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
                    # Configure reconnection and reset behavior
                    max_lifetime=settings.db_pool_max_lifetime,
                    check=AsyncConnectionPool.check,
                    reconnect_timeout=30 
                )

                logger.debug(
                    f"Connection pool created with URL: {settings.database_url[:10]}..., now opening"
                )
                logger.info(
                    f"Pool config: min={settings.db_pool_min_size}, max={settings.db_pool_max_size}, timeout={settings.db_pool_timeout}s"
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
        async with pool.connection() as conn:

            logger.debug(f"Connection acquired in {time.time() - start_time:.6f}s")

            try:
                logger.debug(f"Connection status before yielding: {{'closed': conn.closed, 'broken': conn.broken, 'pgconn': conn.pgconn is not None}}")
                yield conn
            finally:
                logger.debug("Returning connection to pool")

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
                logger.debug(f"Cursor status before yielding: {{'closed': cursor.closed, 'connection_closed': cursor.connection.closed if cursor.connection else 'N/A'}}")
                yield cursor
    except Exception as e:
        logger.exception(f"Error getting database cursor: {str(e)}")
        raise


@async_sql_query_timer("simple_query")
async def execute_simple_query(
    cursor: psycopg.AsyncCursor,
    many_to_many_filters: List[ManyToManyFilter],
    where_clauses: List[str],
    query_params: List[Any],
    limit: int = 25,
    offset: int = 0,
    blacklisted_job_ids: Optional[List[int]] = None
) -> List[Dict[str, Any]]:
    start_time = time.time()

    # Build WHERE clause components
    all_where_clauses = []
    # Add clauses generated by query_builder
    if len(where_clauses) > 0:
        all_where_clauses.extend(where_clauses)

    # Add blacklisted jobs filter if provided
    if blacklisted_job_ids:
        # Ensure it's not an empty list before adding the clause
        if blacklisted_job_ids:
            all_where_clauses.append("j.id <> ALL(%s)") # Use ANY/ALL for list parameter
            logger.info(f"Filtering out {len(blacklisted_job_ids)} applied job IDs.")
        else:
            logger.info("Applied job IDs list is empty, skipping filter.")

    # Construct the final WHERE string
    where_sql = ""
    if len(all_where_clauses) > 0:
        where_sql = "WHERE " + " AND ".join(all_where_clauses) # e.g., "WHERE embedding IS NOT NULL AND co.country_name = %s AND j.experience = %s AND j.id NOT IN %s"

    query = "WITH\n"
    sql_params = []

    if many_to_many_filters is not None and len(many_to_many_filters) > 0:
        relationships = ", ".join([mtm.relationship for mtm in many_to_many_filters])
        query += f"""
        "Jobs" AS (
            SELECT selected.*
            FROM "Jobs" as selected
            WHERE EXISTS (
                SELECT 1 FROM {relationships}
                WHERE """
        query += "AND ".join([mtm.where_clause for mtm in many_to_many_filters])
        sql_params += [param for mtm in many_to_many_filters for param in mtm.params]
        query += """
            )
        ),
        """

    # Define the query using the constructed where_sql
    query += f"""
    "JobMatches" AS (
        SELECT
            j.id AS id,
            j.title AS title,
            j.description AS description,
            j.workplace_type AS workplace_type,
            j.short_description AS short_description,
            j.experience AS experience,
            j.skills_required AS skills_required,
            j.posted_date AS posted_date,
            j.job_state AS job_state,
            j.apply_link AS apply_link,
            co.country_name AS country,
            l.city AS city,
            c.company_name AS company_name,
            c.logo AS company_logo,
            j.portal AS portal
        FROM "Jobs" AS j
        LEFT JOIN "Companies" c ON j.company_id = c.company_id
        LEFT JOIN "Locations" l ON j.location_id = l.location_id
        LEFT JOIN "Countries" co ON l.country = co.country_id
        {where_sql}
        ORDER BY posted_date desc
        LIMIT %s OFFSET %s
    )

    SELECT jm.*, f.root_field, f.sub_field
    FROM "JobMatches" as jm 
    LEFT JOIN "FieldJobs" as fj ON jm.id = fj.job_id
    LEFT JOIN "Fields" as f ON fj.field_id = f.id
    ORDER BY posted_date desc
    """

    # Simplified parameter handling
    # Just one embedding parameter for cosine similarity
    
    # Add filter params for the WHERE clause
    sql_params.extend(query_params)

    # Add limit and offset
    sql_params.append(limit)
    sql_params.append(offset)

    # Log parameter structure for debugging
    logger.info(
        "DB_UTILS: Simplified parameter structure: {embedding_count} embeddings, {where_params_count} WHERE params, {total_params} total params, country filter: {country_filter}",
        embedding_count=0,
        where_params_count=len(query_params),
        total_params=len(sql_params),
        country_filter=[p for p in query_params if isinstance(p, str)],
    )

    # Log query for debugging
    logger.info(
        "DB_UTILS: Executing vector similarity query: {param_count} parameters, {where_clause_count} WHERE clauses, {query_size} characters",
        param_count=len(sql_params),
        where_clause_count=len(where_clauses),
        has_filter=bool(where_clauses),
        query_size=len(query)
    )

    # Detailed parameter breakdown for debugging
    logger.info(
        "DB_UTILS: Parameter structure analysis, where clauses: {where_clauses}, query params: {query_params}, sql params count: {sql_params_count}, first few params: {first_few_params}",
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
            f"Query results fetched: {len(results)} results\nQuery time: {query_time:.6f}s\nFetch time: {fetch_time:.6f}s\nTotal time: {time.time() - start_time:.6f}s"
        )
        return results
    
    except Exception as e:
        logger.error(
            "Error executing simple query",
            error=str(e),
            error_type=type(e).__name__,
            where_clauses=where_clauses,
            param_count=len(sql_params),
            elapsed_time=f"{time.time() - start_time:.6f}s",
        )
        raise
    

@async_sql_query_timer("vector_similarity_query")
async def execute_vector_similarity_query(
    cursor: psycopg.AsyncCursor,
    cv_embedding: List[float],
    many_to_many_filters: List[ManyToManyFilter],
    where_clauses: List[str],
    query_params: List[Any],
    limit: int = 25,
    offset: int = 0,
    blacklisted_job_ids: Optional[List[int]] = None,
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
        applied_job_ids: Optional list of job IDs to exclude
        offset: Number of results to skip

    Returns:
        List of matched job results
    """
    start_time = time.time()

    # Build WHERE clause components
    all_where_clauses = []
    # Add clauses generated by query_builder
    if where_clauses:
        all_where_clauses.extend(where_clauses)

    # Add blacklisted jobs filter if provided
    if blacklisted_job_ids:
        # Ensure it's not an empty list before adding the clause
        if blacklisted_job_ids:
            all_where_clauses.append("j.id <> ALL(%s)") # Use ANY/ALL for list parameter
            logger.info(f"Filtering out {len(blacklisted_job_ids)} applied job IDs.")
        else:
            logger.info("Applied job IDs list is empty, skipping filter.")


    # Construct the final WHERE string
    where_sql = ""
    if all_where_clauses:
        where_sql = "WHERE " + " AND ".join(all_where_clauses) # e.g., "WHERE embedding IS NOT NULL AND co.country_name = %s AND j.experience = %s AND j.id NOT IN %s"

    query = "WITH\n"
    sql_params = []

    if many_to_many_filters is not None and len(many_to_many_filters) > 0:
        relationships = ", ".join([mtm.relationship for mtm in many_to_many_filters])
        query += f"""
        "Jobs" AS (
            SELECT selected.*
            FROM "Jobs" as selected
            WHERE EXISTS (
                SELECT 1 FROM {relationships}
                WHERE """
        query += "AND ".join([mtm.where_clause for mtm in many_to_many_filters])
        sql_params += [param for mtm in many_to_many_filters for param in mtm.params]
        query += """
            )
        ),
        """

    # Define the query using the constructed where_sql
    query += f"""
    "JobMatches" AS (
        SELECT
            j.id AS id,
            j.title AS title,
            j.description AS description,
            j.workplace_type AS workplace_type,
            j.short_description AS short_description,
            j.experience AS experience,
            j.skills_required AS skills_required,
            j.posted_date AS posted_date,
            j.job_state AS job_state,
            j.apply_link AS apply_link,
            co.country_name AS country,
            l.city AS city,
            c.company_name AS company_name,
            c.logo AS company_logo,
            j.portal AS portal,
            --no use operation or function otherwise not use index, problem of performance
            embedding <=> %s::vector AS score
        FROM "Jobs" AS j
        LEFT JOIN "Companies" c ON j.company_id = c.company_id
        LEFT JOIN "Locations" l ON j.location_id = l.location_id
        LEFT JOIN "Countries" co ON l.country = co.country_id
        {where_sql}
        ORDER BY score -- non use desc or function otherwise not use index, problem of performance
        LIMIT %s OFFSET %s
    )

    SELECT jm.*, f.root_field, f.sub_field
    FROM "JobMatches" as jm 
    LEFT JOIN "FieldJobs" as fj ON jm.id = fj.job_id
    LEFT JOIN "Fields" as f ON fj.field_id = f.id
    ORDER BY score
    """

    # Simplified parameter handling
    # Just one embedding parameter for cosine similarity
    
    sql_params.append(cv_embedding)

    # Add filter params for the WHERE clause
    sql_params.extend(query_params)

    # Add applied job IDs list if it exists and is not empty
    if blacklisted_job_ids: # Check original list, not the tuple
        sql_params.append(blacklisted_job_ids) # Append the list directly

    # Add limit and offset
    sql_params.append(limit)
    sql_params.append(offset)

    # Log parameter structure for debugging
    logger.info(
        "DB_UTILS: Simplified parameter structure: {embedding_count} embeddings, {where_params_count} WHERE params, {total_params} total params, country filter: {country_filter}",
        embedding_count=1,
        where_params_count=len(query_params),
        total_params=len(sql_params),
        country_filter=[p for p in query_params if isinstance(p, str)],
    )

    # Log query for debugging
    logger.info(
        "DB_UTILS: Executing vector similarity query: {param_count} parameters, {where_clause_count} WHERE clauses, {embedding_length} embedding length, {query_size} characters",
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
        "DB_UTILS: Parameter structure analysis, where clauses: {where_clauses}, query params: {query_params}, sql params count: {sql_params_count}, first few params: {first_few_params}",
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
            f"Query results fetched: {len(results)} results\nQuery time: {query_time:.6f}s\nFetch time: {fetch_time:.6f}s\nTotal time: {time.time() - start_time:.6f}s"
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



async def close_all_connection_pools():
    """
    Close all connection pools.
    
    This function is particularly important for test cleanup to prevent
    connection pool exhaustion between tests.
    """
    logger.debug("Closing all connection pools")
    start_time = time.time()

    try:
        async with _pool_lock:
            for pool_name, pool in _connection_pools.items():
                logger.info("Closing connection pool", pool_name=pool_name)
                try:
                    # Check if the pool is still open before closing
                    if not pool.closed:
                        # Close with a shorter timeout for tests
                        await asyncio.wait_for(pool.close(), timeout=3.0)
                    else:
                        logger.debug(f"Pool {pool_name} already closed")
                except asyncio.TimeoutError:
                    logger.warning(f"Timeout while closing pool {pool_name}, forcing close")
                    # We can't do much more if close times out
                except Exception as e:
                    logger.warning(f"Error closing pool {pool_name}: {str(e)}")
                    # Continue to close other pools even if one fails

            # Clear all pools
            _connection_pools.clear()
            logger.debug(
                f"All connection pools closed in {time.time() - start_time:.6f}s"
            )
    except Exception as e:
        logger.exception(f"Error closing connection pools: {str(e)}")
        # Don't raise here - best effort cleanup for tests
