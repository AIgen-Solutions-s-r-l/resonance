import random
import pytest
import asyncio
import builtins
from unittest.mock import AsyncMock, MagicMock, patch
from app.libs.job_matcher_optimized import OptimizedJobMatcher
from app.libs.job_matcher.models import JobMatch
from app.utils.db_utils import close_all_connection_pools

# Create a mock Row that supports both dict and list access
class MockRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


@pytest.fixture
def job_matcher():
    """Return a new instance of the optimized matcher."""
    return OptimizedJobMatcher()


@pytest.mark.asyncio
@patch('app.libs.job_matcher.similarity_searcher.SimilaritySearcher._execute_fallback_query')
@patch('app.libs.job_matcher.vector_matcher.get_filtered_job_count')
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_get_top_jobs_by_vector_similarity_single_result(
    mock_get_db_cursor, mock_get_filtered_job_count, mock_execute_fallback, job_matcher
):
    # Set up mocks
    mock_cursor = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_cursor
    mock_context.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_context
    
    mock_get_filtered_job_count.return_value = 1  # This will trigger fallback query
    
    # Create a JobMatch instance, not just a dictionary
    mock_result = JobMatch(
        id="1",
        title="Software Engineer",
        description="Job description",
        workplace_type="office",
        short_description="short desc",
        field="IT",
        experience="3 years",
        skills_required=["Python", "Django"],
        country="USA",
        city="New York",
        company_name="TechCorp",
        score=1.0
    )
    
    mock_execute_fallback.return_value = [mock_result]
    
    mock_embedding = [0.1] * 1024  # Create a properly sized embedding vector
    job_matches = await job_matcher.get_top_jobs_by_vector_similarity(
        mock_embedding
    )
    
    assert len(job_matches) == 1
    assert job_matches[0].title == "Software Engineer"
    assert job_matches[0].score == 1.0


@pytest.mark.asyncio
@patch('app.libs.job_matcher.similarity_searcher.execute_vector_similarity_query')
@patch('app.libs.job_matcher.vector_matcher.get_filtered_job_count')
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_get_top_jobs_by_vector_similarity_multiple_results(
    mock_get_db_cursor, mock_get_filtered_job_count, mock_execute_query, job_matcher
):
    # Set up mocks
    mock_cursor = AsyncMock()
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_cursor
    mock_context.__aexit__.return_value = None
    mock_get_db_cursor.return_value = mock_context
    
    # Create mock results using MockRow
    mock_results = [
        MockRow({
            'title': f"Software Engineer {i}",
            'description': f"Job description {i}",
            'id': f"{i}",
            'workplace_type': "office",
            'short_description': "short desc",
            'field': "IT",
            'experience': "3 years",
            'skills_required': "Python, Django",
            'country': "USA",
            'city': "New York",
            'company_name': "TechCorp",
            'score': 1.0
        }) for i in range(20)
    ]
    
    mock_get_filtered_job_count.return_value = len(mock_results)  # > 5, so uses regular query
    mock_execute_query.return_value = mock_results
    
    mock_embedding = [0.1] * 1024  # Create a properly sized embedding vector
    job_matches = await job_matcher.get_top_jobs_by_vector_similarity(
        mock_embedding
    )
    
    assert len(job_matches) == len(mock_results)
    assert job_matches[0].title == "Software Engineer 0"
    assert (
        job_matches[len(job_matches) - 1].title
        == f"Software Engineer {len(job_matches) - 1}"
    )


@pytest.mark.asyncio
async def test_save_matches(monkeypatch, tmp_path, job_matcher):
    mock_results = {"jobs": [{"id": "1", "title": "Software Engineer"}]}
    resume_id = random.randint(0, 5000)
    
    real_open = builtins.open
    
    def mock_open(filename, mode="r", *args, **kwargs):
        return real_open(tmp_path / filename, mode, *args, **kwargs)
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    await job_matcher.save_matches(mock_results, resume_id, False)
    
    file_path = tmp_path / f"job_matches_{resume_id}.json"
    
    assert file_path.exists(), f"Expected file {file_path} was not created!"


@pytest.mark.asyncio
async def test_save_matches_also_on_mongo(monkeypatch, tmp_path, job_matcher):
    mock_results = {"jobs": [{"id": "1", "title": "Software Engineer"}]}
    resume_id = random.randint(0, 5000)
    
    mock_collection = MagicMock()
    mock_collection.insert_one = AsyncMock()
    
    real_open = builtins.open
    
    def mock_open(filename, mode="r", *args, **kwargs):
        return real_open(tmp_path / filename, mode, *args, **kwargs)
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    monkeypatch.setattr(
        "app.core.mongodb.database.get_collection", lambda _: mock_collection
    )
    
    await job_matcher.save_matches(mock_results, resume_id, True)
    
    file_path = tmp_path / f"job_matches_{resume_id}.json"
    
    assert file_path.exists(), f"Expected file {file_path} was not created!"
    mock_collection.insert_one.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
async def test_process_job_without_embeddings(
    mock_generate_key, mock_get_cached, job_matcher
):
    resume = {"user_id": "123", "experience": "Python Developer"}
    
    # Setup mocks
    mock_generate_key.return_value = "test_key"
    mock_get_cached.return_value = None
    
    result = await job_matcher.process_job(resume)
    
    assert "jobs" in result
    assert len(result["jobs"]) == 0


@pytest.mark.asyncio
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs_by_vector_similarity')
async def test_process_job_success(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached, job_matcher, monkeypatch
):
    resume = {
        "user_id": "123",
        "experience": "Python Developer",
        "vector": [0.1] * 1024,  # Create a properly sized embedding vector
    }
    
    # Create mock results for the get_top_jobs_by_vector_similarity method
    mock_results = [
        JobMatch(
            id=f"{i}",
            title=f"Software Engineer {i}",
            description=f"Job description {i}",
            workplace_type="office",
            short_description="short desc",
            field="IT",
            experience="3 years",
            skills_required=["Python", "Django"],
            country="USA",
            city="New York",
            company_name="TechCorp",
            company_logo=None,
            portal="test_portal",
            score=1.0,
            posted_date=None,
            job_state="active",
            apply_link="https://example.com",
            location=None
        ) for i in range(20)
    ]
    
    # Setup mocks
    mock_generate_key.return_value = "test_key"
    mock_get_cached.return_value = None
    mock_get_top_jobs.return_value = mock_results
    # Create a proper async context manager mock for db_cursor
    class MockDBCursor:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, *args):
            pass
    
    # Apply the mock to prevent actual database connections
    monkeypatch.setattr("app.utils.db_utils.get_db_cursor", lambda: MockDBCursor())
    
    try:
        result = await job_matcher.process_job(resume)
        
        assert isinstance(result, dict)
        assert "jobs" in result.keys()
        assert len(result["jobs"]) == len(mock_results)
        assert result["jobs"][0]["title"] == "Software Engineer 0"
        
        # Verify cache functions were called
        # generate_key is called twice - once to check cache, once to store result
        assert mock_generate_key.await_count == 2
        mock_get_cached.assert_awaited_once()
        mock_store_cached.assert_awaited_once()
        mock_get_top_jobs.assert_awaited_once()
    finally:
        # Explicitly clean up connection pools to prevent leaks
        await close_all_connection_pools()
    mock_get_top_jobs.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
async def test_process_job_with_cache(
    mock_generate_key, mock_get_cached, job_matcher
):
    resume = {
        "user_id": "123",
        "experience": "Python Developer",
        "vector": [0.1] * 1024,  # Create a properly sized embedding vector
        "_id": "test_resume_id"
    }
    
    cached_results = {
        "jobs": [
            {
                "id": "99", 
                "title": "Cached Job",
                "description": "This is from cache"
            }
        ]
    }
    
    # Setup mocks
    mock_generate_key.return_value = "test_key"
    mock_get_cached.return_value = cached_results
    
    result = await job_matcher.process_job(resume)
    
    assert isinstance(result, dict)
    assert "jobs" in result.keys()
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["title"] == "Cached Job"
    
    # Verify that cache functions were called correctly
    mock_generate_key.assert_awaited_once()
    mock_get_cached.assert_awaited_once_with("test_key")
