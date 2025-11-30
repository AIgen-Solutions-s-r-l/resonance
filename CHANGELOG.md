# Changelog

All notable changes to the Matching Service will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Documentation structure following DOCS-KEEPER protocol
- Structured documentation directories (adr/, hld/, investigations/, fixes/, runbooks/, etc.)
- Master documentation index at docs/README.md
- Index files for all documentation categories
- CHANGELOG.md following Keep a Changelog format

### Changed
- Enhanced documentation organization for better discoverability

## Recent Fixes (2025-10-19)

### Fixed
- Location filter bug fixes (multiple iterations)
- Applied jobs filtering improvements
- Test fixes for location and applied jobs features

## Historical Changes

Based on recent commit history:

### 2025-10 (Recent Activity)

#### Fixed
- Location filter multiple iterations (commits: 908594a, 346748c, ec8bbd0)
- Applied jobs filtering logic (commit: 44fe31c)
- None values being converted to 99.18 in scoring (commit: 3f7763e)
- Match score handling for public search (commit: e372dbc)

#### Added
- Logo fetching scripts (commit: 0907cce)
- Logging improvements (commit: ee3ada6)
- Alembic database revision (commit: 4ec4e41)

#### Changed
- Improved rejected job model (commit: 0d9c409)
- Sort type forced to DATE when resume is None (commit: 554cfab)
- URL updates for image checking (commit: 4dca1e1)

---

## Changelog Format

Each release should include sections as applicable:

### Added
For new features.

### Changed
For changes in existing functionality.

### Deprecated
For soon-to-be removed features.

### Removed
For now removed features.

### Fixed
For any bug fixes.

### Security
In case of vulnerabilities.

---

**Note**: This changelog was initialized on 2025-10-19. Historical changes are based on git commit history. Going forward, all changes should be documented here at the time of the pull request.
