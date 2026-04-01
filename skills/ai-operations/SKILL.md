---
name: ai-operations
description: >-
  Configure Harness AI-powered operations (AIDA) via MCP. Set up predictive failure analysis
  with ML models for memory leaks, disk exhaustion, connection pool saturation, and latency
  degradation. Configure intelligent alert correlation and noise reduction to reduce alert
  volume. Use when asked to set up predictive failure analysis, configure AI-powered alerting,
  reduce alert noise, or enable ML-based anomaly detection. Do NOT use for pipeline debugging
  (use debug-pipeline instead) or SLO management (use manage-slos instead). Trigger phrases:
  AIDA, predictive failure, alert correlation, noise reduction, anomaly detection, AI ops,
  predictive analysis, alert fatigue, ML alerting, intelligent alerting.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# AI Operations

Configure AI-powered predictive failure analysis and intelligent alert correlation using Harness AIDA.

## Instructions

### Step 1: Establish Scope

Confirm the user's org, project, service, and observability stack.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the AI Operations Task

Determine which workflow the user needs:

1. **Predictive Failure Analysis** -- ML-based detection of impending failures before SLO breach
2. **Alert Correlation and Noise Reduction** -- Group related alerts and suppress duplicates

### Step 3: Configure Predictive Failure Analysis

Gather from the user:
- Service name and data sources (Datadog, Prometheus, CloudWatch)
- Prediction horizon (30 minutes, 1 hour, 4 hours, 24 hours ahead)
- Training data period (30 days, 90 days, 6 months)
- Model type preference (anomaly detection, time series forecasting, ensemble)

Configure failure prediction scenarios:

1. **Memory leak detection** -- Flag services where memory grows above threshold per window
2. **Disk exhaustion** -- Predict time-to-full and alert N hours in advance
3. **Connection pool saturation** -- Alert when pool usage exceeds threshold for sustained duration
4. **Latency degradation** -- Detect progressive slowdown before SLO breach
5. **Deployment-induced regression** -- Correlate metric changes with recent deployments

Configure alerting:
- Set prediction confidence threshold (suppress below threshold to reduce noise)
- Route alerts to PagerDuty, Slack, or other channels
- Enable auto-generated runbook suggestions using AIDA
- Set up false positive feedback loop for model improvement

Configure data sources:
- Metrics source (Prometheus, Datadog, CloudWatch)
- Log source (Elasticsearch, Splunk, CloudWatch Logs)
- Trace source (Jaeger, Datadog APM, AWS X-Ray)
- Model retraining frequency (daily, weekly, monthly, on data drift)

### Step 4: Configure Alert Correlation and Noise Reduction

Gather from the user:
- Current alert volume (alerts/day) and target reduction percentage
- Alerting tools in use (PagerDuty, OpsGenie, Grafana, Datadog)
- Correlation preferences

Configure alert correlation:
- Correlation window: group alerts fired within N minutes
- Correlation method: topology-based, time-based, ML-based, or hybrid
- Service dependency mapping for topology-based correlation

Configure noise reduction:
- Deduplication: merge identical alerts across sources
- Suppression: suppress known-noisy alerts during maintenance windows
- Aggregation: combine N similar alerts into a single incident
- Priority scoring: ML-based severity assignment using historical resolution data

Configure intelligent routing:
- Route to the team that owns the affected service
- Escalation: auto-escalate if not acknowledged within SLA
- Context enrichment: attach recent deployments, related logs, and runbook links to alerts

## Examples

- "Set up predictive failure analysis for our payment service" -- Configure ML models to detect memory leaks, disk exhaustion, and latency degradation
- "Reduce our alert noise by 50%" -- Configure alert correlation and deduplication to reduce daily alert volume
- "Alert us 4 hours before disk runs out" -- Configure disk exhaustion prediction with advance warning
- "Correlate alerts across our microservices" -- Set up topology-based alert correlation using service dependency map
- "Auto-generate runbook suggestions for alerts" -- Enable AIDA-powered runbook recommendations

## Performance Notes

- ML models need 2-4 weeks of baseline data before predictions become reliable -- expect higher false positive rates initially.
- Topology-based correlation requires an accurate service dependency map -- stale maps cause missed correlations.
- Alert correlation windows should balance grouping (longer = fewer alerts) with response time (shorter = faster notification).
- Retraining frequency should match how fast the system changes -- fast-moving services need weekly retraining.

## Troubleshooting

### High False Positive Rate
- Increase the confidence threshold to suppress low-confidence predictions
- Provide false positive feedback to improve the model
- Check that training data period includes representative traffic patterns (weekday, weekend, peak)

### Predictions Not Triggering
- Verify data sources are connected and sending metrics
- Check that the prediction horizon is appropriate for the failure mode
- Ensure the model has completed initial training (2-4 weeks minimum)

### Alert Correlation Missing Related Alerts
- Increase the correlation window to capture cascading failures
- Update the service dependency map if topology-based correlation is in use
- Check that all alert sources are integrated (missing sources cause orphaned alerts)
