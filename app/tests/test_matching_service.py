from unittest.mock import AsyncMock

import pytest

from app.services.matching_service import get_resume_by_user_id

# I won't be unit testing match_jobs_with_resume as it is literally 1 class instantiation + 1 method call

@pytest.mark.asyncio
async def test_get_resume_by_user_id(monkeypatch):

    fake_collection = AsyncMock()

    fake_collection.find_one.return_value = {
        "_id": "badc0ff3",
        "fake_field": "fake_value"
    }

    monkeypatch.setattr("app.services.matching_service.collection_name", fake_collection)

    result = await get_resume_by_user_id(123)

    assert "fake_field" in result.keys(), f"unexpectedly, result was {result}"
    assert result["fake_field"] == "fake_value", f"expected 'fake_field' to be 'fake_value', got '{result['fake_field']}' instead"

