# Phrase Search Functionality

This document details the implementation and usage of the phrase search functionality within the job matcher service. It explains how the system now correctly handles multi-word search queries, improving the precision and relevance of search results.

## Previous Issue with Phrase Searches

Prior to the recent updates, the job matcher's keyword search functionality would split any multi-word input into individual words. For example, a search for "software engineer" would be treated as a search for "software" AND "engineer". This approach often led to less relevant results, as it would match jobs containing the individual words anywhere in the title or description, rather than the exact phrase.

## New Implementation for Phrase Integrity

The `_build_keyword_filters` method in `app/libs/job_matcher/query_builder.py` has been updated to address this issue. The method now intelligently detects whether the input is a single word, a multi-word phrase, or multiple individual keywords.

The core logic for handling phrases involves using SQL's `ILIKE` operator with wildcards (`%%`) concatenated with the exact phrase. This ensures that the generated SQL query searches for the literal phrase within the job title or description.

## Handling Different Search Scenarios

The updated `_build_keyword_filters` method handles the following scenarios:

### Single Word Search

If the input is a single word (e.g., "developer"), the system generates a filter that searches for this word in the job title or description using `ILIKE`.

**Example SQL Snippet:**

```sql
(j.title ILIKE '%%' || 'developer' || '%%' OR j.description ILIKE '%%' || 'developer' || '%%')
```

### Single Phrase Search

If the input is a single string containing spaces (e.g., "software engineer"), the system treats it as an exact phrase. A single filter clause is generated to search for this exact phrase in the job title or description.

**Example SQL Snippet:**

```sql
(j.title ILIKE '%%' || 'software engineer' || '%%' OR j.description ILIKE '%%' || 'software engineer' || '%%')
```

### Multiple Keywords Search (Potential Phrase)

If the input consists of multiple strings (e.g., ["frontend", "developer"]), the system generates filter clauses for both the combined phrase ("frontend developer") and the individual words ("frontend", "developer"). The combined phrase match is typically given higher relevance in the overall search algorithm, while the individual word matches provide broader coverage.

**Example SQL Snippet:**

```sql
(
    (j.title ILIKE '%%' || 'frontend developer' || '%%' OR j.description ILIKE '%%' || 'frontend developer' || '%%')
    OR (j.title ILIKE '%%' || 'frontend' || '%%' OR j.description ILIKE '%%' || 'frontend' || '%%')
    OR (j.title ILIKE '%%' || 'developer' || '%%' OR j.description ILIKE '%%' || 'developer' || '%%')
)
```

## Benefits of the New Approach

The updated phrase search functionality offers several key benefits:

- **Improved Precision:** By treating phrases as exact units, the search results are more precise and relevant to the user's intent.
- **Enhanced User Experience:** Users can now search using natural language phrases and expect more accurate matches.
- **Flexibility:** The system still supports searching for individual keywords while prioritizing exact phrase matches when applicable.

This enhancement significantly improves the job matching service's ability to understand and respond to complex search queries. The implementation details can be found in the `_build_keyword_filters` method within `app/libs/job_matcher/query_builder.py`.