"""
Tests for geographic matching functionality.

This module contains tests for the geographic matching functionality
using PostGIS.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.schemas.location import LocationFilter
from app.libs.job_matcher.query_builder import JobQueryBuilder


@pytest.fixture
def query_builder():
    """Fixture for JobQueryBuilder."""
    return JobQueryBuilder()


class TestGeoMatching:
    """Test cases for geographic matching functionality."""

    def test_build_location_filters_without_geo(self, query_builder):
        """Test building location filters without geo parameters."""
        # Create a LocationFilter without geo parameters
        location = LocationFilter(
            country="USA",
            city="New York"
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters([location])
        
        # Verify that the geo filter is not included
        assert len(where_clauses) == 1  # country and city filters
        assert all("ST_DWithin" not in clause for clause in where_clauses)
        
        # Verify the parameters
        assert len(query_params) == 1  # Only city parameter (country is handled specially for USA)
        assert query_params[0] == "New York"


    def test_default_radius_in_settings(self):
        """Test that the default radius in settings is 50 km."""
        from app.core.config import settings
        
        # Verify the default radius is 50000 meters (50 km)
        assert settings.default_geo_radius_meters == 50000

        
    def test_geo_coordinates_prioritized_over_city(self, query_builder):
        """Test that latitude and longitude coordinates are prioritized over city names."""
        # Create a LocationFilter with both geo parameters and city
        location = LocationFilter(
            latitude=40.7128,
            longitude=-74.0060,
            radius_km=5,  # 5 km in meters
            city="New York"  # This should be ignored when geo coordinates are provided
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters([location])
        
        # Verify that the geo filter is included
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        
        # Verify that the city filter is NOT included
        assert all("l.city = %s" not in clause for clause in where_clauses)
        
        # Verify the parameters - should only include geo parameters, not city
        assert len(query_params) == 3
        assert query_params[0] == -74.0060  # longitude
        assert query_params[1] == 40.7128   # latitude
        assert query_params[2] == 5.0    

        # Verify that "New York" is not in the parameters
        assert "New York" not in query_params