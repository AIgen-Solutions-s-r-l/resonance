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

    def test_location_filter_with_geo_parameters(self):
        """Test that LocationFilter accepts geo parameters."""
        # Create a LocationFilter with geo parameters
        location = LocationFilter(
            latitude=40.7128,
            longitude=-74.0060,
            radius=5000  # 5 km in meters
        )
        
        # Verify the parameters are set correctly
        assert location.latitude == 40.7128
        assert location.longitude == -74.0060
        assert location.radius == 5000

    def test_build_location_filters_with_geo_and_radius_meters(self, query_builder):
        """Test building location filters with geo parameters and radius in meters."""
        # Create a LocationFilter with geo parameters and radius in meters
        location = LocationFilter(
            latitude=40.7128,
            longitude=-74.0060,
            radius=5000  # 5 km in meters
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is included
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        
        # Verify the parameters
        assert len(query_params) == 3
        assert query_params[0] == -74.0060  # longitude
        assert query_params[1] == 40.7128   # latitude
        assert query_params[2] == 5000.0    # radius in meters (as float)

    def test_build_location_filters_with_geo_and_radius_km(self, query_builder):
        """Test building location filters with geo parameters and radius in kilometers."""
        # Create a LocationFilter with geo parameters and radius in kilometers
        location = LocationFilter(
            latitude=40.7128,
            longitude=-74.0060,
            radius_km=10.0  # 10 km
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is included
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        
        # Verify the parameters
        assert len(query_params) == 3
        assert query_params[0] == -74.0060  # longitude
        assert query_params[1] == 40.7128   # latitude
        assert query_params[2] == 10.0      # radius in km

    def test_build_location_filters_without_geo(self, query_builder):
        """Test building location filters without geo parameters."""
        # Create a LocationFilter without geo parameters
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

    def test_build_location_filters_with_incomplete_geo(self, query_builder):
        """Test building location filters with incomplete geo parameters."""
        # Create a LocationFilter with only latitude but no longitude
        location = LocationFilter(
            latitude=40.7128,
            longitude=None,
            radius=5000
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is not included
        assert len(where_clauses) == 0
        assert len(query_params) == 0
        
        # Create a LocationFilter with only longitude but no latitude
        location = LocationFilter(
            latitude=None,
            longitude=-74.0060,
            radius=5000
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is not included
        assert len(where_clauses) == 0
        assert len(query_params) == 0

    def test_radius_precedence(self, query_builder):
        """Test that radius in meters takes precedence over radius_km."""
        # Create a LocationFilter with both radius and radius_km
        location = LocationFilter(
            latitude=40.7128,
            longitude=-74.0060,
            radius_km=10.0,  # 10 km
            radius=5000      # 5 km in meters (should take precedence)
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is included
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        
        # Verify the parameters - radius should be 5000 meters, not 10.0 * 1000
        assert len(query_params) == 3
        assert query_params[0] == -74.0060  # longitude
        assert query_params[1] == 40.7128   # latitude
        assert query_params[2] == 5000.0    # radius in meters (as float)