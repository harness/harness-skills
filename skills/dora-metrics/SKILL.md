---
name: dora-metrics
description: Generate DORA metrics and engineering performance reports using Harness SEI via MCP. Track deployment frequency, lead time, change failure rate, and MTTR. Use when user says "DORA metrics", "deployment frequency", "lead time", "engineering metrics", or asks about team performance.
metadata:
  author: Harness
  version: 2.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2). All six DORA metric variants are served by a single consolidated `sei_dora_metric` resource — pick the variant via the `metric` parameter.
---

# DORA Metrics

Generate DORA metrics reports using Harness Software Engineering Insights (SEI) via MCP.

## Instructions

All DORA metrics are served by a single resource type: `sei_dora_metric`. Pass the `metric` parameter to select the variant:

- `deployment_frequency`
- `deployment_frequency_drilldown`
- `lead_time`
- `change_failure_rate`
- `change_failure_rate_drilldown`
- `mttr`

Required inputs on every DORA call: `team_ref_id`, `date_start`, `date_end`, `granularity` (DAILY | WEEKLY | MONTHLY).

### Step 1: Get a DORA Metric

Deployment Frequency:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_dora_metric"
  metric: "deployment_frequency"
  team_ref_id: "<team_id>"
  date_start: "2026-03-01"
  date_end: "2026-04-01"
  granularity: "WEEKLY"
```

Lead Time for Changes:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_dora_metric"
  metric: "lead_time"
  team_ref_id: "<team_id>"
  date_start: "2026-03-01"
  date_end: "2026-04-01"
  granularity: "WEEKLY"
```

Change Failure Rate:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_dora_metric"
  metric: "change_failure_rate"
  team_ref_id: "<team_id>"
  date_start: "2026-03-01"
  date_end: "2026-04-01"
  granularity: "WEEKLY"
```

Mean Time to Recovery:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_dora_metric"
  metric: "mttr"
  team_ref_id: "<team_id>"
  date_start: "2026-03-01"
  date_end: "2026-04-01"
  granularity: "WEEKLY"
```

### Step 2: Get Drilldown Data

Per-deployment detail for frequency:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_dora_metric"
  metric: "deployment_frequency_drilldown"
  team_ref_id: "<team_id>"
  date_start: "2026-03-01"
  date_end: "2026-04-01"
  granularity: "DAILY"
```

Per-failure detail for CFR:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_dora_metric"
  metric: "change_failure_rate_drilldown"
  team_ref_id: "<team_id>"
  date_start: "2026-03-01"
  date_end: "2026-04-01"
  granularity: "DAILY"
```

### Step 3: Get Team Data

List teams:
```
Call MCP tool: harness_list
Parameters:
  resource_type: "sei_team"
```

Get team details (integrations, developers, integration filters):
```
Call MCP tool: harness_list
Parameters:
  resource_type: "sei_team_detail"
  team_ref_id: "<team_id>"
  aspect: "developers"   # or "integrations" | "integration_filters"
```

### Step 4: AI Metrics (Optional)

```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_ai_adoption"
```

Related: `sei_ai_impact`, `sei_ai_usage`, `sei_ai_raw_metric`.

## DORA Benchmarks

| Metric | Elite | High | Medium | Low |
|--------|-------|------|--------|-----|
| Deployment Frequency | Multiple/day | Weekly-Monthly | Monthly-6mo | 6mo+ |
| Lead Time | < 1 hour | 1 day-1 week | 1-6 months | 6mo+ |
| Change Failure Rate | < 5% | 5-10% | 10-15% | > 15% |
| MTTR | < 1 hour | < 1 day | 1 day-1 week | 1 week+ |

## Report Format

```
## DORA Metrics Report

**Period:** <date range>
**Team:** <team or org>

### Performance Summary

| Metric | Value | Rating | Trend |
|--------|-------|--------|-------|
| Deployment Frequency | X/week | High | Improving |
| Lead Time | X hours | Elite | Stable |
| Change Failure Rate | X% | Medium | Needs attention |
| MTTR | X hours | High | Improving |

### Overall Rating: <Elite/High/Medium/Low>

### Recommendations
1. CFR at X% - invest in test automation and code review
2. Lead time trending up - look at PR review bottlenecks
3. Consider feature flags to decouple deploy from release
```

## SEI Resource Types

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `sei_dora_metric` | get (+ `metric` param) | All 6 DORA variants: deployment_frequency, deployment_frequency_drilldown, lead_time, change_failure_rate, change_failure_rate_drilldown, mttr |
| `sei_team` | list, get | Team definitions |
| `sei_team_detail` | list (+ `aspect` param: developers / integrations / integration_filters) | Per-team sub-resources |
| `sei_metric` | list, get | Generic metrics |
| `sei_productivity_metric` | get | Productivity metrics |
| `sei_org_tree` | list, get | Organization structure |
| `sei_org_tree_detail` | list, get | Org tree detail |
| `sei_business_alignment` | get | Business alignment |
| `sei_ai_adoption` | get | AI adoption metrics |
| `sei_ai_impact` | get | AI impact metrics |
| `sei_ai_usage` | get | AI usage metrics |
| `sei_ai_raw_metric` | get | Raw AI metrics |

## Examples

- "How are we doing on DORA metrics?" - Call `sei_dora_metric` four times with each primary `metric`
- "Compare DORA across teams" - List `sei_team`, then call `sei_dora_metric` per `team_ref_id`
- "What's our deployment frequency trend?" - Get `sei_dora_metric` with `metric: deployment_frequency`, then drilldown
- "Show AI adoption metrics" - Get `sei_ai_adoption` and related AI resources

## Performance Notes

- Always pass `team_ref_id`, `date_start`, `date_end`, `granularity` — these are required.
- Gather metrics across the full requested time range before generating the report. Partial data skews results.
- Compare metrics across multiple time periods to identify trends, not just snapshots.

## Troubleshooting

### No Metric Data
- Verify SEI integrations are configured (Git, CI/CD, issue tracking)
- Confirm `team_ref_id` belongs to an active SEI team (`harness_list resource_type: sei_team`)
- Check the date range covers data the integrations have ingested
- Allow time for data collection and calculation after new integrations are added

### Metrics Seem Incorrect
- Verify deployment detection rules in SEI settings
- Check failure classification criteria
- Review team member mappings via `sei_team_detail aspect: developers`
