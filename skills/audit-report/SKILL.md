---
name: audit-report
description: >-
  Generate audit reports and compliance trails using Harness audit trail data via MCP v2 tools.
  Track user actions, resource changes, authentication events, and access patterns across accounts,
  organizations, and projects. Use when asked to audit activity, generate compliance reports,
  investigate security incidents, review user actions, check change logs, or produce SOC2/GDPR/HIPAA
  audit evidence. Trigger phrases: audit report, audit trail, compliance audit, user activity log,
  change log, access audit, security investigation, who changed what, audit events.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Audit Report Skill

Generate audit reports and compliance trails using Harness MCP v2 tools.

## MCP v2 Tools Used

- `harness_list` with `resource_type: "audit_event"` -- list audit events with filters
- `harness_describe` with `resource_type: "audit_event"` -- discover available filters and fields

Audit events are **read-only**. You can list and filter them but cannot create, update, or delete them.

## Instructions

### Step 1: Discover Available Filters

```
harness_describe(resource_type="audit_event")
```

Understand the available filter parameters before querying.

### Step 2: List Audit Events

```
harness_list(
  resource_type="audit_event",
  org_id="<org>",           # optional - scope to organization
  project_id="<project>",   # optional - scope to project
  search_term="<user or resource>",  # optional
  page=0,
  size=100
)
```

### Step 3: Filter by Action Type

Filter results by these standard action types:

| Action | Description |
|--------|-------------|
| `CREATE` | Resource creation |
| `UPDATE` | Resource modification |
| `DELETE` | Resource deletion |
| `LOGIN` | User authentication |
| `LOGOUT` | Session termination |
| `ACCESS` | Resource access |
| `EXECUTE` | Pipeline execution |

### Step 4: Filter by Resource Type

Common resource types in audit events:

| Resource Type | Examples |
|---------------|----------|
| `PIPELINE` | Pipeline create, update, delete |
| `SECRET` | Secret access, rotation, deletion |
| `CONNECTOR` | Connector modifications |
| `SERVICE` | Service definition changes |
| `ENVIRONMENT` | Environment configuration changes |
| `USER` | User management actions |
| `ROLE` | Role assignment changes |
| `USER_GROUP` | Group membership changes |

### Step 5: Analyze and Correlate

- Group events by user to identify activity patterns
- Group events by resource to track change history
- Correlate timestamps to reconstruct incident timelines
- Flag anomalies (off-hours activity, unusual access patterns, privilege escalation)

### Step 6: Generate Report

Format findings using the templates in references/report-templates.md.

For report templates (General, User Activity, Security) and compliance framework mappings (SOC 2, GDPR, HIPAA), consult references/report-templates.md.

## Examples

### Generate a 30-day audit report

```
/audit-report
Generate an audit report for the last 30 days
```

### Investigate a specific user

```
/audit-report
What has john.doe@company.com been doing in the last 7 days?
```

### Track production changes

```
/audit-report
Show all pipeline and environment changes in the production project this month
```

### Security investigation

```
/audit-report
Show all secret access events and privilege changes from last week
```

### Compliance evidence

```
/audit-report
Generate SOC2 audit evidence for Q4 covering access control and change management
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| No audit events returned | Time range too narrow or wrong scope | Broaden time range; verify org_id/project_id |
| Access denied | User lacks audit view permissions | Request `core_audit_view` permission |
| Pagination incomplete | More events than page size | Increment `page` parameter until all pages fetched |
| Search term returns nothing | User ID format mismatch | Try email, username, and display name variants |

## Performance Notes

- Paginate through all results before generating the report. Incomplete data leads to inaccurate audit trails.
- Cross-reference events across scopes (account, org, project) for a complete picture. Do not skip scope levels.
- For compliance reports, verify every claim against actual audit data. Do not infer or assume activity that is not in the logs.

## Troubleshooting

### No Events Found

1. Start with a broader time range and no filters
2. Verify the org_id and project_id scope -- account-level events require no org/project filter
3. Remove search_term to confirm events exist, then re-add filters

### Missing User Activity

1. Check both email and username formats for the user
2. Service account activity may appear under a different principal name
3. API key usage may not show as the human user

### Incomplete Audit Trail

1. Paginate through all results -- check if `size` returned equals the `size` requested (more pages likely)
2. Account-level events are separate from org/project events -- query at the right scope
3. Some event types may require specific permissions to view
