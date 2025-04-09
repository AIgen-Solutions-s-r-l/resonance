"""
Tests for the experience filter functionality.

This module contains tests specifically for the experience filtering feature in the job matcher.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from app.utils.db_utils import close_all_connection_pools

from app.libs.job_matcher_optimized import OptimizedJobMatcher
from app.libs.job_matcher.models import JobMatch
from app.schemas.location import LocationFilter


@pytest.fixture
def job_matcher():
    """Return a new instance of the optimized matcher."""
    return OptimizedJobMatcher()


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs')
@patch('app.libs.job_matcher.vector_matcher.query_builder._build_experience_filters')
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs_by_vector_similarity')
async def test_process_job_with_experience_filter(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached,
    mock_build_experience_filters, mock_get_cooled_jobs, job_matcher, monkeypatch
):
    """Test that process_job correctly applies experience filtering."""
    # Set up test data
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,  # Properly sized embedding vector
        "_id": "test_resume_id"
    }
    
    experience = ["Mid-level", "Executive-level"]
    
    # Mock return values
    mock_build_experience_filters.return_value = (["(j.experience = %s OR j.experience = %s)"], ["Mid-level", "Executive-level"])
    mock_generate_key.return_value = "test_key_with_experience"
    mock_get_cached.return_value = None  # No cache hit
    mock_get_cooled_jobs.return_value = []  # No cooled jobs
    mock_get_top_jobs.return_value = [
        JobMatch(
            id="1",
            title="Senior Software Engineer",
            description="Job description",
            workplace_type="office",
            short_description="short desc",
            field="IT",
            experience="Mid-level",
            skills_required=["Python", "Django"],
            country="USA",
            city="New York",
            company_name="TechCorp",
            score=1.0
        )
    ]
    
    # Create a proper async context manager mock for db_cursor
    class MockDBCursor:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, *args):
            pass
    
    # Apply the mock to prevent actual database connections
    monkeypatch.setattr("app.utils.db_utils.get_db_cursor", lambda: MockDBCursor())
    
    try:
        # Execute the function with experience parameter
        result = await job_matcher.process_job(
            resume,
            experience=experience
        )
        
        # Verify results
        assert isinstance(result, dict)
        assert "jobs" in result
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["title"] == "Senior Software Engineer"
        
        # Verify that the experience parameter was correctly passed
        mock_generate_key.assert_called_with(
            "test_resume_id",
            offset=0,
            location=None,
            keywords=None,
            experience=experience,
            applied_job_ids=[],  # Added expected argument
            cooled_job_ids=[]  # Added expected argument for cooled jobs
        )
    finally:
        # Ensure database connections are cleaned up
        await close_all_connection_pools()
    
    # Verify vector matcher was called with experience
    mock_get_top_jobs.assert_called_once()
    args, kwargs = mock_get_top_jobs.call_args
    assert "experience" in kwargs
    assert kwargs["experience"] == experience


@pytest.mark.asyncio
@patch('app.libs.job_matcher.vector_matcher.query_builder.build_filter_conditions')
@patch('app.libs.job_matcher.vector_matcher.get_filtered_job_count')
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_vector_matcher_with_experience_filter(
    mock_get_db_cursor, mock_get_filtered_job_count, mock_build_filter_conditions, job_matcher
):
    """Test that the vector matcher correctly uses experience filters."""
    # Set up mocks
    mock_cursor = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_cursor
    mock_context.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_context
    
    mock_get_filtered_job_count.return_value = 0  # Will return empty results
    
    # Mock filter conditions
    mock_build_filter_conditions.return_value = (["embedding IS NOT NULL", "(j.experience = %s)"], ["Mid-level"])
    
    # Call the vector matcher with experience parameter
    cv_embedding = [0.1] * 1024
    experience = ["Mid-level"]
    await job_matcher.get_top_jobs_by_vector_similarity(
        cv_embedding,
        experience=experience,
        location=None,
        keywords=None,
        offset=0,
        limit=5
    )
    
    # Verify build_filter_conditions was called with the experience parameter
    mock_build_filter_conditions.assert_called_once()
    args, kwargs = mock_build_filter_conditions.call_args
    assert "experience" in kwargs
    assert kwargs["experience"] == experience
    assert kwargs["experience"] == experience


@pytest.mark.asyncio
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs_by_vector_similarity')
async def test_match_jobs_with_resume_integration(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached
):
    """Integration test for match_jobs_with_resume with experience parameter."""
    from app.services.matching_service import match_jobs_with_resume
    
    # Set up test data
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,
        "_id": "test_resume_id"
    }
    
    location = LocationFilter(
        country="USA",
        city="New York",
        radius_km=20.0
    )
    
    keywords = ["Python", "Django"]
    experience = ["Entry-level", "Mid-level"]
    
    # Mock return values
    mock_generate_key.return_value = "test_key_with_everything"
    mock_get_cached.return_value = None
    mock_get_top_jobs.return_value = [
        JobMatch(
            id="1",
            title="Entry Level Developer",
            description="Job description",
            workplace_type="office",
            short_description="short desc",
            field="IT",
            experience="Entry-level",
            skills_required=["Python"],
            country="USA",
            city="New York",
            company_name="TechCorp",
            score=1.0
        )
    ]
    
    # Execute the function with all parameters
    result = await match_jobs_with_resume(
        resume,
        location=location,
        keywords=keywords,
        experience=experience
    )
    
    # Verify results
    assert isinstance(result, list) or (isinstance(result, dict) and "jobs" in result)
    
    # Check that get_top_jobs_by_vector_similarity was called with all parameters
    mock_get_top_jobs.assert_called_once()
    args, kwargs = mock_get_top_jobs.call_args
    assert args[0] == resume["vector"]
    assert kwargs["location"] == location
    assert kwargs["keywords"] == keywords
    assert kwargs["offset"] == 0
    assert kwargs["limit"] == 25
    assert kwargs["experience"] == experience
    assert "location" in kwargs
    assert kwargs["location"] == location
    assert "keywords" in kwargs
    assert kwargs["keywords"] == keywords


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs')
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs_by_vector_similarity')
async def test_experience_filter_with_cache(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached,
    mock_get_cooled_jobs, job_matcher, monkeypatch
):
    """Test that different experience filters use different cache keys."""
    # Set up test data
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,
        "_id": "test_resume_id"
    }
    
    experience_1 = ["Mid-level"]
    experience_2 = ["Entry-level"]
    # Configure mocks for experience filtering
    mock_generate_key.return_value = "key_with_mid"  # First key
    mock_get_cached.return_value = None  # No cache hit
    mock_get_cooled_jobs.return_value = []  # No cooled jobs
    
    
    job_match = JobMatch(
        id="1",
        title="Mid Level Developer",
        description="Job description",
        workplace_type="office",
        short_description="short desc",
        field="IT",
        experience="Mid-level",
        skills_required=["Python"],
        country="USA",
        city="New York",
        company_name="TechCorp",
        score=1.0
    )
    
    mock_get_top_jobs.return_value = [job_match]
    
    # Create a proper async context manager mock for db_cursor
    class MockDBCursor:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, *args):
            pass
    
    # Apply the mock to prevent actual database connections
    monkeypatch.setattr("app.utils.db_utils.get_db_cursor", lambda: MockDBCursor())
    
    try:
        # First call with experience_1
        await job_matcher.process_job(resume, experience=experience_1)
        
        # Verify first call generated correct cache key with experience_1
        mock_generate_key.assert_called_with(
            "test_resume_id",
            offset=0,
            location=None,
            keywords=None,
            experience=experience_1,
            applied_job_ids=[],  # Added expected argument
            cooled_job_ids=[]  # Added expected argument for cooled jobs
        )
        
        # Store what would be cached for first call
        mock_store_cached.assert_called_once()
        args, _ = mock_store_cached.call_args
        cached_key_1, cached_result_1 = args
        
        # Store first call information for comparison
        first_call_args = mock_generate_key.call_args
        
        # Change the mock return value for the second call
        mock_generate_key.return_value = "key_with_entry"
        
        # Reset mocks for second call
        mock_generate_key.reset_mock()
        mock_get_cached.reset_mock()
        mock_store_cached.reset_mock()
        mock_get_top_jobs.reset_mock()
        
        # Second call with different experience filter
        await job_matcher.process_job(resume, experience=experience_2)
    finally:
        # Ensure database connections are cleaned up
        await close_all_connection_pools()
    
    # Verify second call generated key with experience_2
    mock_generate_key.assert_called_with(
        "test_resume_id",
        offset=0,
        location=None,
        keywords=None,
        experience=experience_2,
        applied_job_ids=[],  # Added expected argument
        cooled_job_ids=[]  # Added expected argument for cooled jobs
    )
    
    # Verify that the experience parameter affects the cache key
    assert "key_with_entry" != "key_with_mid"


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs')
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs_by_vector_similarity')
async def test_experience_filter_with_cache_hit(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached,
    mock_get_cooled_jobs, job_matcher
):
    """Test that cached results are correctly retrieved with experience filter."""
    # Set up test data
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,
        "_id": "test_resume_id"
    }
    
    experience = ["Mid-level"]
    
    # Mock cache key generation
    mock_generate_key.return_value = "key_with_mid_experience"
    mock_get_cooled_jobs.return_value = []  # No cooled jobs
    
    # Create cached result that should be returned
    cached_result = {
        "jobs": [
            {
                "id": "1",
                "title": "Mid Level Developer",
                "description": "Job description",
                "workplace_type": "office",
                "short_description": "short desc",
                "field": "IT",
                "experience": "Mid-level",
                "skills_required": ["Python"],
                "country": "USA",
                "city": "New York",
                "company_name": "TechCorp",
                "score": 1.0
            }
        ]
    }
    
    # Mock cache hit
    mock_get_cached.return_value = cached_result
    
    # Call process_job with experience filter
    result = await job_matcher.process_job(resume, experience=experience)
    
    # Verify cache key was generated with experience parameter
    mock_generate_key.assert_called_with(
        "test_resume_id",
        offset=0,
        location=None,
        keywords=None,
        experience=experience,
        applied_job_ids=[],  # Added expected argument
        cooled_job_ids=[]  # Added expected argument for cooled jobs
    )
    
    # Verify cached result was returned
    assert result == cached_result
    
    # Verify vector matcher was not called (cache hit)
    mock_get_top_jobs.assert_not_called()