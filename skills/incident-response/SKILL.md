---
name: incident-response
description: >-
  Incident response and analysis via Harness MCP. Correlate incidents with recent deployments,
  assess blast radius and downstream service impact, and generate comprehensive postmortem
  documents. Use when asked to investigate an incident, determine if a deployment caused an
  issue, assess blast radius, or create a postmortem. Do NOT use for pipeline debugging
  (use debug-pipeline instead) or SLO management (use manage-slos instead). Trigger phrases:
  incident, deployment correlation, blast radius, postmortem, root cause, service impact,
  outage analysis, rollback decision, incident timeline, deployment caused, which deploy.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Incident Response

Correlate incidents with deployments, assess blast radius, and generate postmortem documents using Harness MCP.

## Instructions

### Step 1: Establish Scope

Confirm the affected service, environment, and incident details.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "service"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Identify the Incident Response Task

Determine which workflow the user needs:

1. **Deployment-to-Incident Correlation** -- Determine if a recent deployment caused the incident
2. **Blast Radius Assessment** -- Map affected services and downstream impact
3. **Postmortem Generation** -- Create a structured postmortem document

### Step 3: Correlate Deployment to Incident

Gather from the user:
- Affected service name and environment
- Alert or incident name and start time
- Observed symptoms (error rate spike, latency, outage)

Pull recent deployments:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
  status: "Success"
```

For each recent deployment, check:
- **Timing:** Was the deployment within the incident correlation window (e.g., 2 hours before)?
- **Service match:** Does the deployed service match or depend on the affected service?
- **Change content:** What changed in the deployment (config, code, infrastructure)?

Build a deployment timeline:
1. List all deployments to the affected environment in the last N hours
2. Mark the incident start time on the timeline
3. Identify the most likely causal deployment (closest before incident start)
4. Check if a rollback was performed and whether it resolved the issue

Present findings with confidence level: HIGH (deployment matches timing + service), MEDIUM (timing matches but different service), LOW (no deployment correlation found).

### Step 4: Assess Blast Radius

Gather from the user:
- Failing service and failure type (outage, elevated error rate, high latency)
- Current error rate or severity
- Environment

Map the impact:

```
Call MCP tool: harness_status
Parameters:
  org_id: "<organization>"
  project_id: "<project>"
```

Assess:
- **Direct impact:** The failing service's error rate, latency, and availability
- **Upstream callers:** Services that call the failing service -- are they degrading?
- **Downstream dependencies:** Services the failing service depends on -- are they healthy?
- **User impact:** Estimate affected users based on traffic volume
- **Data integrity:** Any risk of data corruption or inconsistency?

Classify severity:
- **Critical:** User-facing outage, data loss risk, or multiple services affected
- **Major:** Degraded performance affecting users, single service impacted
- **Minor:** Internal service degraded, no user-facing impact

Recommend immediate actions based on blast radius:
- If deployment-correlated: recommend rollback with expected resolution time
- If infrastructure-related: recommend failover or scaling
- If dependency-related: recommend circuit breaker activation or graceful degradation

### Step 5: Generate Postmortem

Gather from the user:
- Service name and incident summary
- Incident duration and environment
- Resolution steps taken

Structure the postmortem:

**1. Executive Summary** -- What happened, customer impact, duration (2-3 sentences)

**2. Timeline** -- Build from Harness pipeline events and alert timestamps:
- When was the issue first detected?
- When did the on-call team engage?
- What deployment or change triggered the regression?
- When was mitigation applied and service restored?

Pull timeline data:
```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
```

**3. Root Cause Analysis** -- Which deployment or change triggered the incident and why

**4. Impact Assessment** -- Affected services, environments, and approximate user impact

**5. Action Items** -- Categorized as:
- Immediate fixes (address the root cause)
- Process improvements (prevent recurrence)
- Monitoring improvements (detect faster)

**6. Lessons Learned** -- What went well, what didn't, and what was lucky

## Examples

- "Our payment service is down -- was it a deployment?" -- Correlate incident with recent deployments and provide confidence level
- "What is the blast radius of the checkout outage?" -- Map upstream/downstream services and estimate user impact
- "Generate a postmortem for yesterday's auth-service incident" -- Create structured postmortem with timeline, RCA, and action items
- "A Sev-1 just fired -- which deployment caused it?" -- Pull recent deployments and correlate with alert timing

## Performance Notes

- Deployment correlation is most accurate within a 2-hour window -- beyond that, other factors become more likely.
- Blast radius assessment requires an up-to-date service dependency map -- stale maps miss connections.
- Postmortems should be generated within 48 hours while the incident is fresh in the team's memory.
- Always include what went well in the postmortem -- blameless culture requires acknowledging good responses.

## Troubleshooting

### No Deployment Found in Correlation Window
- Expand the search window to 4-6 hours -- some failures have delayed onset
- Check for infrastructure changes (not just code deployments)
- Look for config changes, feature flag toggles, or certificate expirations

### Blast Radius Assessment Missing Services
- The service dependency map may be incomplete -- check for undocumented dependencies
- Look for shared infrastructure (databases, message queues) that multiple services use
- Check for external dependencies (third-party APIs, DNS, CDN)

### Postmortem Missing Timeline Events
- Pull from multiple sources: pipeline executions, alert history, and chat transcripts
- Check if automated rollbacks occurred that may not be in the deployment history
- Include infrastructure events (auto-scaling, node failures) alongside deployment events
