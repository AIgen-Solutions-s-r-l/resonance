import random
import pytest
import builtins
from unittest.mock import AsyncMock, MagicMock, patch
from app.libs.job_matcher import JobMatcher


@pytest.fixture
def job_matcher(monkeypatch):
    mock_connect = MagicMock()

    # Patching psycopg.connect globally to return our mock connection
    monkeypatch.setattr("psycopg.connect", mock_connect)

    return JobMatcher()


def test_get_top_jobs_by_multiple_metrics_single_result(job_matcher):
    
    mock_cursor = MagicMock()

    mock_cursor.fetchone.return_value = [1]

    mock_cursor.fetchall.return_value = [
        ("Software Engineer", "Job description", "1", "office", False, "short desc",
         "IT", "3 years", "Python, Django", "USA", "New York", "TechCorp", 1.0)
    ]

    mock_embedding = [0.1, 0.2, 0.3]
    job_matches = job_matcher.get_top_jobs_by_multiple_metrics(mock_cursor, mock_embedding)

    assert len(job_matches) == 1
    assert job_matches[0].title == "Software Engineer"
    assert job_matches[0].score == 1.0


def test_get_top_jobs_by_multiple_metrics_multiple_results(job_matcher):
    mock_cursor = MagicMock()

    mock_results = [ (f"Software Engineer {i}", f"Job description {i}", f"{i}", "office", False, "short desc",
         "IT", "3 years", "Python, Django", "USA", "New York", "TechCorp", 1.0) for i in range(20) ]

    mock_cursor.fetchone.return_value = [len(mock_results)]

    mock_cursor.fetchall.return_value = mock_results

    mock_embedding = [0.1, 0.2, 0.3]
    job_matches = job_matcher.get_top_jobs_by_multiple_metrics(mock_cursor, mock_embedding)

    assert len(job_matches) == len(mock_results)
    assert job_matches[0].title == "Software Engineer 0"
    assert job_matches[len(job_matches) - 1].title == f"Software Engineer {len(job_matches) - 1}"

@pytest.mark.asyncio
async def test_save_matches(monkeypatch, tmp_path, job_matcher):

    mock_results = {"jobs": [{"id": "1", "title": "Software Engineer"}]}
    resume_id = random.randint(0, 5000)

    real_open = builtins.open
    def mock_open(filename, mode='r', *args, **kwargs):
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
    def mock_open(filename, mode='r', *args, **kwargs):
        return real_open(tmp_path / filename, mode, *args, **kwargs)
    
    monkeypatch.setattr("builtins.open", mock_open)

    monkeypatch.setattr("app.core.mongodb.database.get_collection", lambda _ : mock_collection)

    await job_matcher.save_matches(mock_results, resume_id, True)

    file_path = tmp_path / f"job_matches_{resume_id}.json"

    assert file_path.exists(), f"Expected file {file_path} was not created!"
    mock_collection.insert_one.assert_awaited_once()


@pytest.mark.asyncio
async def test_process_job_without_embeddings(job_matcher):
    resume = {"user_id": "123", "experience": "Python Developer"}

    mock_cursor = MagicMock()
    
    job_matcher.conn.cursor.return_value.__enter__.return_value = mock_cursor

    result = await job_matcher.process_job(resume)

    assert len(result) == 0


@pytest.mark.asyncio
async def test_process_job_success(job_matcher):
    resume = {"user_id": "123", "experience": "Python Developer", "vector": [0.1, 0.2, 0.3]}

    mock_cursor = MagicMock()

    mock_results = [ (f"Software Engineer {i}", f"Job description {i}", f"{i}", "office", False, "short desc",
         "IT", "3 years", "Python, Django", "USA", "New York", "TechCorp", 1.0) for i in range(20) ]

    mock_cursor.fetchone.return_value = [len(mock_results)]

    mock_cursor.fetchall.return_value = mock_results
    
    job_matcher.conn.cursor.return_value.__enter__.return_value = mock_cursor

    result = await job_matcher.process_job(resume)

    assert type(result) == type({})
    assert "jobs" in result.keys()
    assert len(result["jobs"]) == len(mock_results)
    assert result["jobs"][0]["title"] == "Software Engineer 0"

