# Audit Report Templates

## General Audit Report

```markdown
## Audit Report

**Period:** <start_date> to <end_date>
**Scope:** <account / org / project>
**Generated:** <current_date>

### Summary

| Metric | Count |
|--------|-------|
| Total Events | <n> |
| Unique Users | <n> |
| Resources Modified | <n> |
| Pipelines Executed | <n> |

### Activity by Category

| Category | Events | % of Total |
|----------|--------|------------|
| Pipeline Executions | <n> | <pct> |
| Resource Updates | <n> | <pct> |
| Resource Creates | <n> | <pct> |
| Resource Deletes | <n> | <pct> |
| Access Events | <n> | <pct> |

### Top Users by Activity

| User | Events | Primary Activity |
|------|--------|-----------------|
| <user> | <n> | <category> |

### Critical Changes

| Date | User | Action | Resource | Details |
|------|------|--------|----------|---------|
| <date> | <user> | <action> | <resource> | <detail> |
```

## User Activity Report

```markdown
## User Activity Report

**User:** <user_id>
**Period:** <date_range>

### Activity Summary

| Metric | Value |
|--------|-------|
| Total Actions | <n> |
| Pipelines Modified | <n> |
| Deployments Triggered | <n> |
| Secrets Accessed | <n> |

### Actions by Type

| Action | Count |
|--------|-------|
| Execute Pipeline | <n> |
| Update Pipeline | <n> |
| View Resources | <n> |
| Access Secrets | <n> |

### Notable Actions

| Date | Time | Action | Resource | Notes |
|------|------|--------|----------|-------|
| <date> | <time> | <action> | <resource> | <notes> |
```

## Security Audit Report

```markdown
## Security Audit Report

**Period:** <date_range>
**Focus:** Access Control & Secrets
**Classification:** Confidential

### Authentication Events

| Event Type | Count | Status |
|------------|-------|--------|
| Successful Logins | <n> | Normal / Review |
| Failed Logins | <n> | Normal / Review |
| API Key Usage | <n> | Normal / Review |

### Secret Access Audit

| Secret | Access Count | Users | Last Access |
|--------|--------------|-------|-------------|
| <secret> | <n> | <n> | <time> |

### Privileged Actions

| Date | User | Action | Details |
|------|------|--------|---------|
| <date> | <user> | <action> | <detail> |

### Access Pattern Anomalies

List any unusual patterns: off-hours access, new IP addresses, privilege changes.
```

## Compliance Framework Mapping

### SOC 2

| Control | Relevant Audit Events |
|---------|----------------------|
| CC6.1 - Logical Access | LOGIN, LOGOUT, ACCESS |
| CC6.2 - Access Authorization | ROLE assignment, approval events |
| CC6.3 - Access Removal | DELETE user, revoke role |
| CC7.1 - Change Management | CREATE, UPDATE, DELETE on pipelines/resources |
| CC7.2 - System Monitoring | EXECUTE, all event logging |

### GDPR

| Requirement | Relevant Audit Events |
|-------------|----------------------|
| Access Logging | All ACCESS events |
| Data Processing | EXECUTE pipeline events |
| Right to Audit | Complete audit trail |

### HIPAA

| Control | Relevant Audit Events |
|---------|----------------------|
| Access Controls | LOGIN, LOGOUT, ACCESS |
| Audit Controls | All event types |
| Integrity Controls | UPDATE, DELETE events |
