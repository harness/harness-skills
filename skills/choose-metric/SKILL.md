---
name: choose-metric
description: >-
  Recommend primary/guardrail metrics for an experiment or rollout, judged
  against a good-metric checklist. Checks existing metrics and event health,
  surfaces auto-created guardrails. Doesn't create or attach metrics — see
  create-metric / instrument-metric / manage-experiments. Trigger phrases:
  choose/pick a metric, primary metric, guardrail metric, what to monitor.
metadata:
  author: Harness
  version: 1.3.2
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Choose Metric

Recommend metrics for an FME experiment or feature-flag rollout: which is primary, which are guardrails/supporting, and which existing candidates are healthy enough to trust, judged against [what makes a good metric](../../references/fme/metric-design.md#what-makes-a-good-metric). Related: `/manage-experiments` attaches metrics to experiments; `/create-metric` creates new metrics; `/instrument-metric` adds tracking calls.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| Get flag | `harness_get` · `fme_feature_flag` · `params: { feature_flag_name }` | `harness get feature_flag <name> --json` |
| Get experiment | `harness_get` · `fme_experiment` · `params: { experiment_id }` | `harness get experiment <id> --json` |
| List metrics | `harness_list` · `fme_metric` · `filters: { traffic_type_id?, name?, limit }` · `compact: false` | `harness list metric --traffic-type-id <id> --name <substring> --json` |
| List traffic types | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type --json` |
| List event types | `harness_list` · `fme_event_type` · `filters: { traffic_type?, name? }` · `compact: false` | `harness list event_type --traffic-type <name or id> --name <substring> --json` |
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

**List metrics** with full definitions, narrowed by the traffic type from Phase 4 and a name substring if the hypothesis gives an obvious keyword. Request ~30 rows unless the hypothesis points to a specific name. A total exceeding returned rows proves more pages remain, but equality does not prove completeness: MCP can fall back to page length when the API total is absent. Set an explicit `filters.limit`/`filters.offset` and follow [pagination](../../references/fme/tool-map.md#pagination) for metrics, traffic types and event inventories. Say "no suitable metric in the examined subset," not "no suitable metric exists"; finish pagination (or ask to narrow a costly inventory) before making a project-wide absence claim.

Read `name`, `description`, `aggregation`, `spread`, `format`, `isPositive`, `baseEventTypes[].eventTypeId` for each. Judge candidates against [What makes a good metric](../../references/fme/metric-design.md#what-makes-a-good-metric), not health alone.

### Phase 6: Health-check each candidate

Metric creation doesn't validate any event reference, so a metric can look complete while its event is a typo, was renamed, or has gone idle. For each candidate you're about to recommend, **Get event type** for *every* event reference it uses — `baseEventTypes`, and `filterEventType`/`triggerEventType` if set, not just the base event, since a stale filter or trigger event silently changes which units get counted even if the base event is healthy. The response has only `id` and `trafficTypes` — check the returned `trafficTypes` includes the candidate's traffic type. Event types are listed only if an event arrived in the last 30 days, project-wide across all environments — this isn't a "currently flowing" guarantee for any one environment. An exact-get 404 means no matching event is visible in this scope/window — check scope and spelling, then whether a previously working flow has simply been idle. It does **not** prove the event was never instrumented. Absence from a filtered or partial list is inconclusive. Ask whether the flow has run recently before concluding the metric needs re-instrumentation or modifying any code; if confirmed idle rather than broken, say so instead of handing off to `instrument-metric` by default. Don't health-check metrics you're explicitly ruling out.

For rollout monitoring, surface [auto-created ` - Split Agents` metrics](../../references/fme/metric-design.md#auto-created-metrics) as ready-made guardrails.

### Phase 7: Recommend, branching by context

**Experiment:**
- **Primary metric** — must directly measure the stated hypothesis, be healthy, and use `spread: PER` (`ACROSS` metrics get no significance test and can't decide an experiment). One of each secondary type is usually enough; every extra metric adds noise. A primary with no events produces no result. The metric's traffic type must match the flag's traffic type, and the subject key used in `track()` must be the same key `getTreatment` uses for this flag (attribution fact) — the event's **name** does not need to, and usually shouldn't, match the flag's name. If no existing metric qualifies, recommend `/create-metric` (and `/instrument-metric` first if the event doesn't exist yet) rather than forcing a loose fit.
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
<any hypothesis/rollout aspect with no healthy metric>
For each gap, give a concrete starting spec (event, aggregation, format, isPositive from the intent table) for /create-metric. If the app repo is available, offer candidates via [Suggest metrics from code](../../references/fme/metric-design.md#suggest-metrics-from-code).
```

Flag every at-risk metric explicitly rather than silently omitting it — the user may know it's about to be re-instrumented.

## Examples

- "We have no metrics yet — what should we measure for the search-ranking test?" — Phase 2 hypothesis check; Phase 5 finds no candidates; Phase 8 gaps with code suggestions if app repo available.
- "What metric should I use as primary for the checkout-redesign experiment?" — Phase 2 hypothesis check, then Phases 5-7 for a primary + guardrails.
- "Pick guardrails for the new-pricing test" — primary already known/set; focus Phase 7 on guardrail/counter-metric selection only.
- "What should I monitor while rolling out the new-search flag?" — flag rollout branch of Phase 7, cap at 2-3 metrics; surface auto-created metrics.
- "Is checkout_conversion_rate a good primary metric for this test?" — evaluate the named metric via Phases 5-6 rather than surveying all metrics, then confirm or push back with a reason.

## Performance Notes

- Reuse one metric inventory per scope/session, not one per candidate; an inventory may require multiple pages.
- Health-check (Phase 6) every metric you're about to recommend, but skip it for metrics you're explicitly ruling out.
- Don't **Get experiment** per treatment — once per experiment is enough (Phase 3).
- Don't use substring list to check event health; use **Get event type** (exact) for a definitive 200/404 signal.

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Experiment doesn't exist yet | Phase 3 fails with 404 | Skip Phase 3, tell the user you're recommending from inventory and hypothesis alone, proceed |
| No metrics survive health check | Referenced events are not visible in the current scope/window | Confirm scope, exact names, traffic types, and recent activity first. Idle events do not imply missing instrumentation or justify duplicate metrics. Route to `/instrument-metric` only for a confirmed gap/investigation; report candidates as at-risk, not decision-ready |
| User proposes >5 metrics for a rollout | Large guardrail set increases false-positive rollback risk | Push back — ask which 2-3 matter most |
