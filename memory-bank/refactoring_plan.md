# JobMatcher Refactoring Plan

## Current Analysis (2025-03-05)

I've completed an analysis of the matching algorithm implementation, focusing on the misalignment between `JobMatch` and `JobSchema`. This misalignment creates maintenance challenges and potential bugs when transforming data between these two representations.

### Key Issues Identified

1. **Field Name Inconsistencies**:
   - `workplace` in JobMatch vs. `workplace_type` in JobSchema
   - `skills` in JobMatch vs. `skills_required` in JobSchema  
   - `company` in JobMatch vs. `company_name` in JobSchema
   - `logo` in JobMatch vs. `company_logo` in JobSchema

2. **Data Structure Problems**:
   - `company` field appears twice in JobMatch (line 30 and line 33)
   - `skills` is a string in JobMatch but List[str] in JobSchema

3. **Missing Fields** in JobMatch that exist in JobSchema:
   - `posted_date`
   - `job_state`
   - `apply_link`
   - `location`

4. **Type Mismatch**: All fields in JobMatch are required, while many in JobSchema are optional

5. **Positional Index Risk**: Current implementation uses positional indexes to access database query results, making the code fragile and error-prone

## Detailed Refactoring Plan

### 1. Create Shared Utilities Module

First, create a shared utilities module to avoid duplicating the skills parsing logic:

```python
# app/utils/data_parsers.py
from typing import List, Optional

def parse_skills_string(value: Optional[str]) -> List[str]:
    """
    Parse a skills string into a list of skills.
    
    Handles both PostgreSQL array format '{skill1,skill2}' and simple comma-separated strings.
    Returns an empty list for None values.
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
    return [item.strip().strip('"') for item in items]
```

### 2. Refactor JobMatch Class

Align the `JobMatch` class with `JobSchema` for consistency:

```python
# app/libs/job_matcher.py
from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime

@dataclass
class JobMatch:
    """Data class for job matching results, aligned with JobSchema."""
    
    id: str
    title: str
    description: Optional[str] = None
    workplace_type: Optional[str] = None
    short_description: Optional[str] = None
    field: Optional[str] = None
    experience: Optional[str] = None
    skills_required: Optional[List[str]] = None
    country: Optional[str] = None
    city: Optional[str] = None
    company_name: Optional[str] = None
    company_logo: Optional[str] = None
    portal: Optional[str] = None
    score: Optional[float] = None
    posted_date: Optional[datetime] = None
    job_state: Optional[str] = None
    apply_link: Optional[str] = None
    location: Optional[str] = None
```

### 3. Implement Dictionary-Based Result Handling

Modify database connection initialization to use `DictCursor`:

```python
def _initialize_database(self) -> None:
    try:
        self.conn = psycopg.connect(
            self.settings.database_url, 
            autocommit=True,
            row_factory=psycopg.rows.dict_row  # Use dictionary rows instead of tuples
        )
        logger.info("Database connection established successfully")
    except psycopg.Error as e:
        logger.exception("Database connection failed")
        raise
```

### 4. Update SQL Queries and Result Processing

Modify the SQL queries to ensure all needed fields are included and properly named:

#### Simple Query (for small result sets)

```sql
SELECT
    j.id as id,
    j.title as title,
    j.description as description,
    j.workplace_type as workplace_type,
    j.short_description as short_description,
    j.field as field,
    j.experience as experience,
    j.skills_required as skills_required,
    j.posted_date as posted_date,
    j.job_state as job_state,
    j.apply_link as apply_link,
    co.country_name as country,
    l.city as city,
    c.company_name as company_name,
    c.logo as company_logo,
    'test_portal' as portal,
    0.0 AS score
FROM "Jobs" j
LEFT JOIN "Companies" c ON j.company_id = c.company_id
LEFT JOIN "Locations" l ON j.location_id = l.location_id
LEFT JOIN "Countries" co ON l.country = co.country_id
{where_sql}
LIMIT 5
```

#### Main Query (with similarity metrics)

Update the main query in a similar fashion, ensuring consistent field naming in both the CTE and final SELECT.

### 5. Result Mapping with Dictionary Access

Replace positional index access with dictionary key access:

```python
# Process dictionary row results into JobMatch objects
from app.utils.data_parsers import parse_skills_string

job_matches = []
for row in results:
    job_match = JobMatch(
        id=str(row['id']),
        title=row['title'],
        description=row['description'],
        workplace_type=row['workplace_type'],
        short_description=row['short_description'],
        field=row['field'],
        experience=row['experience'],
        skills_required=parse_skills_string(row['skills_required']),
        country=row['country'],
        city=row['city'],
        company_name=row['company_name'],
        company_logo=row['company_logo'],
        portal=row['portal'],
        score=float(row['score']),
        posted_date=row.get('posted_date'),
        job_state=row.get('job_state'),
        apply_link=row.get('apply_link')
    )
    job_matches.append(job_match)
```

### 6. Update Job Result Dictionary Creation

Modify the dictionary creation in `process_job` to align with JobSchema field names:

```python
job_results = {
    "jobs": [
        {
            "id": str(match.id),
            "title": match.title,
            "description": match.description,
            "workplace_type": match.workplace_type,
            "short_description": match.short_description,
            "field": match.field,
            "experience": match.experience,
            "skills_required": match.skills_required,
            "country": match.country,
            "city": match.city,
            "company_name": match.company_name,
            "company_logo": match.company_logo,
            "portal": match.portal,
            "score": match.score,
            "posted_date": match.posted_date,
            "job_state": match.job_state,
            "apply_link": match.apply_link
        }
        for match in job_matches
    ]
}
```

### 7. Error Handling Improvements

Add validation and better error handling:

```python
def _validate_row_data(self, row: dict) -> bool:
    """Validate that row has required fields."""
    required_fields = ['id', 'title']
    return all(field in row for field in required_fields)

# Then, in result processing:
for row in results:
    if not self._validate_row_data(row):
        logger.warning(
            "Skipping row with missing required fields",
            row=row
        )
        continue
    
    # Process row into JobMatch...
```

## Implementation Sequence

I recommend implementing these changes in the following order:

1. Create the shared utils module with the skills parser
2. Refactor the JobMatch class to align with JobSchema
3. Update the SQL queries to use proper field names
4. Modify the database connection to use dictionary rows
5. Update result processing to use dictionary access
6. Add improved error handling
7. Update tests

This approach allows for incremental implementation and testing, reducing the risk of introducing bugs.