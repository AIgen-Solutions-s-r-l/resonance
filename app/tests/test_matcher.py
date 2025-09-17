"""
Tests for the experience filter functionality.

This module contains tests specifically for the experience filtering feature in the job matcher.
"""

import pytest
from unittest.mock import AsyncMock, patch
from app.utils.db_utils import close_all_connection_pools

from app.libs.job_matcher_optimized import OptimizedJobMatcher
from app.libs.job_matcher.models import JobMatch
from app.schemas.location import LocationFilter
from app.core.config import settings


@pytest.fixture
def job_matcher():
    """Return a new instance of the optimized matcher."""
    return OptimizedJobMatcher()


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.query_builder._build_experience_filters')
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.utils.db_utils.execute_simple_query', new_callable=AsyncMock)              # ensure embedding-less path is covered
@patch('app.utils.db_utils.execute_vector_similarity_query', new_callable=AsyncMock)  # vector path
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_process_job_with_experience_filter(
    mock_get_db_cursor,        # get_db_cursor
    mock_exec_vec,             # execute_vector_similarity_query
    mock_exec_simple,          # execute_simple_query
    mock_generate_key,         # cache.generate_key
    mock_get_cached,           # cache.get
    mock_store_cached,         # cache.set
    mock_build_experience_filters,
    mock_get_applied_jobs,
    mock_get_cooled_jobs,
    job_matcher,
):
    resume = {"user_id": "123", "vector": [0.1] * 1024, "_id": "test_resume_id"}
    experience = ["Mid-level", "Executive-level"]

    mock_build_experience_filters.return_value = (
        ["(j.experience = %s OR j.experience = %s)"],
        ["Mid-level", "Executive-level"],
    )
    mock_generate_key.return_value = "test_key_with_experience"
    mock_get_cached.return_value = None
    mock_get_applied_jobs.return_value = []
    mock_get_cooled_jobs.return_value = []

    rows = [{
        "id": 1,
        "title": "Senior Software Engineer",
        "description": "Job description",
        "workplace_type": "office",
        "short_description": "short desc",
        "field": "IT",
        "experience": "Mid-level",
        "skills_required": "Python, Django",
        "country": "USA",
        "city": "New York",
        "company_name": "TechCorp",
        "score": 1.0,
    }]
    mock_exec_vec.return_value = rows
    mock_exec_simple.return_value = rows

    # async cursor context
    mock_cursor = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_cursor
    mock_ctx.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_ctx

    try:
        result = await job_matcher.process_job(
            resume,
            experience=experience,
            is_remote_only=None,
        )
        assert isinstance(result, dict)
        assert "jobs" in result
        assert len(result["jobs"]) == 1
        assert result["jobs"][0]["title"] == "Senior Software Engineer"

        mock_generate_key.assert_called_with(
            "test_resume_id",
            offset=0,
            location=[],
            fields=None,
            keywords=None,
            experience=experience,
            applied_job_ids=[],
            cooled_job_ids=[],
            is_remote_only=None,
        )
        mock_build_experience_filters.assert_called_once()
    finally:
        await close_all_connection_pools()


@pytest.mark.asyncio
@patch('app.libs.job_matcher.vector_matcher.query_builder.build_filter_conditions')
@patch('app.libs.job_matcher.similarity_searcher.SimilaritySearcher._execute_vector_query', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_vector_matcher_with_experience_filter(
    mock_get_db_cursor,
    mock_exec_vector_query,         # SimilaritySearcher._execute_vector_query
    mock_build_filter_conditions,
    job_matcher,
):
    mock_cursor = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_cursor
    mock_ctx.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_ctx

    mock_build_filter_conditions.return_value = (
        [], ["embedding IS NOT NULL", "(j.experience = %s)"], ["Mid-level"]
    )

    mock_exec_vector_query.return_value = [{
        "id": 1,
        "title": "Mid Level Developer",
        "description": "Job description",
        "workplace_type": "office",
        "short_description": "short desc",
        "field": "IT",
        "experience": "Mid-level",
        "skills_required": "Python",
        "country": "USA",
        "city": "New York",
        "company_name": "TechCorp",
        "score": 1.0,
    }]

    await job_matcher.get_top_jobs(
        "123",                # user_id first
        [0.1] * 1024,         # embedding second
        experience=["Mid-level"],
        fields=[],
        location=None,
        keywords=None,
        offset=0,
        limit=5,
    )

    mock_build_filter_conditions.assert_called_once()
    args, kwargs = mock_build_filter_conditions.call_args
    assert kwargs.get("experience") == ["Mid-level"]
    assert kwargs.get("is_remote_only") is None

    mock_exec_vector_query.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.VectorMatcher.get_top_jobs', new_callable=AsyncMock)
async def test_match_jobs_with_resume_integration(
    mock_get_top_jobs,
    mock_generate_key,
    mock_get_cached,
    mock_store_cached,
    mock_get_applied_jobs,
    mock_get_cooled_jobs,
):
    """Integration test for match_jobs_with_resume with experience parameter."""
    from app.services.matching_service import match_jobs_with_resume

    # Set up test data
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,
        "_id": "test_resume_id",
    }

    location = LocationFilter(
        country="USA",
        city="New York",
        radius_km=20.0,
        latitude=43.0,
        longitude=-75.0,
    )

    keywords = ["Python", "Django"]
    experience = ["Entry-level", "Mid-level"]

    # Mocks
    mock_generate_key.return_value = "test_key_with_everything"
    mock_get_cached.return_value = None
    mock_get_applied_jobs.return_value = []  # prevent real Mongo call
    mock_get_cooled_jobs.return_value = []
    mock_get_top_jobs.return_value = [
        JobMatch(
            id=1,
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
            score=1.0,
        )
    ]

    # Execute
    result = await match_jobs_with_resume(
        resume,
        location=[location],
        keywords=keywords,
        experience=experience,
    )

    # Verify results
    assert isinstance(result, list) or (isinstance(result, dict) and "jobs" in result)

    # get_top_jobs was called with the right args
    mock_get_top_jobs.assert_called()
    args, kwargs = mock_get_top_jobs.call_args_list[0]
    if len(args) == 2:
        user_id_arg, embedding_arg = args
    else:
        _, user_id_arg, embedding_arg = args[:3]

    assert user_id_arg == resume["user_id"]
    assert embedding_arg == resume["vector"]
    assert kwargs["location"][0] == location
    assert kwargs["keywords"] == keywords
    assert kwargs["offset"] == 0
    assert kwargs["limit"] == settings.CACHE_SIZE
    assert kwargs["experience"] == experience
    assert "is_remote_only" in kwargs
    assert kwargs["is_remote_only"] is None


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.utils.db_utils.execute_vector_similarity_query', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_experience_filter_with_cache(
    mock_get_db_cursor,
    mock_exec_sim,
    mock_generate_key,
    mock_get_cached,
    mock_store_cached,
    mock_get_applied_jobs,
    mock_get_cooled_jobs,
    job_matcher,
):
    """Test that different experience filters use different cache keys."""
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,
        "_id": "test_resume_id",
    }

    experience_1 = ["Mid-level"]
    experience_2 = ["Entry-level"]

    mock_generate_key.return_value = "key_with_mid"
    mock_get_cached.return_value = None
    mock_get_applied_jobs.return_value = []
    mock_get_cooled_jobs.return_value = []

    mock_exec_sim.return_value = [
        {
            "id": 1,
            "title": "Mid Level Developer",
            "description": "Job description",
            "workplace_type": "office",
            "short_description": "short desc",
            "field": "IT",
            "experience": "Mid-level",
            "skills_required": "Python",
            "country": "USA",
            "city": "New York",
            "company_name": "TechCorp",
            "score": 1.0,
        }
    ]

    mock_cursor = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_cursor
    mock_ctx.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_ctx

    try:
        # First call with experience_1
        await job_matcher.process_job(resume, experience=experience_1, is_remote_only=None)

        mock_generate_key.assert_called_with(
            "test_resume_id",
            offset=0,
            location=[],
            fields=None,
            keywords=None,
            experience=experience_1,
            applied_job_ids=[],
            cooled_job_ids=[],
            is_remote_only=None,
        )

        mock_store_cached.assert_called_once()
        args, _ = mock_store_cached.call_args
        cached_key_1, cached_result_1 = args

        # Second call with different experience filter
        mock_generate_key.return_value = "key_with_entry"
        mock_generate_key.reset_mock()
        mock_get_cached.reset_mock()
        mock_store_cached.reset_mock()

        await job_matcher.process_job(resume, experience=experience_2, is_remote_only=None)
    finally:
        await close_all_connection_pools()

    mock_generate_key.assert_called_with(
        "test_resume_id",
        offset=0,
        location=[],
        keywords=None,
        fields=None,
        experience=experience_2,
        applied_job_ids=[],
        cooled_job_ids=[],
        is_remote_only=None,
    )

    assert "key_with_entry" != "key_with_mid"


@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
@patch('app.utils.db_utils.execute_vector_similarity_query', new_callable=AsyncMock)
async def test_experience_filter_with_cache_hit(
    mock_exec_sim,
    mock_get_db_cursor,
    mock_generate_key,
    mock_get_cached,
    mock_store_cached,
    mock_get_applied_jobs,
    mock_get_cooled_jobs,
    job_matcher,
):
    """Test that cached results are correctly retrieved with experience filter."""
    resume = {
        "user_id": "123",
        "vector": [0.1] * 1024,
        "_id": "test_resume_id",
    }

    experience = ["Mid-level"]

    mock_generate_key.return_value = "key_with_mid_experience"
    mock_get_applied_jobs.return_value = []
    mock_get_cooled_jobs.return_value = []

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
                "score": 1.0,
            }
        ]
    }

    mock_get_cached.return_value = cached_result

    result = await job_matcher.process_job(resume, experience=experience, is_remote_only=None)

    mock_generate_key.assert_called_with(
        "test_resume_id",
        offset=0,
        location=[],
        keywords=None,
        fields=None,
        experience=experience,
        applied_job_ids=[],
        cooled_job_ids=[],
        is_remote_only=None,
    )

    assert result == cached_result

    # Ensure no DB vector call happened due to cache hit
    mock_exec_sim.assert_not_called()
