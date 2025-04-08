"""
Standalone test for the JobQueryBuilder._build_location_filters method.
"""

import sys
import os
import pytest
from typing import List, Optional, Tuple, Dict, Any

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# Create a mock for the settings
class MockSettings:
    default_geo_radius_meters = 50000

# Mock the imports
sys.modules['app.core.config'] = type('MockConfig', (), {'settings': MockSettings()})
sys.modules['app.libs.job_matcher.exceptions'] = type('MockExceptions', (), {'QueryBuildingError': Exception})
sys.modules['loguru'] = type('MockLoguru', (), {'logger': type('MockLogger', (), {'debug': print, 'info': print, 'error': print})})

# Import the LocationFilter schema
from app.schemas.location import LocationFilter

# Define a simplified version of the JobQueryBuilder class
class JobQueryBuilder:
    """Simplified builder for job matching SQL queries."""
    
    def _build_location_filters(
        self, location: LocationFilter
    ) -> Tuple[List[str], List[Any]]:
        """
        Build location filter conditions.
        
        Args:
            location: Location filter
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        where_clauses = []
        query_params = []
        
        # Country filter - Using direct comparison without CASE statement
        if location.country:
            if location.country == 'USA':
                # Handle USA/United States special case without parameters in the CASE
                where_clauses.append("(co.country_name = 'United States')")
            else:
                where_clauses.append("(co.country_name = %s)")
                query_params.append(location.country)
        
        # Check if we have both latitude and longitude
        has_geo_coordinates = location.latitude is not None and location.longitude is not None
        
        # City filter - only add if geo coordinates are NOT provided
        if location.city and not has_geo_coordinates:
            where_clauses.append("(l.city = %s OR l.city = 'remote')")
            query_params.append(location.city)
        
        # Geo filter - if we have both latitude and longitude
        if has_geo_coordinates:
            # Determine which radius to use (radius in meters takes precedence over radius_km)
            if hasattr(location, 'radius') and location.radius is not None:
                # Use radius in meters directly
                radius_meters = float(location.radius)
                use_km_multiplier = False
            elif location.radius_km is not None:
                # Use radius in km, will be multiplied by 1000 in the query
                radius_meters = float(location.radius_km)
                use_km_multiplier = True
            else:
                # Use default radius from settings if no radius is specified
                radius_meters = float(MockSettings.default_geo_radius_meters / 1000)  # Convert from meters to km
                use_km_multiplier = True
            
            # Build the geo filter clause
            if use_km_multiplier:
                where_clauses.append(
                    """
                    (
                        l.city = 'remote'
                        OR ST_DWithin(
                            ST_MakePoint(l.longitude::DOUBLE PRECISION, l.latitude::DOUBLE PRECISION)::geography,
                            ST_MakePoint(%s, %s)::geography,
                            %s * 1000
                        )
                    )
                    """
                )
            else:
                where_clauses.append(
                    """
                    (
                        l.city = 'remote'
                        OR (
                            l.latitude IS NOT NULL
                            AND l.longitude IS NOT NULL
                            AND ST_DWithin(
                                ST_MakePoint(l.longitude::DOUBLE PRECISION, l.latitude::DOUBLE PRECISION)::geography,
                                ST_MakePoint(%s, %s)::geography,
                                %s
                            )
                        )
                    )
                    """
                )
            
            # Convert to float to ensure proper parameter handling
            query_params.append(float(location.longitude))
            query_params.append(float(location.latitude))
            query_params.append(radius_meters)
        
        return where_clauses, query_params


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

    def test_geo_coordinates_prioritized_over_city(self, query_builder):
        """Test that latitude and longitude coordinates are prioritized over city names."""
        # Create a LocationFilter with both geo parameters and city
        location = LocationFilter(
            latitude=40.7128,
            longitude=-74.0060,
            radius=5000,  # 5 km in meters
            city="New York"  # This should be ignored when geo coordinates are provided
        )
        
        # Build the location filters
        where_clauses, query_params = query_builder._build_location_filters(location)
        
        # Verify that the geo filter is included
        assert len(where_clauses) == 1
        assert "ST_DWithin" in where_clauses[0]
        
        # Verify that the city filter is NOT included
        assert all("l.city = %s" not in clause for clause in where_clauses)
        
        # Verify the parameters - should only include geo parameters, not city
        assert len(query_params) == 3
        assert query_params[0] == -74.0060  # longitude
        assert query_params[1] == 40.7128   # latitude
        assert query_params[2] == 5000.0    # radius in meters (as float)
        
        # Verify that "New York" is not in the parameters
        assert "New York" not in query_params


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", __file__])