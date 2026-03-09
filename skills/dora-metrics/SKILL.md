---
name: dora-metrics
description: Generate DORA metrics and engineering performance reports using Harness SEI via MCP. Track deployment frequency, lead time, change failure rate, and MTTR. Use when user says "DORA metrics", "deployment frequency", "lead time", "engineering metrics", or asks about team performance.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# DORA Metrics

Generate DORA metrics reports using Harness Software Engineering Insights (SEI) via MCP.

## Instructions

### Step 1: Get DORA Metrics

Deployment Frequency:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_deployment_frequency"
```

Lead Time for Changes:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_lead_time"
```

Change Failure Rate:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_change_failure_rate"
```

Mean Time to Recovery:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_mttr"
```

### Step 2: Get Drilldown Data

For detailed deployment frequency:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_deployment_frequency_drilldown"
```

For detailed change failure rate:
```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_change_failure_rate_drilldown"
```

### Step 3: Get Team Data

```
Call MCP tool: harness_list
Parameters:
  resource_type: "sei_team"
```

```
Call MCP tool: harness_list
Parameters:
  resource_type: "sei_team_developer"
```

### Step 4: AI Metrics (Optional)

```
Call MCP tool: harness_get
Parameters:
  resource_type: "sei_ai_adoption"
```

Also: `sei_ai_adoption_breakdown`, `sei_ai_impact`, `sei_ai_usage`, `sei_ai_usage_breakdown`

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
| `sei_deployment_frequency` | get | Deploy frequency metric |
| `sei_deployment_frequency_drilldown` | get | Detailed frequency data |
| `sei_lead_time` | get | Lead time for changes |
| `sei_change_failure_rate` | get | Change failure rate |
| `sei_change_failure_rate_drilldown` | get | Detailed CFR data |
| `sei_mttr` | get | Mean time to recovery |
| `sei_team` | list, get | Team definitions |
| `sei_team_developer` | list | Team members |
| `sei_metric` | list, get | Generic metrics |
| `sei_org_tree` | get | Organization structure |
| `sei_business_alignment` | get | Business alignment |
| `sei_ai_adoption` | get | AI adoption metrics |

## Examples

- "How are we doing on DORA metrics?" - Get all 4 metrics, compare to benchmarks
- "Compare DORA across teams" - List teams, get metrics per team
- "What's our deployment frequency trend?" - Get sei_deployment_frequency with drilldown
- "Show AI adoption metrics" - Get sei_ai_adoption and breakdown

## Troubleshooting

### No Metric Data
- Verify SEI integrations are configured (Git, CI/CD, issue tracking)
- Check team mappings exist
- Allow time for data collection and calculation

### Metrics Seem Incorrect
- Verify deployment detection rules in SEI settings
- Check failure classification criteria
- Review team member mappings
