---
name: security-report
description: Generate security compliance reports using Harness SCS and STO via MCP. Analyze vulnerabilities, SBOMs, and manage exemptions. Use when user says "security report", "vulnerabilities", "SBOM", "security scan", "compliance check", or asks about application security.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Security Report

Generate security compliance reports using Harness Software Supply Chain (SCS) and Security Testing Orchestration (STO) via MCP.

## Instructions

### Step 1: List Vulnerabilities

```
Call MCP tool: harness_list
Parameters:
  resource_type: "security_issue"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Get Vulnerability Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "security_issue"
  resource_id: "<issue_id>"
```

### Step 3: List SBOMs

```
Call MCP tool: harness_list
Parameters:
  resource_type: "scs_sbom"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 4: Get SBOM Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "scs_sbom"
  resource_id: "<sbom_id>"
```

### Step 5: Check Artifact Components

```
Call MCP tool: harness_list
Parameters:
  resource_type: "scs_artifact_component"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 6: Get Remediation Guidance

```
Call MCP tool: harness_list
Parameters:
  resource_type: "scs_artifact_remediation"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 7: Check Compliance

```
Call MCP tool: harness_list
Parameters:
  resource_type: "scs_compliance_result"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 8: Manage Exemptions

List existing exemptions:
```
Call MCP tool: harness_list
Parameters:
  resource_type: "security_exemption"
  org_id: "<organization>"
  project_id: "<project>"
```

Create an exemption:
```
Call MCP tool: harness_create
Parameters:
  resource_type: "security_exemption"
  org_id: "<organization>"
  project_id: "<project>"
  body: <exemption details>
```

Approve or revoke an exemption:
```
Call MCP tool: harness_execute
Parameters:
  resource_type: "security_exemption"
  action: "approve"    # or "revoke"
  resource_id: "<exemption_id>"
```

## Report Format

```
## Security Compliance Report

**Date:** <date>
**Scope:** <project/artifact>

### Vulnerability Summary
| Severity | Count | New | Fixed |
|----------|-------|-----|-------|
| Critical | X     | X   | X     |
| High     | X     | X   | X     |
| Medium   | X     | X   | X     |
| Low      | X     | X   | X     |

### Top Critical Vulnerabilities
1. **CVE-XXXX-XXXXX** - <description> (Package: <name>)
   - Remediation: Upgrade to version X.Y.Z

### SBOM Status
- Artifacts with SBOMs: X/Y
- Compliance checks passing: X/Y

### Active Exemptions
- X exemptions active, Y pending review

### Recommendations
1. <prioritized fix action>
2. <next fix action>
```

## Security Resource Types

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `security_issue` | list, get | Vulnerabilities from scans |
| `security_exemption` | list, get, create, update | Exemption management |
| `scs_sbom` | list, get | Software Bill of Materials |
| `scs_artifact_component` | list | Components in artifacts |
| `scs_artifact_remediation` | list | Fix recommendations |
| `scs_compliance_result` | list | Policy compliance results |
| `scs_opa_policy` | list | OPA policy status |

## Examples

- "Generate security report for backend-service" - List security_issue filtered by service
- "Show critical vulnerabilities" - List security_issue, filter by severity
- "Download SBOM for api-service:v2.3" - Get scs_sbom by artifact
- "Create exemption for CVE-2024-1234" - Create security_exemption

## Troubleshooting

### No Vulnerabilities Shown
- Verify STO scans are configured in pipelines
- Check scan tool connectors (Snyk, Aqua, etc.)
- Ensure scan results are being ingested

### SBOM Not Available
- Verify SBOM generation is enabled in CI pipeline
- Check artifact registry configuration
