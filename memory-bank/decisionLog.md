## 2026-02-26 - Job ID Type Change from String to UUID

**Context:** Currently, the `id` field in JobSchema is defined as a string even though it represents a UUID. The database model generates UUIDs but stores them as strings: `id: str = Column(String, primary_key=True, default=lambda: str(uuid4()))`. This leads to a mismatch between the actual data type (UUID) and how it's represented in the schema (string).

**Decision:** Change the JobSchema `id` field type from string to UUID to accurately reflect its nature while maintaining compatibility with the database storage.

**Rationale:**
- Using the correct data type (UUID) in the schema improves type safety and makes the API contract more accurate
- Pydantic can handle the serialization/deserialization between UUID objects and string representations automatically
- This change helps prevent errors where non-UUID strings might be incorrectly accepted as valid IDs
- The change is backward compatible as the string representation will still be the same in JSON responses

**Implementation:**
1. Update JobSchema in app/schemas/job.py to import UUID from the uuid module
2. Change the type annotation of the `id` field from `str` to `UUID`
3. No changes needed to the database model as it will continue to store the string representation

**Consequences:**
- More accurate type information in the schema
- Improved validation for UUID fields
- No breaking changes to the API as UUIDs serialize to the same string format
- Better alignment between the conceptual data model and its implementation

## 2026-02-27 - Revert Job ID Type from UUID to String with Validation

**Context:** After implementing the UUID type for the `id` field in JobSchema, we encountered compatibility issues with MongoDB, which doesn't natively support Python's UUID type. While the SQL database was handling the UUID conversion correctly, MongoDB was raising errors when processing UUID objects.

**Decision:** Change the JobSchema `id` field back to string type but add explicit validation to ensure it still adheres to the UUID format.

**Rationale:**
- MongoDB has compatibility issues with Python's UUID objects
- String representation is more universally compatible across different database systems
- We can maintain type safety by adding explicit validation via Pydantic field validators
- This approach gives us the best of both worlds: database compatibility and type validation

**Implementation:**
1. Update JobSchema in app/schemas/job.py to use `str` type for the `id` field
2. Add a Pydantic field validator to ensure the string follows UUID format
3. Tests confirm the validation works correctly and rejects non-UUID strings

**Consequences:**
- Better compatibility with MongoDB while maintaining data integrity
- Explicit validation ensures only properly formatted UUIDs are accepted
- No breaking changes to the API as the format remains the same
- Type safety is preserved through validation rather than the type system

## Template for Future Decisions

## [Date] - [Decision Topic]
**Context:** [What led to this decision point? What problem are we solving?]
**Decision:** [What was decided?]
**Rationale:** [Why was this decision made? What alternatives were considered?]
**Implementation:** [How the decision will be/was implemented]
**Consequences:** [Expected impacts, both positive and negative]