# Implementation Plan: Job ID Type Handling in Schema (Updated)

## Overview
This updated plan addresses MongoDB compatibility issues by using string type with explicit UUID validation for the JobSchema `id` field. This ensures both database compatibility and type safety.

## Current Implementation
- Database model (`Job` class):
  ```python
  id: str = Column(String, primary_key=True, default=lambda: str(uuid4()))
  ```
- Previous Pydantic schema (with UUID type):
  ```python
  id: UUID  # Using UUID type for validation while database stores string representation
  ```

## Revised Implementation Steps

### 1. Update the Pydantic Schema
- Modify `app/schemas/job.py` to:
  - Import field_validator from pydantic
  - Use str type for id field
  - Add UUID format validation

```python
from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime
import re

class JobSchema(BaseModel):
    id: str  # Changed to str type for MongoDB compatibility while maintaining UUID validation
    
    @field_validator('id')
    @classmethod
    def validate_uuid_format(cls, v):
        # Validate that the string is in UUID format
        uuid_pattern = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.I)
        if not uuid_pattern.match(v):
            raise ValueError('id must be a valid UUID string format')
        return v
    
    # other fields remain unchanged
    
    class Config:
        from_attributes = True
```

### 2. Test Data Validation and Serialization
- Ensure Pydantic correctly:
  - Validates incoming string UUIDs (rejecting invalid formats)
  - Maintains the string format throughout processing

### 3. Review Database Compatibility
- This approach is compatible with both SQL and MongoDB databases
- String representation is universally supported
- Validation ensures data integrity

### 4. Maintain Type Safety
- Field validator ensures only properly formatted UUIDs are accepted
- Validation occurs at the schema level instead of the type level
- Proper error messages are provided for invalid formats

### 5. Code Style Update
- Updated comment explains the rationale behind the string type with validation

## Testing Approach
1. Unit tests for schema validation (test_schema_changes.py)
2. Integration tests for database interactions with MongoDB
3. End-to-end API tests to verify proper handling

## Implementation Notes
- This approach is a practical compromise that ensures both database compatibility and type safety
- No database migration is required
- No API response format changes will occur
- MongoDB compatibility is maintained while ensuring data integrity