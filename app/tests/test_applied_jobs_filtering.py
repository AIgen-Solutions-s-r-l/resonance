"""
Tests for the applied jobs filtering functionality.

This module contains tests to ensure that jobs a user has already applied to
are properly filtered out from job recommendations.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.utils.db_utils import close_all_connection_pools
import json

from app.libs.job_matcher.matcher import JobMatcher
from app.schemas.location import LocationFilter
from app.services.applied_jobs_service import applied_jobs_service # Import the instance
from app.libs.job_matcher.models import JobMatch


@pytest.mark.asyncio
async def test_filter_applied_jobs_from_search_results(monkeypatch):
    """Test that applied jobs are filtered out from vector search results."""
    # Setup test data - mocked job matches (use integer IDs)
    # These represent the results *after* filtering would have happened in the DB
    mock_filtered_job_matches = [
        JobMatch(id=2, title="Data Scientist", score=0.90),
        JobMatch(id=4, title="UX Designer", score=0.80),
    ]
    user_id_to_test = 123
    
    # Mock applied jobs - user has already applied to job1 and job3
    # Mock applied jobs (use integer IDs) - user has applied to job 1 and 3
    mock_applied_job_ids = [1, 3]
    
    # Create a test resume
    test_resume = {
        "_id": "test-resume-id",
        "user_id": user_id_to_test,
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5]  # Mock vector
    }
    
    # Mock dependencies
    # Patch the instance method directly
    with patch.object(applied_jobs_service, "get_applied_jobs", new_callable=AsyncMock) as mock_get_applied_jobs:
        mock_get_applied_jobs.return_value = mock_applied_job_ids

        with patch("app.utils.db_utils.get_rejected_jobs", new_callable=AsyncMock) as mock_get_rejected:

            mock_get_rejected.return_value = []
            # Mock the vector matcher to return the *already filtered* results
            with patch("app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs",
                    new_callable=AsyncMock) as mock_get_jobs:
                mock_get_jobs.return_value = mock_filtered_job_matches
                
                with patch("app.libs.job_matcher.cache.cache.get", 
                        new_callable=AsyncMock) as mock_cache_get:
                    mock_cache_get.return_value = None  # Force a cache miss
                    
                    with patch("app.libs.job_matcher.cache.cache.set", 
                            new_callable=AsyncMock) as mock_cache_set:
                        with patch("app.libs.job_matcher.cache.cache.generate_key", 
                                new_callable=AsyncMock) as mock_generate_key:
                            mock_generate_key.return_value = "test-cache-key"
                            
                            # Create a proper async context manager mock for db_cursor
                            class MockDBCursor:
                                async def __aenter__(self):
                                    return AsyncMock()
                                async def __aexit__(self, *args):
                                    pass
                            
                            # Apply the mock to prevent actual database connections
                            monkeypatch.setattr("app.utils.db_utils.get_db_cursor", lambda: MockDBCursor())
                            monkeypatch.setattr("app.libs.job_matcher.matcher.get_db_cursor", lambda: MockDBCursor())
                            
                            try:
                                # Initialize matcher and process job
                                matcher = JobMatcher()
                                result = await matcher.process_job(
                                    test_resume,
                                    use_cache=True
                                )
                                
                                # Verify the result - should contain the pre-filtered jobs from the mock
                                assert len(result["jobs"]) == 2, "Should return the 2 non-applied jobs"
                                job_ids = [job["id"] for job in result["jobs"]]
                                assert 2 in job_ids, "Non-applied job 2 should be present"
                                assert 4 in job_ids, "Non-applied job 4 should be present"
                                
                                # Verify that get_applied_job_ids was called with the correct user_id
                                mock_get_applied_jobs.assert_called_once_with(user_id_to_test)

                                # Verify that get_top_jobs was called with applied_job_ids
                                mock_get_jobs.assert_called_once()
                                call_args, call_kwargs = mock_get_jobs.call_args
                                assert call_kwargs.get("blacklisted_job_ids") == mock_applied_job_ids, \
                                    "get_top_jobs should be called with applied_job_ids"

                                # Verify cache stores the results returned by the mock (already filtered)
                                mock_cache_set.assert_called_once()
                                cache_key_arg, cache_data_arg = mock_cache_set.call_args[0]
                                assert cache_key_arg == "test-cache-key"
                                assert len(cache_data_arg["jobs"]) == 2, "Cache should store the 2 returned jobs"
                                assert cache_data_arg["jobs"][0]["id"] == 2
                                assert cache_data_arg["jobs"][1]["id"] == 4
                            finally:
                                # Ensure database connections are cleaned up
                                await close_all_connection_pools()

                            # Removed test_filter_applied_jobs_from_cache as the filtering logic
                            # in the cache hit path of matcher.py was removed. Filtering now happens
                            # before the DB query / cache check.
                            await close_all_connection_pools()
