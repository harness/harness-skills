---
name: deployment-readiness
description: >-
  Assess deployment readiness via Harness MCP. Run pre-deployment readiness checks with go/no-go
  recommendations, analyze environment drift between source and target environments, and provide
  data-driven canary rollout decisions. Use when asked to check if a service is ready to deploy,
  compare environments before deployment, or decide whether to promote a canary. Do NOT use for
  running pipelines (use run-pipeline instead) or debugging failures (use debug-pipeline instead).
  Trigger phrases: deployment readiness, ready to deploy, pre-deploy check, environment drift,
  canary decision, promote canary, rollback canary, go no-go, deployment checklist, production
  readiness, canary analysis.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Deployment Readiness

Assess deployment readiness, analyze environment drift, and make data-driven canary rollout decisions using Harness MCP.

## Instructions

### Step 1: Establish Scope

Confirm the service, target environment, and deployment type.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "service"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Identify the Readiness Task

Determine which assessment the user needs:

1. **Deployment Readiness Check** -- Comprehensive pre-deploy validation with go/no-go
2. **Environment Drift Analysis** -- Differences between source and target environments
3. **Canary Rollout Decision** -- Data-driven promote, pause, or rollback recommendation

### Step 3: Run Deployment Readiness Check

Gather from the user:
- Service name and target environment
- Deployment type (rolling, blue-green, canary)
- Change summary (what is being deployed)

Execute readiness checks:

**Pipeline Health:**
```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
  pipeline_id: "<pipeline_identifier>"
```
- Last N pipeline executions: pass rate and failure patterns
- All required stages passed (build, test, security scan)

**Dependency Verification:**
- All referenced connectors, secrets, and infrastructure are accessible
- Required approvals are configured for the target environment

**Artifact Readiness:**
- Container image exists and has passed security scanning
- SBOM is generated and signed (if required)
- Image tag matches the expected version

**Environment Health:**
- Target environment is not frozen or in maintenance
- No active incidents on the target cluster
- Resource capacity is sufficient for the deployment

**Security Gates:**
- No critical or high CVEs above threshold
- OPA policies pass for the target environment
- Required compliance attestations are present

Present a structured report with PASS/FAIL/WARNING for each check and a final GO/NO-GO recommendation.

### Step 4: Analyze Environment Drift

Gather from the user:
- Service name, source environment, and target environment

Compare environments using harness_get for each:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "environment"
  resource_id: "<source_env>"
  org_id: "<organization>"
  project_id: "<project>"
```

Check for drift in:
- **Configuration:** Environment variables, feature flags, config maps
- **Infrastructure:** Resource limits, replica counts, node pools
- **Secrets:** Secret versions and rotation status
- **Manifests:** Kubernetes manifest differences
- **Dependencies:** External service versions and endpoints

Classify each difference by risk:
- CRITICAL: Could cause outage (missing secrets, wrong endpoints)
- WARNING: May cause behavioral differences (different resource limits)
- INFO: Cosmetic or expected differences (environment-specific values)

### Step 5: Canary Rollout Decision

Gather from the user:
- Service name, canary traffic percentage, and duration
- Canary version vs. baseline version
- Key metrics to evaluate (error rate, latency, throughput)

Analyze canary health:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
```

Evaluate:
- **Error rate:** Canary vs. baseline (threshold: no more than 1.1x baseline)
- **Latency:** P50, P95, P99 comparison
- **Throughput:** Requests handled without errors
- **Resource usage:** CPU and memory vs. baseline
- **Business metrics:** Conversion rate, transaction success rate

Provide a recommendation:
- **PROMOTE** -- All metrics within thresholds, recommend increasing traffic or full rollout
- **HOLD** -- Some metrics borderline, recommend extending observation window
- **ROLLBACK** -- Metrics degraded beyond thresholds, recommend immediate rollback

## Examples

- "Is our payment-service ready to deploy to production?" -- Run full readiness check with go/no-go recommendation
- "Compare staging and production environments before deploying" -- Analyze configuration, infrastructure, and secret drift
- "Should we promote the canary or roll back?" -- Evaluate canary metrics and recommend promote/hold/rollback
- "Run a pre-deploy checklist for the checkout service" -- Validate pipeline health, artifacts, security gates, and environment

## Performance Notes

- Readiness checks should run against the actual target environment, not a cached state -- environments change between checks.
- Environment drift analysis is most valuable right before deployment -- running it hours early may miss recent changes.
- Canary decisions need sufficient traffic volume to be statistically meaningful -- low-traffic services may need longer observation windows.
- Include business metrics in canary analysis when available -- technical metrics alone may miss user-facing issues.

## Troubleshooting

### Readiness Check Returns False Negatives
- Verify connectors and secrets are accessible from the readiness check runner
- Check that security scan results are available for the specific image tag being deployed
- Ensure environment freeze status is up to date

### Drift Analysis Shows Too Many Differences
- Filter out expected differences (environment-specific variables like URLs, credentials)
- Focus on infrastructure and manifest drift first -- these are most likely to cause issues
- Use environment overrides in Harness to manage expected per-environment configuration

### Canary Metrics Inconclusive
- Increase traffic percentage to get more data points
- Extend the observation window to capture more traffic patterns
- Check that metric collection is working correctly for the canary pods
