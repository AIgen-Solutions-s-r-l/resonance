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

    def test_location_filter_with_legacy_geo(self):
        """Test that LocationFilter accepts legacy geo parameters."""
        # Create a LocationFilter with legacy geo parameters
        location = LocationFilter(
            legacy_latitude=40.7128,
            legacy_longitude=-74.0060,
            radius=5000  # 5 km in meters
        )
        
        # Verify the parameters are set correctly
        assert location.legacy_latitude == 40.7128
        assert location.legacy_longitude == -74.0060
        assert location.radius == 5000

    def test_build_location_filters_with_legacy_geo(self, query_builder):
        """Test building location filters with legacy geo parameters."""
        # Create a LocationFilter with legacy geo parameters
        location = LocationFilter(
            legacy_latitude=40.7128,
            legacy_longitude=-74.0060,
            radius=5000  # 5 km in meters
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is included
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        assert "l.latitude IS NOT NULL" in where_clauses[0]
        assert "l.longitude IS NOT NULL" in where_clauses[0]
        
        # Verify the parameters
        assert len(query_params) == 3
        assert query_params[0] == -74.0060  # longitude
        assert query_params[1] == 40.7128   # latitude
        assert query_params[2] == 5000      # radius in meters

    def test_build_location_filters_with_legacy_geo_default_radius(self, query_builder):
        """Test building location filters with legacy geo parameters and default radius."""
        # Create a LocationFilter with legacy geo parameters but no radius
        location = LocationFilter(
            legacy_latitude=40.7128,
            legacy_longitude=-74.0060
        )
        
        # Mock the settings to have a default radius
        with patch('app.libs.job_matcher.query_builder.settings') as mock_settings:
            mock_settings.default_geo_radius_meters = 10000  # 10 km in meters
            
            # Build the location filters
            where_clauses, query_params = query_builder._build_location_filters(location)
            
            # Verify that the geo filter is included
            assert len(where_clauses) == 1
            assert "ST_DWithin" in where_clauses[0]
            
            # Verify the parameters
            assert len(query_params) == 3
            assert query_params[0] == -74.0060  # longitude
            assert query_params[1] == 40.7128   # latitude
            assert query_params[2] == 10000     # default radius in meters

    def test_build_location_filters_without_legacy_geo(self, query_builder):
        """Test building location filters without legacy geo parameters."""
        # Create a LocationFilter without legacy geo parameters
        location = LocationFilter(
            country="USA",
            city="New York"
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is not included
        assert len(where_clauses) == 2  # country and city filters
        assert all("ST_DWithin" not in clause for clause in where_clauses)
        
        # Verify the parameters
        assert len(query_params) == 1  # Only city parameter (country is handled specially for USA)
        assert query_params[0] == "New York"

    def test_build_location_filters_with_incomplete_legacy_geo(self, query_builder):
        """Test building location filters with incomplete legacy geo parameters."""
        # Create a LocationFilter with only latitude but no longitude
        location = LocationFilter(
            legacy_latitude=40.7128,
            legacy_longitude=None,
            radius=5000
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is not included
        assert len(where_clauses) == 0
        assert len(query_params) == 0
        
        # Create a LocationFilter with only longitude but no latitude
        location = LocationFilter(
            legacy_latitude=None,
            legacy_longitude=-74.0060,
            radius=5000
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is not included
        assert len(where_clauses) == 0
        assert len(query_params) == 0

    def test_build_location_filters_with_both_geo_types(self, query_builder):
        """Test building location filters with both regular and legacy geo parameters."""
        # Create a LocationFilter with both regular and legacy geo parameters
        location = LocationFilter(
            latitude=37.7749,
            longitude=-122.4194,
            radius_km=10.0,
            legacy_latitude=40.7128,
            legacy_longitude=-74.0060,
            radius=5000
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that only the regular geo filter is included (it takes precedence)
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        
        # Verify the parameters are for the regular geo filter
        assert len(query_params) == 3
        assert query_params[0] == -122.4194  # longitude
        assert query_params[1] == 37.7749    # latitude
        assert query_params[2] == 10.0       # radius in km