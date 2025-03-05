"""Data parsing utilities for the matching service."""

from typing import List, Optional


def parse_skills_string(value: Optional[str]) -> List[str]:
    """
    Parse a skills string into a list of skills.
    
    Handles both PostgreSQL array format '{skill1,skill2}' and simple comma-separated strings.
    Returns an empty list for None values.
    
    Args:
        value: A string containing skills in either PostgreSQL array format or comma-separated format,
              or None.
              
    Returns:
        List of cleaned skill strings.
        
    Examples:
        >>> parse_skills_string('{Python,SQL,"Machine Learning"}')
        ['Python', 'SQL', 'Machine Learning']
        >>> parse_skills_string('Python, SQL, Machine Learning')
        ['Python', 'SQL', 'Machine Learning']
        >>> parse_skills_string(None)
        []
    """
    if value is None:
        return []
        
    # If it's already a list, just return it
    if isinstance(value, list):
        return value
        
    # Process string format
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1]
        
    # Split and clean
    if not value:
        return []
        
    items = value.split(",")
    return [item.strip().strip('"').strip("'") for item in items if item.strip()]