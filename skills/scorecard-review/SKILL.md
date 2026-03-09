---
name: scorecard-review
description: Review service maturity scorecards and compliance using Harness IDP via MCP. Check production readiness, security, and documentation scores. Use when user says "scorecard", "service maturity", "production readiness", "compliance score", or asks about service health scores.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Scorecard Review

Review service maturity and compliance scorecards using Harness Internal Developer Portal (IDP) via MCP.

## Instructions

### Step 1: List Catalog Entities

```
Call MCP tool: harness_list
Parameters:
  resource_type: "idp_entity"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Get Entity Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "idp_entity"
  resource_id: "<entity_id>"
```

### Step 3: Get Scorecard Scores

```
Call MCP tool: harness_list
Parameters:
  resource_type: "idp_score"
  org_id: "<organization>"
  project_id: "<project>"
```

Get specific entity score:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "idp_score"
  resource_id: "<entity_id>"
```

### Step 4: Check Documentation

```
Call MCP tool: harness_list
Parameters:
  resource_type: "idp_tech_doc"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 5: Review Workflows

```
Call MCP tool: harness_list
Parameters:
  resource_type: "idp_workflow"
  org_id: "<organization>"
  project_id: "<project>"
```

## Common Scorecard Categories

- **Production Readiness** - CI/CD, monitoring, alerting, runbooks
- **Security Compliance** - Vulnerability scanning, secrets management, access control
- **Documentation** - API docs, architecture diagrams, runbooks
- **Operational Excellence** - SLOs, incident response, on-call
- **Developer Experience** - Build times, test coverage, onboarding

## Report Format

```
## Service Scorecard Report

**Service:** <name>
**Overall Score:** X/100

### Category Scores
| Category | Score | Status |
|----------|-------|--------|
| Production Readiness | 85/100 | Pass |
| Security | 70/100 | Needs Work |
| Documentation | 45/100 | Failing |
| Operations | 90/100 | Pass |

### Failing Checks
1. Missing API documentation
2. No SBOM generation configured
3. Test coverage below 80%

### Improvement Actions
1. Add API docs to /docs endpoint
2. Enable SBOM in CI pipeline
3. Increase test coverage to 80%+
```

## IDP Resource Types

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `idp_entity` | list, get | Catalog entities |
| `idp_score` | list, get | Scorecard scores |
| `idp_tech_doc` | list, get | Technical docs |
| `idp_workflow` | list, get | IDP workflows |

## Examples

- "How is api-gateway doing on scorecards?" - Get idp_score for entity
- "Which services are failing production readiness?" - List idp_score, filter by failing
- "Help me improve checkout-service score" - Get score, identify failing checks, suggest fixes
- "Show all services below 80% compliance" - List and filter idp_score

## Troubleshooting

### No Scores Available
- Verify scorecards are configured in IDP settings
- Check entity is registered in the catalog
- Ensure data sources (CI/CD, monitoring) are connected

### Scores Not Updating
- Check integration sync status
- Verify data source connectivity
- Review scorecard rule configuration
