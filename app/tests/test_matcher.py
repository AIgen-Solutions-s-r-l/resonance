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


# -----------------------------------------------------------------------------
# 1) process_job should apply experience filter and return jobs
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.query_builder._build_experience_filters')
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.similarity_searcher.SimilaritySearcher._execute_vector_query', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_process_job_with_experience_filter(
    mock_get_db_cursor,
    mock_exec_vector,              # SimilaritySearcher._execute_vector_query
    mock_generate_key,
    mock_get_cached,
    mock_store_cached,
    mock_build_experience_filters,
    mock_get_cooled_jobs,
    mock_get_applied_jobs,
    job_matcher,
    monkeypatch
):
    
    monkeypatch.setattr("app.libs.job_matcher.matcher.get_db_cursor",mock_get_db_cursor)
    mock_get_rejected_jobs = AsyncMock()
    monkeypatch.setattr("app.utils.db_utils.get_rejected_jobs", mock_get_rejected_jobs)
    mock_get_rejected_jobs.return_value = []

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

    # Return JobMatch objects so .to_dict() works inside process_job
    mock_exec_vector.return_value = [
        JobMatch(
            id=1,
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
            score=1.0,
        )
    ]

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
            is_remote_only=None,
        )
        mock_build_experience_filters.assert_called_once()
    finally:
        await close_all_connection_pools()


# -----------------------------------------------------------------------------
# 2) vector matcher should pass experience filter into query builder
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
@patch('app.libs.job_matcher.vector_matcher.query_builder.build_filter_conditions')
@patch('app.libs.job_matcher.similarity_searcher.SimilaritySearcher._execute_vector_query', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_vector_matcher_with_experience_filter(
    mock_get_db_cursor,
    mock_exec_vector_query,         # SimilaritySearcher._execute_vector_query
    mock_build_filter_conditions,
    job_matcher,
    monkeypatch
):
    mock_cursor = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_cursor
    mock_ctx.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_ctx

    monkeypatch.setattr("app.libs.job_matcher.matcher.get_db_cursor",mock_get_db_cursor)
    mock_get_rejected_jobs = AsyncMock()
    monkeypatch.setattr("app.utils.db_utils.get_rejected_jobs", mock_get_rejected_jobs)
    mock_get_rejected_jobs.return_value = []

    mock_build_filter_conditions.return_value = (
        [], ["embedding IS NOT NULL", "(j.experience = %s)"], ["Mid-level"]
    )

    mock_exec_vector_query.return_value = [
        JobMatch(
            id=1,
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
            score=1.0,
        )
    ]

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


# -----------------------------------------------------------------------------
# 3) integration-ish: matching_service passes args through to vector matcher
# -----------------------------------------------------------------------------
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
    from app.services.matching_service import match_jobs_with_resume

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

    mock_generate_key.return_value = "test_key_with_everything"
    mock_get_cached.return_value = None
    mock_get_applied_jobs.return_value = []
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

    result = await match_jobs_with_resume(
        resume,
        location=[location],
        keywords=keywords,
        experience=experience,
    )

    assert isinstance(result, list) or (isinstance(result, dict) and "jobs" in result)

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


# -----------------------------------------------------------------------------
# 4) cache key should include experience
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.similarity_searcher.SimilaritySearcher._execute_vector_query', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_experience_filter_with_cache(
    mock_get_db_cursor,
    mock_exec_vector,
    mock_generate_key,
    mock_get_cached,
    mock_store_cached,
    mock_get_applied_jobs,
    mock_get_cooled_jobs,
    job_matcher,
    monkeypatch
):
    monkeypatch.setattr("app.libs.job_matcher.matcher.get_db_cursor",mock_get_db_cursor)
    mock_get_rejected_jobs = AsyncMock()
    monkeypatch.setattr("app.utils.db_utils.get_rejected_jobs", mock_get_rejected_jobs)
    mock_get_rejected_jobs.return_value = []

    resume = {"user_id": "123", "vector": [0.1] * 1024, "_id": "test_resume_id"}
    experience_1 = ["Mid-level"]
    experience_2 = ["Entry-level"]

    mock_generate_key.return_value = "key_with_mid"
    mock_get_cached.return_value = None
    mock_get_applied_jobs.return_value = []
    mock_get_cooled_jobs.return_value = []

    mock_exec_vector.return_value = [
        JobMatch(
            id=1,
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
            score=1.0,
        )
    ]

    mock_cursor = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_cursor
    mock_ctx.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_ctx

    try:
        await job_matcher.process_job(resume, experience=experience_1, is_remote_only=None)
        mock_generate_key.assert_called_with(
            "test_resume_id",
            offset=0,
            location=[],
            fields=None,
            keywords=None,
            experience=experience_1,
            is_remote_only=None,
        )

        mock_store_cached.assert_called_once()

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
        is_remote_only=None,
    )
    assert "key_with_entry" != "key_with_mid"


# -----------------------------------------------------------------------------
# 5) cache hit should bypass vector query
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs', new_callable=AsyncMock)
@patch('app.services.applied_jobs_service.AppliedJobsService.get_applied_jobs', new_callable=AsyncMock)
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
@patch('app.libs.job_matcher.similarity_searcher.SimilaritySearcher._execute_vector_query', new_callable=AsyncMock)
async def test_experience_filter_with_cache_hit(
    mock_exec_vector,
    mock_get_db_cursor,
    mock_generate_key,
    mock_get_cached,
    mock_store_cached,
    mock_get_applied_jobs,
    mock_get_cooled_jobs,
    job_matcher,
    monkeypatch
):
    monkeypatch.setattr("app.libs.job_matcher.matcher.get_db_cursor",mock_get_db_cursor)
    mock_get_rejected_jobs = AsyncMock()
    monkeypatch.setattr("app.utils.db_utils.get_rejected_jobs", mock_get_rejected_jobs)
    mock_get_rejected_jobs.return_value = []

    resume = {"user_id": "123", "vector": [0.1] * 1024, "_id": "test_resume_id"}
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
        is_remote_only=None,
    )
    assert result == cached_result
    mock_exec_vector.assert_not_called()
