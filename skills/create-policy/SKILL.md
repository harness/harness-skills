---
name: create-policy
description: >-
  Create OPA governance policies for Harness supply chain security via MCP. Define policies that enforce
  compliance rules on artifacts, code repositories, and deployment pipelines. Use when asked to create
  a governance policy, OPA policy, compliance rule, supply chain policy, or enforce security standards.
  Trigger phrases: create policy, OPA policy, governance policy, compliance rule, supply chain governance,
  enforce policy, security policy.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Policy

Create OPA governance policies for Harness Software Supply Chain Assurance (SCS) via MCP.

## Instructions

### Step 1: Identify Policy Requirements

Determine what the policy should enforce:
- What artifact or repository standard must be met?
- What is the enforcement action (warn, deny)?
- What scope should the policy apply to?

### Step 2: Create the Policy

```
Call MCP tool: harness_create
Parameters:
  resource_type: "scs_opa_policy"
  org_id: "<organization>"
  project_id: "<project>"
  body: <policy definition>
```

### Step 3: Verify Compliance Results

After a policy is created, check compliance status on artifacts or repositories:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "scs_compliance_result"
  org_id: "<organization>"
  project_id: "<project>"
```

## Common Policy Patterns

### Require SBOM Generation

Enforce that all artifacts have an SBOM before deployment:

```rego
package harness.artifact

deny[msg] {
  not input.artifact.sbom
  msg := "Artifact must have an SBOM before deployment"
}
```

### Block Critical Vulnerabilities

Deny deployment of artifacts with critical CVEs:

```rego
package harness.artifact

deny[msg] {
  vuln := input.artifact.vulnerabilities[_]
  vuln.severity == "CRITICAL"
  msg := sprintf("Critical vulnerability %s found in artifact", [vuln.cve_id])
}
```

### Enforce Approved Base Images

Restrict container images to approved base images:

```rego
package harness.artifact

approved_bases := {"alpine", "distroless", "ubuntu"}

deny[msg] {
  not approved_bases[input.artifact.base_image]
  msg := sprintf("Base image '%s' is not in the approved list", [input.artifact.base_image])
}
```

### Require Signed Artifacts

Enforce artifact signing before deployment:

```rego
package harness.artifact

deny[msg] {
  not input.artifact.signed
  msg := "Artifact must be signed before deployment"
}
```

## Related Resource Types

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `scs_opa_policy` | create | Create governance policies |
| `scs_compliance_result` | list | Check policy compliance status |
| `artifact_security` | list, get | View artifact security posture |
| `code_repo_security` | list, get | View repository security posture |
| `scs_chain_of_custody` | get | Verify artifact provenance |

## Examples

- "Create a policy to block critical CVEs" -- Create OPA deny rule for critical severity
- "Enforce SBOM generation for all artifacts" -- Create policy requiring SBOM presence
- "Only allow approved base images" -- Create policy with allowed base image list
- "Require artifact signing before production" -- Create policy checking signature status
- "Check which artifacts violate our policies" -- List scs_compliance_result

## Performance Notes

- Validate Rego syntax before submitting. Common issues: missing package declaration, deny rules without msg return.
- Ensure the policy package name follows `package harness.<domain>` convention.
- Test policy logic mentally against expected inputs before creating.

## Troubleshooting

### Policy Not Enforcing
- Policies are create-only via MCP -- verify the policy was created successfully
- Check that the policy scope matches the target artifacts/repositories
- Use `scs_compliance_result` to verify the policy is being evaluated

### Policy Syntax Errors
- OPA policies use Rego language -- validate syntax before submitting
- Package names should follow `package harness.<domain>` convention
- Deny rules must return a `msg` string explaining the violation

### Limitations
- MCP supports create-only for OPA policies (no list, update, or delete via MCP)
- For managing existing policies, use the Harness UI under Supply Chain Assurance settings
- Policies apply within the project scope where they are created
