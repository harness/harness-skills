---
name: choose-metric
description: >-
  Recommend primary/guardrail FME metrics for an experiment or rollout,
  checking existing metrics and event health first. Doesn't create or
  attach metrics - see create-metric / instrument-metric. Trigger phrases:
  choose/pick a metric, primary metric, guardrail metric, what to monitor.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 server (harness-mcp-v2) with fme_metric,
  fme_event_type, and fme_experiment. Rollout-monitoring recommendations
  are advisory only; the MCP server can't attach metrics to a rollout.
  fme_experiment is not registered in the MCP server yet, so Step 2's
  already-attached check is unavailable - recommend from the metric
  inventory and hypothesis alone until it ships. fme_metric and
  fme_event_type are available today.
---

# Choose Metric

Recommend metrics for an FME experiment or feature-flag rollout: which one
is primary, which are guardrails/supporting, and which existing candidates
are healthy enough to trust.

## Prerequisites

Establish Harness-native project scope (`org_id` + `project_id`) before any
list/get call. Do not fall back to a legacy `workspace_id` - `fme_metric`
and `fme_event_type` don't support it.

## Instructions

### Step 1: Identify the context

Ask (if not already stated): is this for an **experiment** (A/B test) or a
**feature-flag rollout** being monitored for safety? The recommendation
logic differs (Step 5).

For an experiment, get the hypothesis before recommending anything:
*"if this succeeds, [what] will increase/decrease?"* The primary metric
must directly measure that hypothesis, not just be topically related.

**Stop condition:** if it's an experiment and the user hasn't stated a
hypothesis, ask for one before recommending a primary metric. Don't infer it
from the flag name.

### Step 2: Check what's already attached (experiment context only)

Skip this step while `fme_experiment` is unregistered (see `compatibility`);
the call will fail on the `resource_type` before reaching the API. Once it
ships, read the experiment's current attachment before recommending
anything, so you don't propose duplicates:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_experiment"
  org_id: "<org_id>"
  project_id: "<project_id>"
  resource_id: "<experiment_id>"
```

Read `keyMetrics`/`supportingMetrics` from the response. If the experiment
doesn't exist yet, skip this step and proceed on the hypothesis alone.
Workspace-wide guardrail metrics are added to every experiment's results
automatically and don't appear in these lists.

### Step 3: Inventory candidate metrics

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_metric"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { traffic_type_id: "<traffic_type_id>", limit: 30 }
```

Always narrow this call. Resolve `traffic_type_id` from `fme_traffic_type`
first if you don't have it, and add `name` when the hypothesis gives an
obvious keyword - an unnarrowed list returns up to 100 full metric
definitions, which is the largest response in this skill by far.

Filter fields (`traffic_type_id`, `name`, `limit`, `offset`) must go inside
`filters` - passed top-level they're silently accepted and ignored. FME
lists default to `limit: 100` (max 100) and ignore `harness_list`'s `page` -
paginate with `offset` instead. When `totalCount` exceeds the rows you got
back, say the inventory was truncated rather than presenting it as the
complete set; `totalCount` is an upper bound, so treat it as "at least this
many more", not an exact remainder.

Read `name`, `description`, `aggregation`, `spread`, `format`,
`isPositive`, and `baseEventTypes[].eventTypeId` for each. `description` matters here: use it
to judge how central or noisy a metric is (a metric described as "leading
indicator, noisy" is a weaker guardrail candidate than one described as
"primary revenue metric").

### Step 4: Health-check each candidate

Metric creation doesn't validate that `baseEventTypes[].eventTypeId` is a
real, live event (FME allows creating a metric ahead of instrumentation),
so a metric can look complete while its event is a typo, was renamed, or
has gone idle. Never recommend a metric without checking:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_event_type"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { name: "<eventTypeId from the metric's baseEventTypes>" }
```

`fme_event_type` only surfaces event types with traffic in the last 30
days. Absent = either the event never existed, was renamed, or has been
idle for 30+ days - classify the metric as **at-risk** either way; don't
guess which. Present = **healthy**.

### Step 5: Recommend, branching by context

**Experiment:**
- **Primary metric** - must directly measure the stated hypothesis, be
  healthy, and use `spread: PER` (`ACROSS` metrics get no significance test,
  so they can't decide an experiment). If no existing metric qualifies, say
  so and recommend `/create-metric` (and `/instrument-metric` first if the
  event doesn't exist yet) rather than forcing a loose fit.
- **Secondary metrics**, each typed:
  - *Guardrail* - a safety metric that must not regress (e.g. error rate,
    latency, unsubscribe rate).
  - *Counter-metric* - checks for an undesirable tradeoff the primary
    metric wouldn't reveal on its own (e.g. conversion up but average order
    value down).
  - *Supporting signal* - correlated metric that corroborates the primary
    without being decisive on its own.
- Map these to the experiment's attachment fields: primary →
  `keyMetrics`, everything else → `supportingMetrics` (set via
  `fme_experiment` create/update; this skill only recommends which metric
  IDs go where).

**Feature-flag rollout monitoring:**
- Prioritize a small set (2-3 ideal) of reliable, low-noise metrics -
  engineering-health metrics (error rate, latency) over noisy product
  metrics, since false-positive rollbacks are costly.
- State that the MCP server can't attach these to the rollout - the user
  (or their dashboards/alerting) has to watch them. Don't imply this skill
  attached anything.

### Step 6: Deliver the recommendation

```
## Recommended Metrics
- Primary: <name> - <why it measures the hypothesis> [healthy/at-risk]
- Guardrail: <name> - <what it protects against> [healthy/at-risk]
- Supporting: <name> - <what it corroborates> [healthy/at-risk]

## Gaps
<any hypothesis/rollout aspect with no healthy existing metric - point to
/create-metric or /instrument-metric>
```

Flag every at-risk metric explicitly rather than silently omitting it -
the user may know it's about to be re-instrumented.

## Examples

- "What metric should I use as primary for the checkout-redesign
  experiment?" - Step 1 hypothesis check, then Steps 3-5 for a primary +
  guardrails.
- "What should I monitor while rolling out the new-search flag?" - flag
  rollout branch of Step 5, cap at 2-3 metrics.
- "Is checkout_conversion_rate a good primary metric for this test?" -
  evaluate the named metric via Steps 3-4 rather than surveying all
  metrics, then confirm or push back with a reason.

## Performance Notes

- List `fme_metric` once per session, not once per candidate.
- Health-check (Step 4) every metric you're about to recommend, but skip it
  for metrics you're explicitly ruling out.

## Troubleshooting

### Experiment doesn't exist yet
Skip Step 2, tell the user you're recommending from the metric inventory
and hypothesis alone without visibility into what (if anything) is already
attached, and proceed.

### No metrics survive the health check
Say so directly rather than recommending an at-risk metric as a stopgap.
Point to `/create-metric` for a new metric and `/instrument-metric` if the
gap is that no event exists yet.

### User proposes more than ~5 metrics for a rollout
Push back - large guardrail sets increase false-positive rollback risk.
Ask which 2-3 matter most rather than accepting the full list silently.
