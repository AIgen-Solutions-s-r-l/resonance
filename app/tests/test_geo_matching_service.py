"""
Tests for geographic matching service functionality.

This module contains tests for the geographic matching service functionality
using PostGIS.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.schemas.location import LocationFilter
from app.services.matching_service import match_jobs_with_resume


@pytest.mark.asyncio
async def test_match_jobs_with_resume_legacy_geo():
    """Test that match_jobs_with_resume correctly handles legacy geo data."""
    # Create a mock resume with legacy geo data
    resume = {
        "user_id": "test_user",
        "latitude": 40.7128,
        "longitude": -74.0060,
    }
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function with a radius
        await match_jobs_with_resume(
            resume,
            radius=5000  # 5 km in meters
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called_once()
        call_args = mock_matcher_instance.process_job.call_args[1]
        
        # Check that the location parameter has the legacy geo data
        assert call_args['location'] is not None
        assert call_args['location'].legacy_latitude == 40.7128
        assert call_args['location'].legacy_longitude == -74.0060
        assert call_args['location'].radius == 5000


@pytest.mark.asyncio
async def test_match_jobs_with_resume_legacy_geo_no_radius():
    """Test that match_jobs_with_resume correctly handles legacy geo data without radius."""
    # Create a mock resume with legacy geo data
    resume = {
        "user_id": "test_user",
        "latitude": 40.7128,
        "longitude": -74.0060,
    }
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function without a radius
        await match_jobs_with_resume(resume)
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called_once()
        call_args = mock_matcher_instance.process_job.call_args[1]
        
        # Check that the location parameter has the legacy geo data but no radius
        assert call_args['location'] is not None
        assert call_args['location'].legacy_latitude == 40.7128
        assert call_args['location'].legacy_longitude == -74.0060
        assert call_args['location'].radius is None


@pytest.mark.asyncio
async def test_match_jobs_with_resume_no_legacy_geo():
    """Test that match_jobs_with_resume correctly handles resume without legacy geo data."""
    # Create a mock resume without legacy geo data
    resume = {
        "user_id": "test_user",
    }
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function with a radius
        await match_jobs_with_resume(
            resume,
            radius=5000  # 5 km in meters
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called_once()
        call_args = mock_matcher_instance.process_job.call_args[1]
        
        # Check that the location parameter doesn't have legacy geo data
        assert call_args['location'] is not None
        assert call_args['location'].legacy_latitude is None
        assert call_args['location'].legacy_longitude is None


@pytest.mark.asyncio
async def test_match_jobs_with_resume_with_location_and_legacy_geo():
    """Test that match_jobs_with_resume correctly handles both location and legacy geo data."""
    # Create a mock resume with legacy geo data
    resume = {
        "user_id": "test_user",
        "latitude": 40.7128,
        "longitude": -74.0060,
    }
    
    # Create a location filter
    location = LocationFilter(
        country="USA",
        city="New York",
        latitude=37.7749,
        longitude=-122.4194,
        radius_km=10.0
    )
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function with a location and radius
        await match_jobs_with_resume(
            resume,
            location=location,
            radius=5000  # 5 km in meters
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called_once()
        call_args = mock_matcher_instance.process_job.call_args[1]
        
        # Check that the location parameter has both the original location data and the legacy geo data
        assert call_args['location'] is not None
        assert call_args['location'].country == "USA"
        assert call_args['location'].city == "New York"
        assert call_args['location'].latitude == 37.7749
        assert call_args['location'].longitude == -122.4194
        assert call_args['location'].radius_km == 10.0
        assert call_args['location'].legacy_latitude == 40.7128
        assert call_args['location'].legacy_longitude == -74.0060
        assert call_args['location'].radius == 5000