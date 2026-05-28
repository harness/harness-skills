---
name: pr-analysis
description: >-
  Analyze pull request impact on Harness pipelines via MCP. Assess PR pipeline impact by
  identifying which pipelines, services, and environments are affected by code changes.
  Perform security-focused PR reviews checking for secrets, vulnerabilities, and compliance.
  Track PRs from merge through deployment to production verification. Use when asked to
  analyze PR impact, review PR security, or track a PR to production. Trigger phrases:
  PR impact, pull request analysis, PR security review, PR to production, merge impact,
  deployment tracking, code change impact, PR pipeline, which pipelines affected.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# PR Analysis

Analyze pull request pipeline impact, run security-focused reviews, and track PRs from merge to production deployment.

## Instructions

### Step 1: Establish Scope

Confirm the service, repository, and PR details.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Identify the PR Analysis Task

Determine which analysis the user needs:

1. **PR Pipeline Impact Analysis** -- Which pipelines, services, and environments are affected
2. **Security-Focused PR Review** -- Check for secrets, vulnerabilities, and compliance issues
3. **PR to Production Tracker** -- Track a PR from merge through deployment and verification

### Step 3: PR Pipeline Impact Analysis

Gather from the user:
- Service name and repository
- PR description and changed components (files/directories modified)

Identify affected resources:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "trigger"
  org_id: "<organization>"
  project_id: "<project>"
```

Analyze impact:
- **Pipelines triggered:** Which CI/CD pipelines will fire on merge (based on triggers and path filters)
- **Services affected:** Which Harness services reference the changed code or manifests
- **Environments reached:** Which environments will receive the change (dev, staging, prod)
- **Downstream impact:** Other services that depend on the changed service
- **Infrastructure changes:** Any Terraform, Helm, or Kubernetes manifest changes

Present findings as:
- DIRECT IMPACT: Pipelines and services directly triggered
- INDIRECT IMPACT: Downstream services and dependent deployments
- RISK LEVEL: Low (test/docs only), Medium (application code), High (infrastructure/security/config)

### Step 4: Security-Focused PR Review

Gather from the user:
- Service name and repository
- PR description and changed components

Security checklist:

**Secrets and Credentials:**
- Scan for hardcoded secrets, API keys, tokens, or passwords in the diff
- Check for new environment variables that should use Harness Secrets
- Verify no secrets are logged or exposed in error messages

**Dependency Changes:**
- Check for new dependencies with known CVEs
- Verify license compatibility of new dependencies
- Flag dependencies from untrusted or deprecated sources

**Configuration Security:**
- Check for overly permissive RBAC or IAM changes
- Verify network policies and security group modifications
- Review any changes to authentication or authorization logic

**Compliance:**
- Verify changes don't violate OPA policies configured in Harness
- Check if changes require additional security review or approval
- Flag changes to compliance-sensitive code paths (PII handling, encryption)

Present findings as a structured security report with PASS/FAIL/WARNING per category.

### Step 5: PR to Production Tracker

Gather from the user:
- Service name, PR title, and target environment
- Expected deployment window

Track the PR lifecycle:

**Stage 1 -- Merge:**
- PR merged to target branch
- CI pipeline triggered

**Stage 2 -- Build:**
```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
```
- Build pipeline status and duration
- Test results and coverage delta
- Security scan results

**Stage 3 -- Deploy to Staging:**
- Staging deployment pipeline status
- Verification results in staging

**Stage 4 -- Production Deployment:**
- Production pipeline status
- Canary or blue-green deployment progress
- Health check results post-deployment

**Stage 5 -- Verification:**
- Error rate comparison: pre-deploy vs. post-deploy
- Latency comparison: pre-deploy vs. post-deploy
- SLO compliance check

Present a timeline view showing the PR's journey with status at each stage and elapsed time.

## Examples

- "What pipelines will this PR trigger?" -- Analyze triggers, path filters, and downstream services to identify all affected pipelines
- "Review this PR for security issues before merge" -- Run security checklist covering secrets, dependencies, RBAC, and compliance
- "Track my PR from merge to production" -- Monitor the PR through build, staging deploy, production deploy, and verification
- "What is the blast radius of this code change?" -- Identify all services, environments, and pipelines impacted

## Performance Notes

- Pipeline impact analysis depends on correctly configured triggers -- misconfigured path filters can miss affected pipelines.
- Security reviews should be automated in the CI pipeline, not just done manually -- use Harness STO for continuous scanning.
- PR tracking is most useful for critical changes -- routine PRs may not need full lifecycle tracking.
- Track PR-to-production cycle time over time to identify process bottlenecks (part of DORA Lead Time for Changes).

## Troubleshooting

### Pipeline Impact Not Matching Actual Triggers
- Check trigger path filters -- glob patterns may not match the actual file paths changed
- Verify branch conditions on triggers (e.g., main-only vs. all branches)
- Look for manual triggers or scheduled pipelines that also deploy the same service

### Security Review False Positives
- Common false positives: test fixtures with dummy credentials, documentation examples
- Add exceptions for test directories and example files
- Verify secret scanning rules match the actual secret formats in use

### PR Tracking Losing Visibility After Merge
- Verify the CI trigger fires on merge to the target branch
- Check that pipeline identifiers in the tracker match the actual pipeline names
- Ensure deployment pipelines have the correct artifact reference to pick up the new build
