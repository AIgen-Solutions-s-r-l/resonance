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
from app.services.applied_jobs_service import AppliedJobsService
from app.libs.job_matcher.models import JobMatch


@pytest.mark.asyncio
async def test_filter_applied_jobs_from_search_results(monkeypatch):
    """Test that applied jobs are filtered out from vector search results."""
    # Setup test data - mocked job matches
    mock_job_matches = [
        JobMatch(id="job1", title="Software Engineer", score=0.95),
        JobMatch(id="job2", title="Data Scientist", score=0.90),
        JobMatch(id="job3", title="Product Manager", score=0.85),
        JobMatch(id="job4", title="UX Designer", score=0.80),
    ]
    
    # Mock applied jobs - user has already applied to job1 and job3
    mock_applied_jobs = ["job1", "job3"]
    
    # Create a test resume
    test_resume = {
        "_id": "test-resume-id",
        "user_id": 123,
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5]  # Mock vector
    }
    
    # Mock dependencies
    with patch("app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs", 
               new_callable=AsyncMock) as mock_get_applied_jobs:
        mock_get_applied_jobs.return_value = mock_applied_jobs
        
        with patch("app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs_by_vector_similarity", 
                  new_callable=AsyncMock) as mock_get_jobs:
            mock_get_jobs.return_value = mock_job_matches
            
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
                        
                        try:
                            # Initialize matcher and process job
                            matcher = JobMatcher()
                            result = await matcher.process_job(
                                test_resume,
                                use_cache=True
                            )
                            
                            # Verify the result - should only have job2 and job4 (2 jobs)
                            assert len(result["jobs"]) == 2, "Should have filtered out 2 applied jobs"
                            job_ids = [job["id"] for job in result["jobs"]]
                            assert "job1" not in job_ids, "Applied job job1 should be filtered out"
                            assert "job2" in job_ids, "Non-applied job job2 should be present"
                            assert "job3" not in job_ids, "Applied job job3 should be filtered out"
                            assert "job4" in job_ids, "Non-applied job job4 should be present"
                            
                            # Verify that get_applied_jobs was called with the correct user_id
                            mock_get_applied_jobs.assert_called_once_with(123)
                            
                            # Verify that cache was updated with filtered results
                            mock_cache_set.assert_called_once()
                            cache_arg = mock_cache_set.call_args[0][1]  # The second arg is the cache data
                            assert len(cache_arg["jobs"]) == 2, "Cache should store filtered jobs"
                        finally:
                            # Ensure database connections are cleaned up
                            await close_all_connection_pools()


@pytest.mark.asyncio
async def test_filter_applied_jobs_from_cache(monkeypatch):
    """Test that applied jobs are filtered out from cached results."""
    # Mock cache result with 4 jobs
    cached_result = {
        "jobs": [
            {"id": "job1", "title": "Software Engineer", "score": 0.95},
            {"id": "job2", "title": "Data Scientist", "score": 0.90},
            {"id": "job3", "title": "Product Manager", "score": 0.85},
            {"id": "job4", "title": "UX Designer", "score": 0.80},
        ]
    }
    
    # Mock applied jobs - user has already applied to job1 and job3
    mock_applied_jobs = ["job1", "job3"]
    
    # Create a test resume
    test_resume = {
        "_id": "test-resume-id",
        "user_id": 123,
        "vector": [0.1, 0.2, 0.3, 0.4, 0.5]  # Mock vector
    }
    
    # Mock dependencies
    with patch("app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs", 
               new_callable=AsyncMock) as mock_get_applied_jobs:
        mock_get_applied_jobs.return_value = mock_applied_jobs
        
        with patch("app.libs.job_matcher.cache.cache.get", 
                  new_callable=AsyncMock) as mock_cache_get:
            mock_cache_get.return_value = cached_result  # Force a cache hit
            
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
                    
                    try:
                        # Initialize matcher and process job
                        matcher = JobMatcher()
                        result = await matcher.process_job(
                            test_resume,
                            use_cache=True
                        )
                        
                        # Verify the result - should only have job2 and job4 (2 jobs)
                        assert len(result["jobs"]) == 2, "Should have filtered out 2 applied jobs from cache"
                        job_ids = [job["id"] for job in result["jobs"]]
                        assert "job1" not in job_ids, "Applied job job1 should be filtered out"
                        assert "job2" in job_ids, "Non-applied job job2 should be present"
                        assert "job3" not in job_ids, "Applied job job3 should be filtered out"
                        assert "job4" in job_ids, "Non-applied job job4 should be present"
                        
                        # Verify that get_applied_jobs was called with the correct user_id
                        mock_get_applied_jobs.assert_called_once_with(123)
                        
                        # Verify that cache was updated with filtered results
                        mock_cache_set.assert_called_once()
                        cache_arg = mock_cache_set.call_args[0][1]  # The second arg is the cache data
                        assert len(cache_arg["jobs"]) == 2, "Cache should be updated with filtered jobs"
                    finally:
                        # Ensure database connections are cleaned up
                        await close_all_connection_pools()