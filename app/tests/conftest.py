"""
Pytest configuration and fixtures.
"""

import pytest
import asyncio
from app.utils.db_utils import close_all_connection_pools

@pytest.fixture(autouse=True)
async def cleanup_connection_pools():
    """
    Fixture to clean up database connection pools after each test.
    
    This helps prevent connection pool exhaustion in CI environments
    where resources are more limited.
    """
    # Setup - run before the test
    yield
    # Teardown - run after the test
    await close_all_connection_pools()