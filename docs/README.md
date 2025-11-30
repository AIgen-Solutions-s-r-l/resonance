# Matching Service Documentation Index

Welcome to the Matching Service documentation. This index provides quick access to all documentation categories.

## Quick Links

- **[Project Overview](../README.md)** - Main README with setup and usage
- **[Developer Guide](../CLAUDE.md)** - Comprehensive guide for developers and Claude Code
- **[API Documentation](api/index.md)** - API endpoints and usage
- **[Job Matcher Documentation](job_matcher/index.md)** - Core matching engine details

---

## Architecture & Decisions

### Architecture Decision Records (ADRs)
[Browse all ADRs](adr/README.md)

ADRs document significant architectural decisions made in the project.

*No ADRs yet - ADRs will appear here as architectural decisions are documented*

### High-Level Designs (HLDs)
[Browse all HLDs](hld/README.md)

HLDs provide detailed design documentation for complex features.

*No HLDs yet - HLDs will appear here as features are designed*

### Delivery Plans
[Browse all delivery plans](delivery-plan/README.md)

Planning documents for major features and initiatives.

*No delivery plans yet*

---

## Technical Documentation

### Core Systems
- **[Job Matcher](job_matcher/index.md)** - Vector-based job matching engine
- **[Redis Caching](redis_caching/architecture.md)** - Caching layer architecture
- **[Metrics & Monitoring](metrics.md)** - Observability and metrics collection
- **[Geospatial Filtering](geospatial_filtering.md)** - Location-based filtering with PostGIS

### API Documentation
- **[API Overview](api/index.md)** - All API endpoints
- **[Job Details Endpoint](api/jobs_details_endpoint.md)** - Job detail retrieval
- **[Experience Filter](api/match_endpoint_experience_filter.md)** - Experience level filtering

### Performance & Optimization
- **[Performance Optimization](performance_optimization.md)** - Performance tuning guide
- **[Pagination](pagination_limit_offset.md)** - Pagination implementation
- **[Query Optimization](query_scheme.md)** - SQL query optimization

### Database
- **[PostGIS Setup](postgis_setup.md)** - PostGIS extension configuration
- **[PostGIS Implementation](postgis_implementation.md)** - Geospatial query implementation

---

## Operations & Troubleshooting

### Investigations
[Browse all investigations](investigations/README.md)

Active bug investigations and technical analysis.

**Active:**
- *No active investigations*

**Recently Resolved:**
- *No resolved investigations yet*

### Fixes
[Browse all fixes](fixes/README.md)

Documentation of recent bug fixes.

**Recent Fixes:**
- Location filter fix (2025-10-19)
- Applied jobs filter fix (2025-10-19)

### Runbooks
[Browse all runbooks](runbooks/README.md)

Operational procedures for handling alerts and incidents.

**By Severity:**
- Critical: *No runbooks yet*
- High: *No runbooks yet*
- Medium: *No runbooks yet*
- Low: *No runbooks yet*

### Known Issues
[Browse all known issues](issues/README.md)

Tracked issues with workarounds.

*No active issues documented*

### Root Cause Analysis
[Browse all RCAs](root-cause-analysis/README.md)

In-depth analysis of major incidents.

*No RCAs yet*

---

## Feature-Specific Documentation

### Job Matching
- **[Algorithm Details](job_matcher/algorithm_details.md)** - Similarity scoring algorithms
- **[Applied Jobs Filtering](job_matcher/applied_jobs_filtering.md)** - Filter out already-applied jobs
- **[Cooled Jobs Filtering](job_matcher/cooled_jobs_filtering.md)** - Handle temporarily rejected jobs
- **[Phrase Search](job_matcher/phrase_search.md)** - Keyword matching implementation
- **[Edge Cases](job_matcher/edge_cases.md)** - Handling edge cases
- **[Technical Documentation](job_matcher/technical_documentation.md)** - Technical deep dive

### Redis Caching
- **[Architecture](redis_caching/architecture.md)** - Cache layer design
- **[Configuration](redis_caching/configuration.md)** - Cache configuration
- **[Usage Guide](redis_caching/usage_guide.md)** - How to use caching
- **[Performance](redis_caching/performance.md)** - Performance characteristics
- **[Error Handling](redis_caching/error_handling.md)** - Failure handling
- **[Monitoring](redis_caching/monitoring.md)** - Cache monitoring

---

## Documentation Standards

This documentation follows the DOCS-KEEPER protocol for maintaining synchronized, high-quality documentation. Key principles:

- **Keep documentation synchronized** with code changes
- **Use structured templates** for consistency
- **Track decisions** through ADRs
- **Document incidents** for learning
- **Maintain indexes** for discoverability

### File Naming Conventions

- ADRs: `{NNN}-{kebab-case-title}.md`
- HLDs: `{feature-name}-v{X.Y}.md`
- Investigations: `{issue-description}-{YYYY-MM}.md`
- Fixes: `{issue-name}-fix-{YYYYMMDD}.md`
- Runbooks: `{alert-or-scenario-kebab-case}.md`
- Delivery Plans: `{feature-name}-delivery-plan-v{X.Y}.md`

---

## Contributing to Documentation

When contributing code changes, please update relevant documentation:

1. **API changes**: Update API documentation in `docs/api/`
2. **Architecture changes**: Create or update ADR in `docs/adr/`
3. **New features**: Consider creating HLD in `docs/hld/`
4. **Bug fixes**: Document in `docs/fixes/`
5. **Configuration changes**: Update CLAUDE.md

For questions about documentation, refer to the DOCS-KEEPER protocol in `dev-prompts/DOCS-KEEPER-PROTO.yaml`.

---

**Last Updated**: 2025-10-19
