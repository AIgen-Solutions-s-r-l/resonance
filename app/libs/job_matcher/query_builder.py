"""
SQL query building for job matcher.

This module handles SQL query construction for job matching operations.
"""

from typing import List, Optional, Tuple, Dict, Any
from loguru import logger
from time import time

from app.schemas.location import LocationFilter
from app.libs.job_matcher.exceptions import QueryBuildingError


class JobQueryBuilder:
    """Builder for job matching SQL queries."""
    
    def build_filter_conditions(
        self,
        location: Optional[LocationFilter] = None,
        keywords: Optional[List[str]] = None,
        experience: Optional[List[str]] = None
    ) -> Tuple[List[str], List[Any]]:
        """
        Build SQL filter conditions based on location, keywords, and experience.
        
        Args:
            location: Optional location filter
            keywords: Optional keyword filter
            experience: Optional experience level filter. Allowed values: Intern, Entry, Mid, Executive
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        start_time = time()
        try:
            where_clauses = ["embedding IS NOT NULL"]
            query_params = []
            
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
            
            elapsed = time() - start_time
            logger.debug(
                "Query conditions built",
                elapsed_time=f"{elapsed:.6f}s",
                conditions_count=len(where_clauses),
                params_count=len(query_params),
                params=str(query_params)[:100]  # Log a preview of params for debugging
            )
            
            return where_clauses, query_params
            
        except Exception as e:
            elapsed = time() - start_time
            logger.error(
                "Failed to build query conditions",
                error=str(e),
                error_type=type(e).__name__,
                elapsed_time=f"{elapsed:.6f}s"
            )
            raise QueryBuildingError(f"Failed to build query conditions: {e}")
    
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
        
        # City filter
        if location.city:
            where_clauses.append("(l.city = %s OR l.city = 'remote')")
            query_params.append(location.city)
        
        # Geo filter
        if (
            location.latitude is not None
            and location.longitude is not None
            and location.radius_km is not None
        ):
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
            # Convert to float to ensure proper parameter handling
            query_params.append(float(location.longitude))
            query_params.append(float(location.latitude))
            query_params.append(float(location.radius_km))
        
        return where_clauses, query_params
    
    def _build_keyword_filters(
        self, keywords: List[str]
    ) -> Tuple[List[str], List[Any]]:
        """
        Build keyword filter conditions.
        
        Args:
            keywords: List of keywords
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        or_clauses = []
        query_params = []
        
        for kw in keywords:
            or_clauses.append("(j.title ILIKE %s OR j.description ILIKE %s)")
            # Add each parameter separately
            query_params.append(f"%{kw}%")
            query_params.append(f"%{kw}%")
        
        # Combine clauses
        if or_clauses:
            return ["(" + " OR ".join(or_clauses) + ")"], query_params
        
        return [], []
    
    def _build_experience_filters(
        self, experience: List[str]
    ) -> Tuple[List[str], List[Any]]:
        """
        Build experience filter conditions.
        
        Args:
            experience: List of experience levels (Intern, Entry, Mid, Executive)
            
        Returns:
            Tuple of (where clauses list, query parameters list)
        """
        logger.info(f"Building experience filters for: {experience}")
        
        # Validate experience values
        valid_experience = ["Intern", "Entry", "Mid", "Executive"]
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
        
        return [], []


# Singleton instance
query_builder = JobQueryBuilder()