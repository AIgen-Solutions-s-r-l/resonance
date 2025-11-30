# Bug Report — Unprotected Cron Endpoint Without Authentication

## Summary
- Scope/Area: api/cron
- Type: security — Severity: S1
- Environment: FastAPI 0.115.4, MongoDB, Branch: main, Commit: 0368b8aa40f03ca5048ba51bd9a441bde183b7c3

## Expected vs Actual
- Expected: Administrative endpoints like `/clean_requests` should require authentication
- Actual: The endpoint has no authentication or authorization checks, allowing anyone to delete database records

## Steps to Reproduce
1. Start the matching service
2. Make unauthorized request: `curl -X POST http://localhost:8000/clean_requests`
3. Observe that request succeeds without any credentials
4. Check MongoDB `requests` collection - records older than 30 days are deleted
5. Repeat maliciously to cause DoS or data loss

## Evidence
**Code from app/routers/cronrouters.py:8-16:**
```python
@router.post("/clean_requests")
async def clean_request_records():  # NO AUTH DEPENDENCY!
    limit = datetime.now() - timedelta(days=30)
    metrics_collection = database.get_collection("requests")
    result = await metrics_collection.delete_many({
        "time": {"$lt": limit}
    })
    return {"result": "success", "deleted": result.deleted_count}
```

**Comparison with protected endpoints:**
```python
# From jobs_matched_router_async.py - PROPERLY PROTECTED
@router.get("/jobs/match")
async def get_matched_jobs(
    _: bool = Depends(verify_api_key),  # ✓ Authentication required
    current_user: User = Depends(get_current_user),  # ✓ User validation
    ...
):
```

## Root Cause Analysis
**5 Whys:**
1. Why is the endpoint unprotected? → Developer forgot to add authentication dependency
2. Why wasn't this caught in review? → No security checklist for new endpoints
3. Why no automated security testing? → Missing security scan in CI/CD pipeline
4. Why is authentication optional in design? → FastAPI dependencies are optional by default
5. Why deployed to production unprotected? → No security audit before deployment

**Causal chain:** New cron endpoint created → Authentication dependency not added → Code review missed security issue → No automated security testing → Deployed to production → Vulnerability exploitable by anyone

## Remediation
**Workaround/Mitigation:**
IMMEDIATE: Block this endpoint at the network/firewall level until authentication is added:
- Add firewall rule to block external access to `/clean_requests`
- Restrict to internal IP ranges only
- Or disable the route entirely in production

**Proposed permanent fix:**
Add authentication requirement using the existing `verify_api_key` dependency:

```python
from app.core.auth import verify_api_key

@router.post("/clean_requests")
async def clean_request_records(
    _: bool = Depends(verify_api_key)  # ADD THIS
):
    """Clean old request records. Requires internal API key authentication."""
    limit = datetime.now() - timedelta(days=30)
    metrics_collection = database.get_collection("requests")
    result = await metrics_collection.delete_many({
        "time": {"$lt": limit}
    })
    logger.info(f"Cleaned {result.deleted_count} old request records")
    return {"result": "success", "deleted": result.deleted_count}
```

Additionally, consider:
1. Rate limiting to prevent DoS even with auth
2. Audit logging for all deletion operations
3. Require elevated permissions (separate from regular API key)

**Risk & rollback considerations:**
- Low risk: Simply adding authentication
- Ensure API keys are distributed to legitimate cron jobs
- If breaks existing automation, temporarily whitelist specific IPs
- Rollback: Remove dependency if needed, but FIX vulnerability first

## Validation & Prevention
**Test plan:**
1. Add authentication dependency to endpoint
2. Test that unauthenticated requests return 401/403
3. Test that authenticated requests (with valid API key) succeed
4. Verify existing cron jobs have proper credentials configured
5. Test rate limiting if implemented
6. Audit log to confirm deletion events are logged

**Regression tests:**
```python
def test_clean_requests_requires_authentication(client):
    """Verify /clean_requests endpoint requires authentication"""
    # Unauthenticated request should fail
    response = client.post("/clean_requests")
    assert response.status_code == 401 or response.status_code == 403

def test_clean_requests_with_valid_api_key(client, valid_api_key):
    """Verify /clean_requests works with valid API key"""
    headers = {"X-API-Key": valid_api_key}
    response = client.post("/clean_requests", headers=headers)
    assert response.status_code == 200
    assert "deleted" in response.json()

def test_all_endpoints_have_authentication():
    """Security test: verify all POST/DELETE/PUT endpoints require auth"""
    from app.main import app
    import inspect

    for route in app.routes:
        if hasattr(route, 'methods') and route.methods & {'POST', 'DELETE', 'PUT'}:
            # Check if endpoint has authentication dependency
            if hasattr(route, 'endpoint'):
                sig = inspect.signature(route.endpoint)
                has_auth = any(
                    'Depends' in str(param.default)
                    for param in sig.parameters.values()
                )
                assert has_auth, f"Endpoint {route.path} missing authentication!"
```

**Monitoring/alerts:**
- Log all calls to `/clean_requests` with source IP
- Alert on unauthenticated attempts (after fix)
- Monitor deletion counts for anomalies
- Add security scanning to CI/CD (e.g., Bandit, semgrep)

## Ownership & Next Steps
- Owner(s): Security team + Backend team
- Dependencies/links:
  - File: `app/routers/cronrouters.py:8-16` (URGENT FIX NEEDED)
  - Related: `app/core/auth.py` (verify_api_key function)
  - Security policy: All administrative endpoints must be authenticated

**Checklist:**
- [x] Reproducible steps verified
- [x] Evidence attached/linked
- [x] RCA written and reviewed
- [ ] URGENT: Fix implemented/validated
- [ ] URGENT: Deploy to production
- [ ] Regression tests merged
- [ ] Security audit of all other endpoints
