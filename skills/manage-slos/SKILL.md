---
name: manage-slos
description: >-
  Manage Harness Service Reliability Management (SRM) via MCP. Define SLOs with SLIs and error budgets,
  configure burn-rate alerts, set up incident detection and automated response workflows, generate
  on-call handover reports, triage incidents with root cause analysis, and create operational runbooks.
  Use when asked to define SLOs, configure error budgets, set up incident detection, create on-call
  handover reports, generate runbooks, or monitor service reliability. Do NOT use for DORA metrics
  (use dora-metrics instead) or chaos experiments (use chaos-experiment instead). Trigger phrases:
  SLO, SLI, error budget, burn rate, incident detection, on-call handover, runbook, service reliability,
  MTTR, availability target, latency SLO, incident response, on-call shift.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage SLOs

Define, configure, and monitor Service Level Objectives (SLOs), incident detection workflows, on-call handover reports, and operational runbooks in Harness SRM.

## Instructions

### Step 1: Establish Scope

Confirm the user's org and project context. SRM resources are project-scoped.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Define SLOs

Gather the following from the user:
- Service name and tier (Tier 1 / Tier 2 / Tier 3)
- Health sources (e.g., Datadog, Prometheus, CloudWatch)
- SLO targets: availability %, latency threshold, error rate target
- Rolling window (typically 30 days)
- SLI type: ratio-based (good/total requests) or window-based (% of time healthy)

Create the SLO:

```
Call MCP tool: harness_create
Parameters:
  resource_type: "slo"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    name: "<service>-availability-slo"
    identifier: "<service>_availability_slo"
    type: "Simple"
    sloTarget:
      type: "Rolling"
      sloTargetPercentage: 99.9
      periodLengthDays: 30
    serviceLevelIndicators:
      - type: "Ratio"
        eventType: "Good"
        metric1: "<good_event_metric>"
        metric2: "<valid_event_metric>"
    healthSourceRef: "<health_source_connector>"
```

### Step 3: Configure Error Budget Alerts

Set up multi-window burn-rate alerts:
- Page on-call when remaining budget drops below 10%
- Warn the team when below 25%
- Configure burn-rate multiplier alerts (e.g., 14.4x burn rate over 1 hour)

```
Call MCP tool: harness_create
Parameters:
  resource_type: "slo_alert"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    sloIdentifier: "<slo_identifier>"
    conditions:
      - type: "ErrorBudgetRemainingPercentage"
        threshold: 10
        notificationRuleRef: "<page_notification>"
      - type: "BurnRate"
        threshold: 14.4
        lookbackDuration: "1h"
        notificationRuleRef: "<page_notification>"
```

### Step 4: Set Up Incident Detection (Optional)

If the user wants automated incident detection:
- Configure anomaly detection method (static threshold, ML-based, or composite)
- Set alert correlation window (group related alerts within N minutes)
- Define escalation tiers with response time SLAs

```
Call MCP tool: harness_create
Parameters:
  resource_type: "monitored_service"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    name: "<service_name>"
    identifier: "<service_identifier>"
    type: "Application"
    serviceRef: "<service_ref>"
    environmentRef: "<env_ref>"
    healthSources:
      - name: "<health_source_name>"
        type: "<provider_type>"
        identifier: "<health_source_id>"
```

### Step 5: Generate On-Call Handover Report (Optional)

When asked for a handover report, gather:
- Outgoing and incoming engineer names
- Shift time window
- Services owned by the team

Then use harness_list to pull recent incidents and SLO status:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "slo"
  org_id: "<organization>"
  project_id: "<project>"
```

Generate a structured handover with: active incidents, SLO status, recent changes, and items requiring attention.

### Step 6: Generate Operational Runbook (Optional)

When asked to create a runbook, gather:
- Service name, team, tech stack
- Dependencies and SLO targets
- Common failure modes

Structure the runbook with sections for: service overview, health checks, common alerts with response procedures, escalation paths, rollback procedures, and dependency contacts.

### Step 7: Incident Triage and RCA (Optional)

When a user reports an active incident:

1. Check the service's current SLO burn rate
2. List dependent services and their error rates
3. Pull recent deployments via `harness_list` with `resource_type: "execution"`
4. Correlate timeline: deployment time vs. incident start
5. Guide through structured RCA: blast radius, root cause hypothesis, mitigation steps

## Examples

- "Define SLOs for our payment-gateway service" -- Create availability, latency, and error rate SLOs with error budget alerts
- "Set up incident detection for the checkout service" -- Configure monitored service with health sources and anomaly detection
- "Generate an on-call handover report" -- Pull SLO status, active incidents, and recent changes for shift handover
- "Create a runbook for the auth-service" -- Generate operational runbook with health checks, alert procedures, and escalation paths
- "Our payment service is down, help me triage" -- Check SLO burn rate, correlate with deployments, assess blast radius
- "Configure burn-rate alerts for our SLOs" -- Set up multi-window burn-rate alerting with PagerDuty/Slack notifications

## Performance Notes

- Verify health source connectors exist before creating SLOs -- SLOs require valid metric sources.
- Use ratio-based SLIs for request-driven services and window-based SLIs for availability-focused services.
- For burn-rate alerts, the standard multi-window approach uses 14.4x/1h (page), 6x/6h (ticket), 1x/3d (log).
- On-call handover reports should be generated at shift boundaries -- stale data reduces their value.
- Runbooks should reference actual monitoring dashboards and alert names to be actionable.

## Troubleshooting

### SLO Not Tracking
- Verify the health source connector is connected and receiving data
- Confirm the SLI metric names match the actual metric names in the monitoring tool
- Check that the monitored service is correctly linked to the Harness service and environment

### Error Budget Alerts Not Firing
- Verify notification rules are configured with valid channels (Slack, PagerDuty, email)
- Check burn-rate thresholds -- too high a threshold may never trigger
- Confirm the SLO has enough data points to calculate burn rate (needs at least one full window)

### Incident Detection False Positives
- Increase the alert correlation window to group related alerts
- Tune anomaly detection sensitivity -- ML-based detection needs 2-4 weeks of baseline data
- Add noise reduction rules to filter low-impact alerts
