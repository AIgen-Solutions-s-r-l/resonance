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
async def test_match_jobs_with_resume_with_geo_params():
    """Test that match_jobs_with_resume correctly handles geo parameters."""
    # Create a mock resume
    resume = {
        "user_id": "test_user",
    }
    
    # Create a location filter with geo parameters
    location = LocationFilter(
        latitude=40.7128,
        longitude=-74.0060,
    )
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function with a radius
        await match_jobs_with_resume(
            resume,
            location=[location]
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called()
        call_args = mock_matcher_instance.process_job.call_args_list[0][1]
        
        # Check that the location parameter has the geo data
        assert call_args['location'] is not None
        assert call_args['location'][0].latitude == 40.7128
        assert call_args['location'][0].longitude == -74.0060


@pytest.mark.asyncio
async def test_match_jobs_with_resume_with_geo_params_no_radius():
    """Test that match_jobs_with_resume correctly handles geo parameters without radius."""
    # Create a mock resume
    resume = {
        "user_id": "test_user",
    }
    
    # Create a location filter with geo parameters
    location = LocationFilter(
        latitude=40.7128,
        longitude=-74.0060,
        radius_km=10.0  # 10 km
    )
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function without a radius
        await match_jobs_with_resume(
            resume,
            location=[location]
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called()
        call_args = mock_matcher_instance.process_job.call_args_list[0][1]
        
        # Check that the location parameter has the geo data but no radius
        loc = call_args['location'][0]
        assert loc is not None
        assert loc.latitude == 40.7128
        assert loc.longitude == -74.0060
        assert loc.radius_km == 10.0


@pytest.mark.asyncio
async def test_match_jobs_with_resume_no_geo_params():
    """Test that match_jobs_with_resume correctly handles no geo parameters."""
    # Create a mock resume
    resume = {
        "user_id": "test_user",
    }
    
    # Create a mock OptimizedJobMatcher
    with patch('app.services.matching_service.OptimizedJobMatcher') as MockMatcher:
        # Configure the mock
        mock_matcher_instance = AsyncMock()
        MockMatcher.return_value = mock_matcher_instance
        mock_matcher_instance.process_job.return_value = {"jobs": []}
        
        # Call the function with a radius but no location
        await match_jobs_with_resume(
            resume
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called()
        call_args = mock_matcher_instance.process_job.call_args_list[0][1]
        
        assert len(call_args['location']) == 0


@pytest.mark.asyncio
async def test_match_jobs_with_resume_with_location_and_radius():
    """Test that match_jobs_with_resume correctly handles both location and radius."""
    # Create a mock resume
    resume = {
        "user_id": "test_user",
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
            location=[location]
        )
        
        # Verify that process_job was called with the correct parameters
        mock_matcher_instance.process_job.assert_called()
        call_args = mock_matcher_instance.process_job.call_args_list[0][1]
        
        loc = call_args['location'][0]
        # Check that the location parameter has all the data
        assert loc is not None
        assert loc.country == "USA"
        assert loc.city == "New York"
        assert loc.latitude == 37.7749
        assert loc.longitude == -122.4194
        assert loc.radius_km == 10.0