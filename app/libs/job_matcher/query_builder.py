"""
SQL query building for job matcher.

This module handles SQL query construction for job matching operations.
"""

from typing import List, Optional, Tuple, Dict, Any
from app.log.logging import logger
from app.core.config import settings
from time import time

from app.schemas.job_match import ManyToManyFilter
from app.schemas.location import LocationFilter
from app.libs.job_matcher.exceptions import QueryBuildingError

class JobQueryBuilder:
    """Builder for job matching SQL queries."""
    
    def build_filter_conditions(
        self,
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        fields: Optional[List[int]] = None,
        experience: Optional[List[str]] = None,
        company: Optional[str] = None,
        is_remote_only: Optional[bool] = None # Add new parameter
    ) -> Tuple[List[ManyToManyFilter], List[str], List[Any]]:
        """
        Build SQL filter conditions based on location, keywords, experience, and company.
        
        Args:
            location: Optional location filter.
            keywords: Optional keyword filter.
            experience: Optional experience level filter. Allowed values: Entry-level, Executive-level, Internship, Mid-level, Senior-level.
            company: Optional company name filter.
            is_remote_only: Optional filter for remote jobs only.
            
        Returns:
            Triple of (many-to-many filter clauses, where clauses list, query parameters list)
        """
        start_time = time()
        try:
            where_clauses = ["embedding IS NOT NULL"]
            many_to_many_filters = []
            query_params = []
            
            if fields and len(fields) > 0:
                fields_filter = self._build_fields_filters(fields)
                many_to_many_filters.extend(fields_filter)

            # Add location filters
            if location:
                location_clauses, location_params = self._build_location_filters(location)
                where_clauses.extend(location_clauses)
                query_params.extend(location_params)
            
            # Add keyword filters
            if keywords and len(keywords) > 0:
                keyword_clauses, keyword_params = self._build_keyword_filters(keywords)
                where_clauses.extend(keyword_clauses)
                query_params.extend(keyword_params)

            # Add experience filters
            if experience and len(experience) > 0:
                experience_clauses, experience_params = self._build_experience_filters(experience)
                where_clauses.extend(experience_clauses)
                query_params.extend(experience_params)
        
            # Add company filter
            if company:
                company_clause, company_param = self._build_company_filter(company)
                where_clauses.extend(company_clause)
                query_params.extend(company_param)
           
            # Add remote only filter
            if is_remote_only:
                # Assuming 'l' is the alias for the Locations table
                where_clauses.append("(LOWER(l.city) LIKE '%%remote%%')") # Escape % for psycopg
                # No parameter needed for this specific clause
                    
            elapsed = time() - start_time
            logger.debug(
                "Query conditions built",
                elapsed_time=f"{elapsed:.6f}s",
                conditions_count=len(where_clauses),
                params_count=len(query_params),
                params=str(query_params)[:100]  # Log a preview of params for debugging
            )
            
            return many_to_many_filters, where_clauses, query_params
            
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "Failed to build query conditions",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise QueryBuildingError(f"Failed to build query conditions: {e}")
        
    '''
    OLD IMPLEMENTATION OF _build_fields_filters
    -------------------------------------------

    def _build_fields_filters(
        self, fields: List[int]
    ) -> List[ManyToManyFilter]:
        """
        Build fields filter as a Many-to-Many filter

        fields - not nullable and with len > 0
        """
        relationship = '"FieldJobs"'  # TODO : replace with relationship name
        parametrized_any = "ANY(%s" + ", %s" * (len(fields) - 1) + ")"
        return [ManyToManyFilter(
            relationship=f"{relationship} AS fj",
            where_clause=f"(selected.id = fj.job_id AND fj.field_id = {parametrized_any})",
            params=[fields]
        )]  
    '''
    
    def _build_fields_filters(
        self, fields: List[int]
    ) -> List[ManyToManyFilter]:
        """
        Build field filters for a many-to-many relationship.

        The whole list of IDs is passed as **one** parameter; psycopg adapts the
        Python list to an `int[]`, and the explicit `::int[]` cast keeps the query
        planner happy even when the list is empty.
        """
        relationship = '"FieldJobs"'

        return [
            ManyToManyFilter(
                relationship=f"{relationship} AS fj",
                where_clause=(
                    "(selected.id = fj.job_id "
                    "AND fj.field_id = ANY(%s::int[]))"
                ),
                params=[fields],
            )
        ]


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
                radius_meters = float(settings.default_geo_radius_meters / 1000)  # Convert from meters to km
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
    
    def _build_keyword_filters(
        self, keywords: List[str]
    ) -> Tuple[List[str], List[Any]]:
        """
        Build keyword filter conditions, treating keywords as a single phrase.

        This method handles input as follows:
        - If a single string is provided (with or without spaces), it's treated as an exact phrase.
        - If multiple strings are provided, they are assumed to have been preprocessed into a single phrase.
        - In all cases, only the exact phrase is searched for, not individual words.

        Args:
            keywords: List of keywords or phrases. Each element can be a single word or a multi-word phrase.
                     Multiple elements are assumed to have been preprocessed into a single phrase.

        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        if not keywords or len(keywords) == 0:
            return [], []
            
        # Get the phrase (either the single keyword or the preprocessed phrase)
        phrase = keywords[0].strip()
        logger.info(f"Processing search phrase as a complete unit: '{phrase}'")
        
        # Create a single clause that requires the exact phrase in title OR description
        where_clause = ["(j.title ILIKE '%%' || %s || '%%' OR j.description ILIKE '%%' || %s || '%%')"]
        query_params = [phrase, phrase]
        
        return where_clause, query_params
    
    def _build_experience_filters(
        self, experience: List[str]
    ) -> Tuple[List[str], List[Any]]:
        """
        Build experience filter conditions.
        
        Args:
            experience: List of experience levels (Entry-level, Executive-level, Internship, Mid-level, Senior-level)
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        logger.info(f"Building experience filters for: {experience}")
        
        # Validate experience values
        valid_experience = ["Internship", "Entry-level", "Executive-level", "Mid-level", "Senior-level"]
        filtered_experience = [exp for exp in experience if exp in valid_experience]
        
        if not filtered_experience:
            logger.warning(f"No valid experience levels found in: {experience}")
            return [], []
        
        # Create OR clauses for each experience level
        or_clauses = []
        query_params = []
        
        for exp in filtered_experience:
            or_clauses.append("(j.experience = %s)")
            query_params.append(exp)
        
        # Combine clauses
        if or_clauses:
            combined_clause = ["(" + " OR ".join(or_clauses) + ")"]
            logger.info(f"Experience filter clause: {combined_clause}, params: {query_params}")
            return combined_clause, query_params
        
        return [], [] # Return empty lists if no valid experience levels were processed or filtered

    def _build_company_filter(
        self, company: str
    ) -> Tuple[List[str], List[Any]]:
        """
        Build company filter condition.
        
        Args:
            company: Company name to filter by.
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        logger.debug(f"Building company filter for: {company}")
        # Use ILIKE for case-insensitive matching
        # Assuming the company name column is 'company_name' in the jobs table (aliased as j)
        clause = "(j.company_name ILIKE %s)"
        params = [company]  # Use parameterization
        return [clause], params

        


# Singleton instance
query_builder = JobQueryBuilder()