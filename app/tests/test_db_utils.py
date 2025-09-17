import pytest
import psycopg
from unittest.mock import AsyncMock, patch, ANY

from app.utils.db_utils import execute_vector_similarity_query, close_all_connection_pools

# Define the expected vector dimension used in db_utils
EXPECTED_DIMENSION = 1024

@pytest.fixture(autouse=True)
async def cleanup_pools():
    """Ensure connection pools are closed after each test."""
    yield
    await close_all_connection_pools()

@pytest.mark.asyncio
async def test_execute_vector_similarity_query_with_applied_jobs():
    """
    Test execute_vector_similarity_query with applied_job_ids filtering.
    Ensures the query uses <> ALL(%s) and passes the list parameter correctly.
    """
    mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
    mock_cursor.fetchall = AsyncMock(return_value=[{"id": 2, "score": 0.9}]) # Mock fetch result

    cv_embedding = [0.1] * EXPECTED_DIMENSION # Correct dimension
    where_clauses = ["c.company_name = %s"]
    query_params = ["TestCorp"]
    limit = 10
    offset = 0
    applied_job_ids = [1, 3, 5] # List of IDs to exclude

    # Call the function under test
    results = await execute_vector_similarity_query(
        cursor=mock_cursor,
        cv_embedding=cv_embedding,
        many_to_many_filters=[],
        where_clauses=where_clauses,
        query_params=query_params,
        limit=limit,
        offset=offset,
        blacklisted_job_ids=applied_job_ids,
        user_id=123
    )

    # Assertions
    assert results == [{"id": 2, "score": 0.9}] # Check if mock results are returned

    # Check the calls to cursor.execute
    execute_calls = mock_cursor.execute.call_args_list
    assert len(execute_calls) == 4 # SET TRANSACTION, SET LOCAL, main query

    # Verify the main query call
    main_query_call = execute_calls[-1]
    query_string = main_query_call.args[0]
    params = main_query_call.args[1]

    # Check if the correct WHERE clause for applied jobs is present
    assert "j.id <> ALL(%s)" in query_string
    assert "j.id NOT IN %s" not in query_string # Ensure old clause is gone
    assert "WHERE c.company_name = %s AND j.id <> ALL(%s)" in query_string # Check combined clause

    # Check the parameters passed to execute
    # is_app=True adds user_id as last param
    assert len(params) == 6
    # expected order: [embedding, <filter(s)>, <applied_ids?>, limit, offset, user_id]
    assert params[0] == cv_embedding
    assert params[-3:-1] == [limit, offset]
    assert params[-1] == 123

@pytest.mark.asyncio
async def test_execute_vector_similarity_query_without_applied_jobs():
    """
    Test execute_vector_similarity_query without applied_job_ids.
    Ensures the query is constructed correctly when no filtering is needed.
    """
    mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
    mock_cursor.fetchall = AsyncMock(return_value=[{"id": 4, "score": 0.8}])

    cv_embedding = [0.2] * EXPECTED_DIMENSION
    where_clauses = ["j.experience = %s"]
    query_params = ["Senior"]
    limit = 5
    offset = 0
    applied_job_ids = None # No applied jobs

    results = await execute_vector_similarity_query(
        cursor=mock_cursor,
        cv_embedding=cv_embedding,
        many_to_many_filters=[],
        where_clauses=where_clauses,
        query_params=query_params,
        limit=limit,
        offset=offset,
        blacklisted_job_ids=applied_job_ids,
        user_id=123
    )

    assert results == [{"id": 4, "score": 0.8}]

    execute_calls = mock_cursor.execute.call_args_list
    assert len(execute_calls) == 4

    main_query_call = execute_calls[-1]
    query_string = main_query_call.args[0]
    params = main_query_call.args[1]

    # Check that the applied jobs clause is NOT present
    assert "j.id <> ALL(%s)" not in query_string
    assert "WHERE j.experience = %s" in query_string # Only the experience filter

    # Expected params: [embedding, experience_params, limit, offset]
    assert len(params) == 5
    assert params[0] == cv_embedding
    assert params[-1] == 123
    assert params[-3:-1] == [limit, offset]

    mock_cursor.fetchall.assert_called_once()

@pytest.mark.asyncio
async def test_execute_vector_similarity_query_with_empty_applied_jobs():
    """
    Test execute_vector_similarity_query with an empty applied_job_ids list.
    Ensures the query is constructed correctly and no filter is added.
    """
    mock_cursor = AsyncMock(spec=psycopg.AsyncCursor)
    mock_cursor.fetchall = AsyncMock(return_value=[{"id": 5, "score": 0.7}])

    cv_embedding = [0.3] * EXPECTED_DIMENSION
    where_clauses = ["co.country_name = %s"]
    query_params = ["Germany"]
    limit = 15
    offset = 5
    applied_job_ids = [] # Empty list

    results = await execute_vector_similarity_query(
        cursor=mock_cursor,
        cv_embedding=cv_embedding,
        many_to_many_filters=[],
        where_clauses=where_clauses,
        query_params=query_params,
        limit=limit,
        offset=offset,
        blacklisted_job_ids=applied_job_ids,
        user_id=123
    )

    assert results == [{"id": 5, "score": 0.7}]

    execute_calls = mock_cursor.execute.call_args_list
    assert len(execute_calls) == 4

    main_query_call = execute_calls[-1]
    query_string = main_query_call.args[0]
    params = main_query_call.args[1]

    # Check that the applied jobs clause is NOT present
    assert "j.id <> ALL(%s)" not in query_string
    assert "WHERE co.country_name = %s" in query_string # Only the country filter

    # Expected params: [embedding, country_param, limit, offset]
    assert len(params) == 5
    assert params[0] == cv_embedding
    assert params[-1] == 123
    assert params[-3:-1] == [limit, offset]

    mock_cursor.fetchall.assert_called_once()