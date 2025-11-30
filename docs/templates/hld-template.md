# High-Level Design: {Feature Name} v{Version}

Date: {YYYY-MM-DD}
Status: {Draft|Review|Approved|Implemented}
Authors: {Names}

## Executive Summary

{1-2 paragraph overview of the feature and its business value}

## Goals and Non-Goals

### Goals
- {Goal 1}
- {Goal 2}
- {Goal 3}

### Non-Goals
- {Non-goal 1}
- {Non-goal 2}

## Architecture

### System Context

{C4 Context diagram or description. How does this feature fit into the larger system?}

### Components

{Key components and their responsibilities}

**Component 1: {Name}**
- Responsibility: {what it does}
- Interfaces: {APIs, events}
- Dependencies: {what it depends on}

**Component 2: {Name}**
- Responsibility: {what it does}
- Interfaces: {APIs, events}
- Dependencies: {what it depends on}

### Data Model

{Database schema changes, data structures, data flows}

```sql
-- Example schema changes
```

### API Design

{Endpoints, request/response formats}

**Endpoint: POST /api/{resource}**
```json
{
  "request": "example"
}
```

Response:
```json
{
  "response": "example"
}
```

## Implementation Plan

### Phases

**Phase 1: {Name}**
- {Task 1}
- {Task 2}

**Phase 2: {Name}**
- {Task 1}
- {Task 2}

### Dependencies
- {Dependency 1}
- {Dependency 2}

### Timeline

| Phase | Start Date | End Date | Deliverables |
|-------|-----------|----------|--------------|
| Phase 1 | {date} | {date} | {deliverable} |
| Phase 2 | {date} | {date} | {deliverable} |

## Testing Strategy

{Test approach, coverage requirements}

**Unit Tests:**
- {Test area 1}
- {Test area 2}

**Integration Tests:**
- {Test scenario 1}
- {Test scenario 2}

**Coverage Target:** {X%}

## Monitoring and Observability

{Metrics, logs, alerts, dashboards}

**Metrics:**
- {Metric 1}: {description}
- {Metric 2}: {description}

**Alerts:**
- {Alert 1}: {threshold and severity}
- {Alert 2}: {threshold and severity}

## Security Considerations

{Security analysis, threat model}

**Threats:**
- {Threat 1}: {mitigation}
- {Threat 2}: {mitigation}

**Authentication/Authorization:**
- {How is access controlled?}

## Performance Considerations

{Performance requirements, optimization strategies}

**Requirements:**
- Response time: {target}
- Throughput: {target}
- Scalability: {target}

**Optimizations:**
- {Optimization 1}
- {Optimization 2}

## Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| {Risk 1} | High/Med/Low | High/Med/Low | {Strategy} |
| {Risk 2} | High/Med/Low | High/Med/Low | {Strategy} |

## Open Questions

- [ ] {Question 1}
- [ ] {Question 2}
- [ ] {Question 3}

## References

- {Link to related docs}
- {Link to external resources}
- {Link to similar implementations}
