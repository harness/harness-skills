---
name: choose-metric
description: >-
  Recommend primary/guardrail FME metrics for an experiment or rollout,
  checking existing metrics and event health first. Doesn't create or
  attach metrics — see create-metric / instrument-metric / manage-experiments.
  Trigger phrases: choose/pick a metric, primary metric, guardrail metric,
  what to monitor.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Choose Metric

Recommend metrics for an FME experiment or feature-flag rollout: which is primary, which are guardrails/supporting, and which existing candidates are healthy enough to trust. Related: `/manage-experiments` attaches metrics to experiments; `/create-metric` creates new metrics; `/instrument-metric` adds tracking calls.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| Get flag | `harness_get` · `fme_feature_flag` · `params: { feature_flag_name }` | `harness get feature_flag <name> --json` |
| Get experiment | `harness_get` · `fme_experiment` · `params: { experiment_id }` | `harness get experiment <id> --json` |
| List metrics | `harness_list` · `fme_metric` · `filters: { traffic_type_id?, name?, limit }` · `compact: false` | `harness list metric --traffic-type-id <id> --name <substring> --json` |
| List traffic types | `harness_list` · `fme_traffic_type` | `harness list traffic_type --json` |
| Get event type | `harness_get` · `fme_event_type` · `params: { event_type_id }` | `harness get event_type <event-name> --json` |

## Instructions

### Phase 1: Establish scope

See [scope-establishment.md](../../references/scope-establishment.md). Confirm organization and project before any list or get operation.

### Phase 2: Identify the context

Ask (if not already stated): is this for an **experiment** (A/B test) or a **feature-flag rollout** being monitored for safety? The recommendation logic differs (Phase 5).

For an experiment, get the hypothesis before recommending anything: *"if this succeeds, [what] will increase/decrease?"* The primary metric must directly measure that hypothesis, not just be topically related.

**Stop condition:** if it's an experiment and the user hasn't stated a hypothesis, ask for one before recommending a primary metric. Don't infer it from the flag name.

### Phase 3: Check what's already attached (experiment context only)

If the experiment exists, **Get experiment** to read `keyMetrics` / `supportingMetrics` so you don't propose duplicates. Workspace-wide [GUARDRAIL / ALERT metrics](../../references/fme/concepts.md#experiments-and-metrics) are added automatically and don't appear in these lists. If the experiment doesn't exist yet, skip this check and proceed on the hypothesis alone.

### Phase 4: Resolve the traffic type

To narrow the metric list, get the flag's traffic type: **Get flag** returns `trafficType` with `id` and `name`. If you don't have the flag name, **List traffic types** and ask which one applies — a metric on a different traffic type won't collect data for the experiment or rollout.

### Phase 5: Inventory candidate metrics

**List metrics** with full definitions, narrowed by the traffic type from Phase 4 and a name substring if the hypothesis gives an obvious keyword. Request ~30 rows unless the hypothesis points to a specific name. When the total count exceeds the rows returned, report the inventory as truncated.

Read `name`, `description`, `aggregation`, `spread`, `format`, `isPositive`, `baseEventTypes[].eventTypeId` for each. Use `description` to judge centrality vs. noise — "leading indicator, noisy" is a weaker guardrail than "primary revenue metric".

### Phase 6: Health-check each candidate

Metric creation doesn't validate `baseEventTypes[].eventTypeId`, so a metric can look complete while its event is a typo, was renamed, or has gone idle. For each candidate you're about to recommend, **Get event type** using the `eventTypeId` as the exact name. Event types are listed only if an event arrived in the last 30 days. If **Get event type** returns 404 (or the type isn't listed), no events arrived in 30 days — treat it as not instrumented and hand off to `instrument-metric`. Don't health-check metrics you're explicitly ruling out.

### Phase 7: Recommend, branching by context

**Experiment:**
- **Primary metric** — must directly measure the stated hypothesis, be healthy, and use `spread: PER` (`ACROSS` metrics get no significance test and can't decide an experiment). If no existing metric qualifies, recommend `/create-metric` (and `/instrument-metric` first if the event doesn't exist yet) rather than forcing a loose fit.
- **Secondary metrics**, each typed as:
  - *Guardrail* — safety metric that must not regress (error rate, latency, unsubscribe). Goes in `supportingMetrics` (category `SUPPORTING` in results) — not to be confused with workspace-wide `GUARDRAIL` category metrics, which apply automatically to every experiment. See [concepts.md](../../references/fme/concepts.md#experiments-and-metrics) for the distinction.
  - *Counter-metric* — checks for undesirable tradeoffs the primary wouldn't reveal (conversion up but average order value down).
  - *Supporting signal* — correlated metric that corroborates the primary without being decisive.
- Map these to attachment fields: primary → `keyMetrics`, all others → `supportingMetrics`. Attaching them is a separate step; see `/manage-experiments`.

**Feature-flag rollout monitoring:**
- Prioritize a small set (2-3 ideal) of reliable, low-noise metrics — engineering-health metrics (error rate, latency) over noisy product metrics, since false-positive rollbacks are costly.
- State that Harness can't attach these to the rollout automatically — the user (or their dashboards/alerting) must watch them. Don't imply this skill attached anything.

### Phase 8: Deliver the recommendation

```
## Recommended Metrics
- Primary: <name> — <why it measures the hypothesis> [healthy/at-risk]
- Guardrail: <name> — <what it protects against> [healthy/at-risk]
- Supporting: <name> — <what it corroborates> [healthy/at-risk]

## Gaps
<any hypothesis/rollout aspect with no healthy metric — point to /create-metric or /instrument-metric>
```

Flag every at-risk metric explicitly rather than silently omitting it — the user may know it's about to be re-instrumented.

## Examples

- "What metric should I use as primary for the checkout-redesign experiment?" — Phase 2 hypothesis check, then Phases 5-7 for a primary + guardrails.
- "Pick guardrails for the new-pricing test" — primary already known/set; focus Phase 7 on guardrail/counter-metric selection only.
- "What should I monitor while rolling out the new-search flag?" — flag rollout branch of Phase 7, cap at 2-3 metrics.
- "Is checkout_conversion_rate a good primary metric for this test?" — evaluate the named metric via Phases 5-6 rather than surveying all metrics, then confirm or push back with a reason.

## Performance Notes

- **List metrics** once per session, not once per candidate.
- Health-check (Phase 6) every metric you're about to recommend, but skip it for metrics you're explicitly ruling out.
- Don't **Get experiment** per treatment — once per experiment is enough (Phase 3).
- Don't use substring list to check event health; use **Get event type** (exact) for a definitive 200/404 signal.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Experiment doesn't exist yet | Phase 3 fails with 404 | Skip Phase 3, tell the user you're recommending from inventory and hypothesis alone, proceed |
| No metrics survive health check | All `baseEventTypes` return 404 | Say so directly; recommend `/create-metric` and `/instrument-metric` — don't propose an at-risk metric as a stopgap |
| User proposes >5 metrics for a rollout | Large guardrail set increases false-positive rollback risk | Push back — ask which 2-3 matter most |
