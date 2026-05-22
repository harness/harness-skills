---
name: manage-slos
description: >-
  Assist with Harness Service Reliability Management (SRM) tasks that the MCP server currently
  supports: pulling recent deployments for incident correlation, generating on-call handover
  reports from deployment/execution history, and drafting operational runbooks. Use when asked
  about SLOs, error budgets, burn-rate alerts, on-call handover, runbooks, or incident triage.
  Do NOT use for DORA metrics (use dora-metrics instead) or chaos experiments (use
  chaos-experiment instead). Trigger phrases: SLO, SLI, error budget, burn rate, on-call handover,
  runbook, service reliability, incident response, on-call shift.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: |
  Requires Harness MCP v2 server (harness-mcp-v2).
  NOTE: SRM CRUD resources (`slo`, `slo_alert`, `monitored_service`) are NOT currently exposed
  by the MCP server. Creating/managing SLOs and monitored services must be done in the Harness
  UI. This skill focuses on the incident-correlation and reporting workflows that the MCP server
  does support today (via `execution`, `service`, `environment`).
---

# Manage SLOs / SRM

> **Limitation:** The MCP server does not currently expose `slo`, `slo_alert`, or
> `monitored_service` resource types. SLO definitions, burn-rate alerts, and monitored-service
> configuration must be created and edited via the Harness UI under
> **Service Reliability Management**. This skill covers the parts of the SRM workflow that
> *are* supported via MCP: deployment correlation, on-call handover reports, and operational
> runbooks.

## What this skill can do via MCP

| Workflow | Supported today |
|---|---|
| Define an SLO or SLI | ❌ Use the Harness UI |
| Configure error-budget / burn-rate alerts | ❌ Use the Harness UI |
| Configure a monitored service | ❌ Use the Harness UI |
| Correlate deployments with an incident | ✅ via `execution` |
| Summarize recent releases for on-call handover | ✅ via `execution`, `service`, `environment` |
| Draft an operational runbook | ✅ (LLM-authored; pulls context from MCP) |

## Instructions

### Step 1: Establish Scope

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Incident Triage — Correlate Deployments

When the user reports an active incident:

1. Identify the affected service and environment.
2. Pull recent executions that deployed the service.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
  # filter by service or environment as needed
```

3. Correlate incident start time with deployment timestamps.
4. Pull the failing execution's details:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "execution"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

5. Guide the user through structured RCA: blast radius, suspected root cause, mitigation steps, rollback candidate.

### Step 3: On-Call Handover Report

Gather from the user: outgoing/incoming engineers, shift window, owned services.

Pull recent executions and services:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
```

```
Call MCP tool: harness_list
Parameters:
  resource_type: "service"
  org_id: "<organization>"
  project_id: "<project>"
```

Generate a structured handover covering: active/recent incidents the user describes,
deployments during the shift, services with elevated failure counts, and items
requiring attention.

> For SLO burn-rate and error-budget status, direct the user to the SRM UI —
> the MCP server does not expose these metrics.

### Step 4: Operational Runbook (LLM-Authored)

Gather from the user: service name, team, tech stack, dependencies, SLO targets, common
failure modes.

Structure the runbook with:
- Service overview (purpose, owners, tech stack)
- Health checks (pointers to SRM monitored-service dashboard in the Harness UI)
- Common alerts with response procedures
- Escalation paths
- Rollback procedures (reference relevant pipelines via `harness_list resource_type: pipeline`)
- Dependency contacts

## Defining SLOs (UI-Only Today)

When the user asks to define an SLO, burn-rate alert, or monitored service, respond:

1. Gather requirements (service tier, health sources, SLO targets, rolling window, SLI type).
2. Explain that SLO CRUD is not exposed via MCP today and link the user to the Harness SRM UI.
3. Offer to draft the SLO spec (name, target %, SLI type, burn-rate thresholds) as text the
   user can paste into the UI.
4. Suggested burn-rate alert windows: 14.4×/1h (page), 6×/6h (ticket), 1×/3d (log).

## Examples

- "Our payment service is down, help me triage" — Pull recent `execution`s for the service, correlate with incident start, suggest rollback candidate.
- "Generate an on-call handover report" — Pull executions and services during the shift, summarize with active issues.
- "Create a runbook for the auth-service" — Draft runbook using MCP to list pipelines/services/environments for accurate references.
- "Define SLOs for our payment-gateway service" — Draft the SLO spec as text; point to the Harness SRM UI for creation.
- "Configure burn-rate alerts" — Draft the alert config; point to the SRM UI.

## Performance Notes

- When correlating incidents with deployments, pull a wide enough execution window (±30 min) to catch slow-burn failures.
- For handover reports, include both successful and failed executions — a streak of successes is useful context.

## Troubleshooting

### "SLO not found" or "Monitored service not found"
- These resources are not exposed by the MCP server today. Manage them in the Harness UI under Service Reliability Management.

### Incident correlation missing executions
- Confirm `org_id` and `project_id` scope the service
- Broaden the execution filter time window
- Check that the service's pipelines actually ran (no deploy = no execution)
