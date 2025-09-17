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
@patch('app.libs.job_matcher.similarity_searcher.execute_vector_similarity_query', new_callable=AsyncMock)
@patch('app.libs.job_matcher.vector_matcher.get_db_cursor')
async def test_get_top_jobs_multiple_results(
    mock_get_db_cursor, mock_execute_query, job_matcher
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
    
    mock_execute_query.return_value = mock_results
    
    mock_embedding = [0.1] * 1024  # Create a properly sized embedding vector
    job_matches = await job_matcher.get_top_jobs(
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
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs')
async def test_process_job_success(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached, job_matcher, monkeypatch
):
    resume = {
        "user_id": "123",
        "experience": "Python Developer",
        "vector": [0.1] * 1024,  # Create a properly sized embedding vector
    }
    
    # Create mock results for the get_top_jobs method
    mock_results = [
        JobMatch(
            id=i,
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



@pytest.mark.asyncio
@patch('app.services.cooled_jobs_service.cooled_jobs_service.get_cooled_jobs')
@patch('app.libs.job_matcher.matcher.applied_jobs_service.get_applied_jobs')
@patch('app.libs.job_matcher.cache.cache.set')
@patch('app.libs.job_matcher.cache.cache.get')
@patch('app.libs.job_matcher.cache.cache.generate_key')
@patch('app.libs.job_matcher.vector_matcher.vector_matcher.get_top_jobs')
async def test_process_job_cache_handles_different_applied_ids(
    mock_get_top_jobs, mock_generate_key, mock_get_cached, mock_store_cached,
    mock_get_applied_jobs, mock_get_cooled_jobs, job_matcher, monkeypatch
):
    """Verify cache keys differ and cache hits work correctly with different applied_job_ids."""
    resume = {
        "user_id": "user1",
        "experience": "Python Developer",
        "vector": [0.1] * 1024,
        "_id": "resume1"
    }
    base_params = {
        "offset": 0,
        "limit": 10,
        "location": [],
        "keywords": None,
        "experience": None
    }

    # Mock results from vector matcher
    mock_job_matches = [
        JobMatch(id=i, title=f"Job {i}", score=0.9, description="Desc", workplace_type="remote", short_description="Short", field="IT", experience="Mid", skills_required=["Python"], country="UK", city="London", company_name="Test Co")
        for i in range(5)
    ]
    mock_get_top_jobs.return_value = mock_job_matches

    # --- First Call (User 1, applied_ids = [1, 2]) ---
    applied_ids_user1 = [1, 2]
    cache_key_user1 = "key_user1_applied_1_2"
    mock_get_applied_jobs.return_value = applied_ids_user1
    mock_get_cooled_jobs.return_value = []  # No cooled jobs
    mock_generate_key.return_value = cache_key_user1
    mock_get_cached.return_value = None # Cache miss

    # Mock DB for total count (needed if cache miss)
    class MockDBCursor:
        async def __aenter__(self):
            return AsyncMock()
        async def __aexit__(self, *args):
            pass
    monkeypatch.setattr("app.utils.db_utils.get_db_cursor", lambda: MockDBCursor())

    result1 = await job_matcher.process_job(resume, **base_params, use_cache=True, is_remote_only=None) # Add missing param

    # Assertions for first call
    mock_get_applied_jobs.assert_awaited_once_with("user1")
    mock_generate_key.assert_awaited_with(
        resume["_id"],
        offset=base_params.get("offset"),
        location=base_params.get("location"),
        keywords=base_params.get("keywords"),
        fields=base_params.get("fields"),
        experience=base_params.get("experience"),
        applied_job_ids=applied_ids_user1,
        cooled_job_ids=[],
        is_remote_only=None # Add missing param assertion
    )
    mock_get_cached.assert_awaited_once_with(cache_key_user1)
    mock_get_top_jobs.assert_awaited_once() # Called because of cache miss
    mock_store_cached.assert_awaited_once_with(cache_key_user1, result1) # Stored with user1's key
    assert len(result1["jobs"]) == 5

    # --- Reset mocks for second call ---
    mock_get_applied_jobs.reset_mock()
    mock_generate_key.reset_mock()
    mock_get_cached.reset_mock()
    mock_store_cached.reset_mock()
    mock_get_top_jobs.reset_mock()

    # --- Second Call (User 2, applied_ids = [3, 4]) ---
    resume["user_id"] = "user2"
    resume["_id"] = "resume2" # Different resume ID for clarity, though user_id drives applied jobs
    applied_ids_user2 = [3, 4]
    cache_key_user2 = "key_user2_applied_3_4"
    mock_get_applied_jobs.return_value = applied_ids_user2
    mock_get_cooled_jobs.return_value = []  # No cooled jobs
    mock_generate_key.return_value = cache_key_user2
    # Simulate cache miss for this *different* key
    mock_get_cached.return_value = None

    result2 = await job_matcher.process_job(resume, **base_params, use_cache=True, is_remote_only=None) # Add missing param

    # Assertions for second call
    mock_get_applied_jobs.assert_awaited_once_with("user2")
    mock_generate_key.assert_awaited_with(
        resume["_id"],
        offset=base_params.get("offset"),
        location=base_params.get("location"),
        keywords=base_params.get("keywords"),
        fields=base_params.get("fields"),
        experience=base_params.get("experience"),
        applied_job_ids=applied_ids_user2,
        cooled_job_ids=[],
        is_remote_only=None # Add missing param assertion
    )
    mock_get_cached.assert_awaited_once_with(cache_key_user2)
    mock_get_top_jobs.assert_awaited_once() # Called again due to cache miss for the *new* key
    mock_store_cached.assert_awaited_once_with(cache_key_user2, result2)
    assert len(result2["jobs"]) == 5 # Should get full results as cache was missed

    # --- Third Call (User 1 again, should hit cache) ---
    resume["user_id"] = "user1"
    resume["_id"] = "resume1"
    mock_get_applied_jobs.reset_mock()
    mock_generate_key.reset_mock()
    mock_get_cached.reset_mock()
    mock_store_cached.reset_mock()
    mock_get_top_jobs.reset_mock()

    mock_get_applied_jobs.return_value = applied_ids_user1
    mock_get_cooled_jobs.return_value = []  # No cooled jobs
    mock_generate_key.return_value = cache_key_user1 # Use the first key again
    # Simulate cache hit for user 1's key
    mock_get_cached.return_value = result1 # Return the previously stored result

    result3 = await job_matcher.process_job(resume, **base_params, use_cache=True, is_remote_only=None) # Add missing param

    # Assertions for third call (cache hit)
    mock_get_applied_jobs.assert_awaited_once_with("user1")
    mock_generate_key.assert_awaited_once_with(
        resume["_id"],
        offset=base_params.get("offset"),
        location=base_params.get("location"),
        keywords=base_params.get("keywords"),
        fields=base_params.get("fields"),
        experience=base_params.get("experience"),
        applied_job_ids=applied_ids_user1,
        cooled_job_ids=[],
        is_remote_only=None # Add missing param assertion
    )
    mock_get_cached.assert_awaited_once_with(cache_key_user1)
    mock_get_top_jobs.assert_not_awaited() # Should NOT be called due to cache hit
    mock_store_cached.assert_not_awaited() # Should NOT be called due to cache hit
    assert result3 == result1 # Should get the exact cached result
