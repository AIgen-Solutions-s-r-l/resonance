# Runbook: {Alert/Scenario Name}

## Alert Description

{What this alert means}

## Severity

{Critical|High|Medium|Low}

## Impact

{Impact on users/system}

What happens if this alert fires? Who is affected?

## Dashboard

- Grafana: {dashboard URL}
- Metrics: {specific metrics to check}
- Logs: {log dashboard URL}

## Investigation Steps

**1. Check system health**
```bash
curl http://localhost:8002/health
curl http://localhost:8002/health/db
curl http://localhost:8002/health/mongodb
```

**2. Review application logs**
```bash
# Check recent errors
docker logs matching-service --tail 100 | grep ERROR

# Check specific timeframe
docker logs matching-service --since "2024-10-19T10:00:00"
```

**3. Check database connectivity**
```bash
# PostgreSQL
psql -h localhost -U user -d dbname -c "SELECT version();"

# MongoDB
mongosh --eval "db.adminCommand({ ping: 1 })"
```

**4. Review metrics**
- CPU usage: {where to check}
- Memory usage: {where to check}
- Request rate: {where to check}
- Error rate: {where to check}

## Common Causes

### Cause 1: {Description}
**Symptoms:** {How to identify}
**Fix:** {Resolution}

### Cause 2: {Description}
**Symptoms:** {How to identify}
**Fix:** {Resolution}

## Resolution Steps

### Immediate Actions

**1. {Action 1}**
```bash
{command or procedure}
```

**2. {Action 2}**
```bash
{command or procedure}
```

**3. Verify resolution**
```bash
{verification command}
```

### Long-term Fix

**1. {Long-term action 1}**
- {Details}

**2. {Long-term action 2}**
- {Details}

## Escalation

**After 15 minutes:**
- {Escalation path}
- Contact: {team/person}

**After 30 minutes:**
- {Further escalation}
- Contact: {senior engineer/manager}

**Emergency Contacts:**
- On-call engineer: {contact method}
- Team lead: {contact method}
- Engineering manager: {contact method}

## Prevention

{Preventive measures to avoid this issue}

- {Prevention 1}
- {Prevention 2}
- {Prevention 3}

## Related

- **Similar incidents:**
  - {link to RCA or investigation}

- **Related runbooks:**
  - {link to related runbook}

- **Documentation:**
  - {link to relevant docs}

## Notes

{Additional context, historical information, or tips}
