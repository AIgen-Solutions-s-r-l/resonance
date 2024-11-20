import psycopg
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.main import process_resume_callback
from app.services.lib_document_finder.match_cv import process_job
import json

# Test: Process Resume Callback - Success Case
@pytest.mark.asyncio
async def test_process_resume_callback_success():
    resume_data = {"user_id": "123", "experience": "Python Developer"}
    matched_jobs = ["Job Description 1", "Job Description 2"]

    with patch("app.main.rabbitmq_client.send_message", new_callable=AsyncMock) as mock_send_message, \
         patch("app.services.lib_document_finder.match_cv.process_job", return_value=matched_jobs):
        
        message = AsyncMock()
        message.body.decode = MagicMock(return_value=json.dumps(resume_data))

        await process_resume_callback(message)

        mock_send_message.assert_awaited_once_with(queue="job_to_apply_queue", message=matched_jobs)

# Test: Process Resume Callback - No Matches Found
@pytest.mark.asyncio
async def test_process_resume_callback_no_matches():
    resume_data = {"user_id": "123", "experience": "Unknown Tech"}

    with patch("app.main.rabbitmq_client.send_message", new_callable=AsyncMock) as mock_send_message, \
         patch("app.services.lib_document_finder.match_cv.process_job", return_value=[]):
        
        message = AsyncMock()
        message.body.decode = MagicMock(return_value=json.dumps(resume_data))

        await process_resume_callback(message)

        mock_send_message.assert_awaited_once_with(queue="job_to_apply_queue", message=[])

# Test: Process Resume Callback - Invalid Message
@pytest.mark.asyncio
async def test_process_resume_callback_invalid_message():
    invalid_message = AsyncMock()
    invalid_message.body.decode = MagicMock(side_effect=ValueError("Invalid JSON"))

    with patch("app.main.rabbitmq_client.send_message", new_callable=AsyncMock) as mock_send_message:
        with pytest.raises(ValueError, match="Invalid JSON"):
            await process_resume_callback(invalid_message)

        mock_send_message.assert_not_called()

# Test: Process Job - Database Error
def test_process_job_database_error():
    resume_data = {"user_id": "123", "experience": "Python Developer"}

    with patch("app.services.lib_document_finder.match_cv.conn.cursor", MagicMock()) as mock_cursor, \
         patch("app.services.lib_document_finder.match_cv.embedding_model") as MockEmbeddings:

        # Mock a database connection error
        mock_cursor.return_value.__enter__.side_effect = psycopg.ProgrammingError("cannot adapt type 'MagicMock' using placeholder '%s' (format: AUTO)")

        # Verify the exception is raised with the correct message
        with pytest.raises(psycopg.ProgrammingError, match="cannot adapt type 'MagicMock' using placeholder '%s'"):
            process_job(json.dumps(resume_data))

def test_process_job_success():
    # Simplified input data
    resume_data = {"user_id": "123", "experience": "Python Developer"}
    
    # Database mock return values
    db_results = [
        ("Job Description 1", 0.1),
        ("Job Description 2", 0.2),
    ]
    
    # Expected output
    expected_jobs = ["Job Description 1", "Job Description 2"]

    # Mock the database and embedding model
    with patch("app.services.lib_document_finder.match_cv.conn.cursor", MagicMock()) as mock_cursor, \
         patch("app.services.lib_document_finder.match_cv.embedding_model") as MockEmbeddings:

        # Mock embeddings
        mock_embedding = [0.1] * 1536
        MockEmbeddings.embed_documents.return_value = [mock_embedding]

        # Mock database behavior
        mock_cursor.return_value.__enter__.return_value.fetchall.return_value = db_results

        # Call the function
        jobs = process_job(json.dumps(resume_data))

        # Enhanced assertion
        assert jobs == expected_jobs, f"Expected {expected_jobs}, but got {jobs}"

def test_process_job_no_matches():
    # Simplified input data
    resume_data = {"user_id": "123", "experience": "Unknown Tech"}

    # Simulate no matches in the database
    db_results = []
    expected_jobs = []

    # Mock the database and embedding model
    with patch("app.services.lib_document_finder.match_cv.conn.cursor", MagicMock()) as mock_cursor, \
         patch("app.services.lib_document_finder.match_cv.embedding_model") as MockEmbeddings:

        # Mock embeddings
        mock_embedding = [0.1] * 1536
        MockEmbeddings.embed_documents.return_value = [mock_embedding]

        # Mock database behavior to return no results
        mock_cursor.return_value.__enter__.return_value.fetchall.return_value = db_results

        # Call the function
        jobs = process_job(json.dumps(resume_data))

        # Enhanced assertion
        assert jobs == expected_jobs, f"Expected {expected_jobs}, but got {jobs}"