import random
import pytest
import asyncio
import builtins
from unittest.mock import AsyncMock, MagicMock, patch
from app.libs.job_matcher_optimized import OptimizedJobMatcher

# Create a mock Row that supports both dict and list access
class MockRow(dict):
    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return super().__getitem__(key)


@pytest.fixture
async def job_matcher(monkeypatch):
    # Create a mock cursor
    mock_cursor = AsyncMock()
    
    # Create a properly configured async context manager mock
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_cursor
    
    # Mock the get_db_cursor function to return our configured mock
    monkeypatch.setattr(
        "app.libs.job_matcher_optimized.get_db_cursor", 
        lambda *args, **kwargs: mock_context
    )
    
    # Return a new instance of the optimized matcher and the mock cursor
    matcher = OptimizedJobMatcher()
    return matcher, mock_cursor


@pytest.mark.asyncio
async def test_get_top_jobs_by_vector_similarity_single_result(job_matcher):
    # Need to await the fixture
    matcher, mock_cursor = await job_matcher
    
    mock_cursor.fetchone.return_value = MockRow({'count': 1})
    
    mock_row = MockRow({
        'title': "Software Engineer",
        'description': "Job description",
        'id': "1",
        'workplace_type': "office",
        'short_description': "short desc",
        'field': "IT",
        'experience': "3 years",
        'skills_required': "Python, Django",
        'country': "USA",
        'city': "New York",
        'company_name': "TechCorp",
        'score': 1.0
    })
    
    mock_cursor.fetchall.return_value = [mock_row]
    
    mock_embedding = [0.1, 0.2, 0.3]
    job_matches = await matcher.get_top_jobs_by_vector_similarity(
        mock_embedding
    )
    
    assert len(job_matches) == 1
    assert job_matches[0].title == "Software Engineer"
    assert job_matches[0].score == 1.0


@pytest.mark.asyncio
async def test_get_top_jobs_by_vector_similarity_multiple_results(job_matcher):
    # Need to await the fixture
    matcher, mock_cursor = await job_matcher
    
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
    
    mock_cursor.fetchone.return_value = MockRow({'count': len(mock_results)})
    mock_cursor.fetchall.return_value = mock_results
    
    mock_embedding = [0.1, 0.2, 0.3]
    job_matches = await matcher.get_top_jobs_by_vector_similarity(
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
    # Need to await the fixture
    matcher, _ = await job_matcher
    
    mock_results = {"jobs": [{"id": "1", "title": "Software Engineer"}]}
    resume_id = random.randint(0, 5000)
    
    real_open = builtins.open
    
    def mock_open(filename, mode="r", *args, **kwargs):
        return real_open(tmp_path / filename, mode, *args, **kwargs)
    
    monkeypatch.setattr("builtins.open", mock_open)
    
    await matcher.save_matches(mock_results, resume_id, False)
    
    file_path = tmp_path / f"job_matches_{resume_id}.json"
    
    assert file_path.exists(), f"Expected file {file_path} was not created!"


@pytest.mark.asyncio
async def test_save_matches_also_on_mongo(monkeypatch, tmp_path, job_matcher):
    # Need to await the fixture
    matcher, _ = await job_matcher
    
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
    
    await matcher.save_matches(mock_results, resume_id, True)
    
    file_path = tmp_path / f"job_matches_{resume_id}.json"
    
    assert file_path.exists(), f"Expected file {file_path} was not created!"
    mock_collection.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_job_without_embeddings(job_matcher):
    # Need to await the fixture
    matcher, mock_cursor = await job_matcher
    
    resume = {"user_id": "123", "experience": "Python Developer"}
    
    # Mock cache functions
    matcher._generate_cache_key = AsyncMock(return_value="test_key")
    matcher._get_cached_results = AsyncMock(return_value=None)
    
    result = await matcher.process_job(resume)
    
    assert "jobs" in result
    assert len(result["jobs"]) == 0


@pytest.mark.asyncio
async def test_process_job_success(job_matcher):
    # Need to await the fixture
    matcher, mock_cursor = await job_matcher
    
    resume = {
        "user_id": "123",
        "experience": "Python Developer",
        "vector": [0.1, 0.2, 0.3],
    }
    
    # Create mock results using MockRow for process_job test
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
    
    mock_cursor.fetchone.return_value = MockRow({'count': len(mock_results)})
    mock_cursor.fetchall.return_value = mock_results
    
    # Mock cache functions
    matcher._generate_cache_key = AsyncMock(return_value="test_key")
    matcher._get_cached_results = AsyncMock(return_value=None)
    matcher._store_cached_results = AsyncMock()
    
    result = await matcher.process_job(resume)
    
    assert isinstance(result, dict)
    assert "jobs" in result.keys()
    assert len(result["jobs"]) == len(mock_results)
    assert result["jobs"][0]["title"] == "Software Engineer 0"


@pytest.mark.asyncio
async def test_process_job_with_cache(job_matcher):
    # Need to await the fixture
    matcher, mock_cursor = await job_matcher
    
    resume = {
        "user_id": "123",
        "experience": "Python Developer",
        "vector": [0.1, 0.2, 0.3],
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
    
    # Mock cache functions
    matcher._generate_cache_key = AsyncMock(return_value="test_key")
    matcher._get_cached_results = AsyncMock(return_value=cached_results)
    
    result = await matcher.process_job(resume)
    
    assert isinstance(result, dict)
    assert "jobs" in result.keys()
    assert len(result["jobs"]) == 1
    assert result["jobs"][0]["title"] == "Cached Job"
    
    # Verify that cache functions were called correctly
    matcher._generate_cache_key.assert_awaited_once()
    matcher._get_cached_results.assert_awaited_once_with("test_key")
