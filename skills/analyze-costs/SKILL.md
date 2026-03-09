---
name: analyze-costs
description: Analyze cloud costs, find optimization opportunities, and track anomalies using Harness CCM via MCP. Use when user says "cloud costs", "analyze costs", "cost optimization", "reduce spending", "cost report", or asks about cloud bills.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Analyze Costs

Analyze cloud costs and identify savings using Harness Cloud Cost Management (CCM) via MCP.

## Instructions

### Step 1: Get Cost Overview

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_overview"
```

Returns total spend, provider breakdown, and trend vs previous period.

### Step 2: Get Cost Breakdown

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_breakdown"
```

Multi-dimensional breakdown by service, environment, team, region.

### Step 3: Explore Perspectives

```
Call MCP tool: harness_list
Parameters:
  resource_type: "cost_perspective"
```

Then get detailed data for a specific perspective:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_perspective"
  resource_id: "<perspective_id>"
```

### Step 4: Get Cost Trends

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_timeseries"
```

### Step 5: Get Optimization Recommendations

```
Call MCP tool: harness_list
Parameters:
  resource_type: "cost_recommendation"
```

For detailed recommendation info:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_recommendation_detail"
  resource_id: "<recommendation_id>"
```

Summary statistics:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_recommendation_stats"
```

### Step 6: Check for Anomalies

```
Call MCP tool: harness_list
Parameters:
  resource_type: "cost_anomaly"
```

To dismiss a known anomaly:

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "cost_anomaly"
  action: "ignore"
  resource_id: "<anomaly_id>"
```

### Step 7: Commitment Analysis

```
Call MCP tool: harness_get
Parameters:
  resource_type: "cost_commitment_analysis"
```

Also: `cost_commitment_coverage`, `cost_commitment_utilisation`, `cost_commitment_savings`

## Report Format

```
## Cloud Cost Analysis

**Period:** Last 30 Days

### Summary
| Provider | Spend | vs Previous |
|----------|-------|-------------|
| AWS      | $X    | +X%         |
| GCP      | $X    | +X%         |
| Azure    | $X    | -X%         |

### Top Recommendations
1. **Rightsize <resource>** - Save $X/month (95% confidence)
2. **Convert to Reserved** - Save $X/month
3. **Delete unused resources** - Save $X/month

### Anomalies
- <date>: <service> spiked $X above expected

### Actions
- [ ] Rightsize instance X
- [ ] Purchase reserved capacity
- [ ] Clean up unused volumes
```

## Cost Resource Types Reference

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `cost_overview` | get | Total spend summary |
| `cost_summary` | get | Filtered cost summary |
| `cost_timeseries` | get | Cost trends over time |
| `cost_breakdown` | get | Multi-dimensional breakdown |
| `cost_perspective` | list, get | Custom cost views |
| `cost_recommendation` | list | Optimization suggestions |
| `cost_recommendation_detail` | get | Detailed recommendation |
| `cost_recommendation_stats` | get | Summary statistics |
| `cost_estimated_savings` | get | Savings projections |
| `cost_anomaly` | list, get | Cost spikes |
| `cost_category` | list, get | Cost allocation |
| `cost_filter_value` | get | Available filter values |

## Examples

- "How much are we spending on cloud?" - Get cost_overview
- "Find $5,000 in monthly savings" - List cost_recommendations, prioritize by savings
- "Why did our bill spike last week?" - List cost_anomaly
- "Break down costs by team" - Get cost_breakdown or cost_perspective
- "Are we using our reserved instances?" - Get cost_commitment_utilisation

## Performance Notes

- Gather data from all relevant perspectives before drawing cost conclusions. Partial data leads to incorrect recommendations.
- Cross-reference recommendations with anomaly data to distinguish trends from spikes.
- Quality of cost analysis is more important than speed. Verify savings estimates before presenting.

## Troubleshooting

### No Cost Data
- Check cloud connectors are configured and syncing
- Initial sync takes 24-48 hours
- Verify billing access permissions (Cost Explorer, Billing API)

### No Recommendations
- Resources need sufficient usage history for analysis
- Small savings may be filtered out
- Check minimum running time requirements
