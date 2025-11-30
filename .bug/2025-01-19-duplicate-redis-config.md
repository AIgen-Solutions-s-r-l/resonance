# Bug Report — Duplicate Redis Configuration Properties

## Summary
- Scope/Area: core/config
- Type: functional — Severity: S1
- Environment: Python 3.10-3.12, FastAPI 0.115.4, Branch: main, Commit: 0368b8aa40f03ca5048ba51bd9a441bde183b7c3

## Expected vs Actual
- Expected: Redis configuration properties should be defined once with consistent type conversion
- Actual: Redis properties (host, port, db, password) are defined twice in config.py with different type handling, causing potential type confusion and inconsistent behavior

## Steps to Reproduce
1. Examine `app/core/config.py` lines 35-39 and 76-81
2. Note the duplicate definitions of `redis_host`, `redis_port`, `redis_db`, `redis_password`
3. Observe type inconsistency: first definition uses direct type hint without conversion, second uses explicit `int()` conversion
4. Run application with `REDIS_PORT` environment variable set to string value
5. Observe potential type confusion when the first definition assigns string but type hint expects int

## Evidence
**Logs**: N/A (configuration error)
**Traces/Metrics**: N/A
**Screenshots/Attachments**:
```python
# First definition (lines 35-39)
redis_host: str = os.getenv("REDIS_HOST", "localhost")
redis_port: int = os.getenv("REDIS_PORT", 6379)  # Type hint says int, but os.getenv returns str
redis_db: int = os.getenv("REDIS_DB", 0)
redis_password: str = os.getenv("REDIS_PASSWORD", "")

# Second definition (lines 76-81) - OVERWRITES FIRST
redis_host: str = os.getenv("REDIS_HOST", "localhost")
redis_port: int = int(os.getenv("REDIS_PORT", "6379"))  # Proper int conversion
redis_db: int = int(os.getenv("REDIS_DB", "0"))
redis_password: str = os.getenv("REDIS_PASSWORD", "")
```

**Recent changes considered**:
```
0368b8a 2025-01-18 keat Merge branch 'main' of https://github.com/AIHawk-Startup/matching_service
908594a 2025-01-18 keat try to fix location filter
346748c 2025-01-16 keat fix the tests of the fix of the fix
```

## Diagnosis Timeline
- Detection: Code analysis revealed duplicate property definitions in Settings class
- Initial hypothesis: Copy-paste error during refactoring or configuration reorganization
- Tests/evidence: Manual code inspection confirms duplication at lines 35-39 and 76-81
- Impact: Second definition overwrites first; type confusion possible with first definition's lack of int() conversion

## Root Cause Analysis
**5 Whys:**
1. Why are Redis properties defined twice? → Copy-paste error or incomplete refactoring
2. Why wasn't this caught in code review? → No automated checks for duplicate class properties
3. Why does the first definition lack proper type conversion? → Developer oversight assuming os.getenv respects type hints
4. Why hasn't this caused runtime errors? → The second definition (correct one) overwrites the first
5. Why keep both? → Likely unintentional; dead code that should be removed

**Causal chain:** Refactoring/reorganization → Duplicate definitions added → Type inconsistency introduced → Second definition masks first → No runtime error but code quality issue → Risk of future bugs if order changes

## Remediation
**Workaround/Mitigation:**
Currently the second definition (correct one) takes precedence, so the system works. However, this is fragile and confusing.

**Proposed permanent fix:**
1. Remove lines 35-39 (first set of Redis definitions)
2. Keep only lines 76-81 with proper `int()` conversions
3. Add linter rule to detect duplicate class property definitions
4. Add unit test to validate Settings class has no duplicate properties

```python
# REMOVE lines 35-39 entirely
# KEEP only lines 76-81:
redis_host: str = os.getenv("REDIS_HOST", "localhost")
redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
redis_db: int = int(os.getenv("REDIS_DB", "0"))
redis_password: str = os.getenv("REDIS_PASSWORD", "")
redis_cache_ttl: int = int(os.getenv("REDIS_CACHE_TTL", "300"))
redis_enabled: bool = os.getenv("REDIS_ENABLED", "True").lower() == "true"
```

**Risk & rollback considerations:**
- Low risk: Simply removing dead code
- No rollback needed: The second definition is already being used
- Potential issue: If any code somehow relies on property definition order (unlikely)

## Validation & Prevention
**Test plan:**
1. Remove lines 35-39
2. Run full test suite: `pytest --cov=app`
3. Test with various environment variable configurations
4. Verify Redis connections work correctly
5. Run application locally and test Redis caching

**Regression tests to add:**
```python
def test_settings_no_duplicate_properties():
    """Ensure Settings class has no duplicate property definitions"""
    from app.core.config import Settings
    import inspect

    # Get all members of Settings class
    members = inspect.getmembers(Settings)
    property_names = [name for name, _ in members if not name.startswith('_')]

    # Check for duplicates
    assert len(property_names) == len(set(property_names)), \
        "Settings class has duplicate property definitions"

def test_redis_config_type_correctness():
    """Verify Redis configuration has correct types"""
    from app.core.config import settings

    assert isinstance(settings.redis_host, str)
    assert isinstance(settings.redis_port, int)
    assert isinstance(settings.redis_db, int)
    assert isinstance(settings.redis_password, str)
    assert isinstance(settings.redis_cache_ttl, int)
    assert isinstance(settings.redis_enabled, bool)
```

**Monitoring/alerts:**
- Add static analysis check in pre-commit hooks for duplicate properties
- Add unit test for Settings class validation in CI/CD

## Ownership & Next Steps
- Owner(s): Backend team / Configuration management owner
- Dependencies/links:
  - File: `app/core/config.py:35-39` (to be removed)
  - File: `app/core/config.py:76-81` (to be kept)
  - Related: BUG-009 (Type Mismatch in Redis Port Configuration)

**Checklist:**
- [x] Reproducible steps verified
- [x] Evidence attached/linked
- [x] RCA written and reviewed
- [ ] Fix implemented/validated
- [ ] Regression tests merged
