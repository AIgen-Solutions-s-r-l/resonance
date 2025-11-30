# Bug Report — Secret Key Exposure in Security Logs

## Summary
- Scope/Area: core/security
- Type: security — Severity: S1
- Environment: Python 3.10-3.12, Branch: main, Commit: 0368b8aa40f03ca5048ba51bd9a441bde183b7c3

## Expected vs Actual
- Expected: JWT tokens and secret keys should never be logged, even partially
- Actual: JWT verification logs unverified payload and partial secret key, risking exposure of sensitive data

## Steps to Reproduce
1. Make authenticated request to any protected endpoint
2. Check application logs
3. Observe log entries containing:
   - Unverified JWT payload (may contain PII)
   - Partial secret key preview (`secret_preview`)
4. If logs are compromised, attacker gains sensitive information

## Evidence
**Code from app/core/security.py:79-93:**
```python
# Log decoding parameters (partial secret key for security)
secret_preview = settings.secret_key[:3] + "..." if settings.secret_key else "None"

# Try to decode without verification first to see payload
try:
    unverified_payload = jwt.decode(
        token,
        settings.secret_key,
        options={"verify_signature": False}
    )
    logger.info(f"Token payload (unverified): {unverified_payload}")  # SECURITY RISK!
except Exception as e:
    logger.error(f"Error decoding token: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

**Example log output (security risk):**
```
INFO Token payload (unverified): {'user_id': 12345, 'email': 'user@example.com', 'exp': 1737316800}
INFO Decoding JWT token with algorithm HS256, secret_preview: abc...
```

## Root Cause Analysis
**5 Whys:**
1. Why is payload logged? → Debug logging left in production code
2. Why log unverified payload? → Developer trying to troubleshoot token issues
3. Why show secret key preview? → Misguided attempt at "partial masking" for security
4. Why not caught in review? → No security-focused code review process
5. Why deployed to production? → No secret scanning in CI/CD pipeline

**Causal chain:** Debug code added for troubleshooting → Logging sensitive data → Not removed before production → No automated secret detection → Logs may contain PII and partial secrets → If logs compromised, attacker gains information

## Remediation
**Workaround/Mitigation:**
IMMEDIATE:
1. Rotate JWT secret key in production environments
2. Audit logs for exposure, consider them compromised
3. Implement log scrubbing/filtering if available
4. Restrict log access to authorized personnel only

**Proposed permanent fix:**
Remove all sensitive logging from production code:

```python
def verify_jwt_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify a JWT token and return its payload.
    Raises HTTPException if token is invalid or expired.
    """
    try:
        # Decode and verify token (no logging of payloads or secrets)
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm]
        )

        # Only log non-sensitive information
        if settings.debug:
            logger.debug("JWT token successfully verified")

        return payload

    except ExpiredSignatureError:
        logger.warning("JWT token has expired")  # OK to log - no sensitive data
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"JWT verification failed: {type(e).__name__}")  # Only log error type
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

Additionally:
1. Add secret scanning to pre-commit hooks (e.g., detect-secrets)
2. Implement log sanitization library
3. Use structured logging with field-level redaction
4. Never log: passwords, tokens, API keys, even partially

**Risk & rollback considerations:**
- Low technical risk: Just removing log statements
- HIGH security risk if not fixed
- Requires secret key rotation in production
- May impact debugging - use proper observability tools instead

## Validation & Prevention
**Test plan:**
1. Remove sensitive logging
2. Rotate production secrets
3. Verify logs contain no sensitive information
4. Test that debugging still works without exposing secrets
5. Add secret scanning to CI/CD
6. Audit all other logging for similar issues

**Regression tests:**
```python
def test_jwt_verification_does_not_log_secrets(caplog):
    """Verify JWT verification doesn't log sensitive data"""
    import logging
    from app.core.security import verify_jwt_token
    from app.core.config import settings

    caplog.set_level(logging.DEBUG)

    # Create test token
    token = create_access_token({"user_id": 123})

    # Verify token
    payload = verify_jwt_token(token)

    # Check logs don't contain sensitive data
    log_text = caplog.text.lower()
    assert settings.secret_key.lower() not in log_text
    assert "secret" not in log_text or "secret_key" not in log_text
    assert str(payload) not in log_text  # Payload not logged

def test_logs_do_not_contain_secrets_pattern():
    """Security test: scan all log statements for secret patterns"""
    import ast
    import os
    from pathlib import Path

    # Patterns that should never be logged
    forbidden_patterns = [
        "secret_key",
        "SECRET_KEY",
        "api_key",
        "password",
        "token",  # Be careful with this one
    ]

    violations = []
    for py_file in Path("app").rglob("*.py"):
        with open(py_file) as f:
            try:
                tree = ast.parse(f.read())
                for node in ast.walk(tree):
                    if isinstance(node, ast.Call):
                        if hasattr(node.func, 'attr') and 'log' in node.func.attr.lower():
                            # Check arguments for forbidden patterns
                            for arg in node.args:
                                if isinstance(arg, ast.JoinedStr):  # f-string
                                    for value in arg.values:
                                        if hasattr(value, 's'):
                                            for pattern in forbidden_patterns:
                                                if pattern in str(value.s).lower():
                                                    violations.append(f"{py_file}:{node.lineno}")
            except SyntaxError:
                pass

    assert len(violations) == 0, f"Found secret logging violations: {violations}"
```

**Monitoring/alerts:**
- Add secret scanning to CI/CD (GitHub Secret Scanning, GitGuardian, detect-secrets)
- Implement log monitoring for accidental secret exposure
- Regular security audits of logging statements
- Use structured logging with automatic PII redaction

## Ownership & Next Steps
- Owner(s): Security team + Backend team
- Dependencies/links:
  - File: `app/core/security.py:79-93` (URGENT FIX NEEDED)
  - All logging statements across codebase need audit
  - Production secret rotation required

**Checklist:**
- [x] Reproducible steps verified
- [x] Evidence attached/linked
- [x] RCA written and reviewed
- [ ] URGENT: Fix implemented/validated
- [ ] URGENT: Production secrets rotated
- [ ] URGENT: Logs audited for exposure
- [ ] Secret scanning added to CI/CD
- [ ] Security audit of all logging completed
