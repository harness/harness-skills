---
name: create-metric
description: >-
  Create an FME metric (fme_metric): resolves traffic type and event type
  IDs first, drafts the payload for confirmation, then creates. Doesn't
  attach metrics to experiments or add the tracking call - see
  instrument-metric. Trigger phrases: create/define a metric, new metric.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 server (harness-mcp-v2) with fme_metric
  (create/update/delete), fme_traffic_type, and fme_event_type.
  fme_metric.delete is a hard delete with no archive/restore.
---

# Create Metric

Create an FME metric definition, resolving every reference (traffic type,
event type, owners) against real data first instead of guessing IDs.

For every step below marked **Stop condition**, read
`references/stop-conditions.md` before improvising - each covers a case
where a plausible guess is wrong often enough that presenting real options
and waiting for a pick is required, not optional.

## Prerequisites

Establish `org_id` + `project_id`. If `/choose-metric` was already run and
found no suitable metric, reuse its context (hypothesis, traffic type)
instead of re-asking.

## Instructions

### Step 1: Check for an existing metric first

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_metric"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { name: "<proposed name, substring>", limit: 20 }
```

Filter fields go under `filters`, not top-level - passed top-level they're
silently ignored and every metric comes back unfiltered. `limit` belongs in
`filters` too; `harness_list`'s top-level `size` maps to the same thing, so
don't send both. (Same for
`traffic_type` in Step 3). Keep `name` as specific as the request allows:
these are full metric definitions, so a broad substring like `purchase` can
return dozens of them.

The backend returns 409 for a duplicate name and for a duplicate
definition (same attribute combination) under a different name - catching
this early saves a round trip. If something close already exists, confirm a new
metric is actually needed rather than reusing/updating the existing one.

**Stop condition** if the request is vague (e.g. "track checkouts" with no
aggregation specified) - see `references/stop-conditions.md`.

### Step 2: Resolve `trafficType`

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_traffic_type"
  org_id: "<org_id>"
  project_id: "<project_id>"
```

Use the traffic type **name** (immutable after creation, like `name`
itself). Don't ask the user for an ID - resolve it from this list.

### Step 3: Resolve `baseEventTypes[].eventTypeId`

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_event_type"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { traffic_type: "<traffic type name or id>", name: "<event name, if the user named one>" }
```

Add `name` whenever the user named the event; drop it only when you need
the full list to show what's available. Both are substring/ID matches.

**Stop condition** if the event isn't in this list, *or* if several events
match and none is an exact match for what the user said - a substring search
on a word like `purchase` routinely returns a dozen variants, so present the
real ones and ask instead of picking the shortest or cleanest-looking name.
Don't invent an ID and
don't silently substitute the closest-looking real event either; see
`references/stop-conditions.md`.

### Step 4: Decide aggregation, format, spread, isPositive

- **`aggregation`**: `COUNT` (count of events), `TOTAL` (sum of event
  values), `AVERAGE` (average event value), `RATE` (unique units that did
  the event). `TOTAL`/`AVERAGE` sum the `track()` value, or the property
  named in `baseEventTypes[].propertyForValue`.
- **`spread`**: not part of the create body - every new metric is `PER`,
  so don't put it in the draft. `PER` = computed per unit, then compared
  across treatments (`RATE`+`PER` = percent of users who
  converted, `COUNT`+`PER` = events per user). `ACROSS` (one aggregate over
  the whole treatment) is a deprecated legacy value with no create path and
  no significance test in experiment results - don't offer it as a choice.
  Existing `ACROSS` metrics can still be read and patched via
  `fme_metric.update`.
- **`format`**: `NUMBER`, `DOLLAR`, `PERCENTAGE`, `SECONDS`,
  `MILLISECONDS`, `BYTES` - display only. `NUMBER` is the right default when
  the request implies no unit. `RATE`+`PER` always reads back as
  `PERCENTAGE`; `PERCENTAGE` on anything else reads back as `NUMBER`.
- **`isPositive`**: `true` if an increase is a good outcome. Get this
  right - it drives significance-direction interpretation downstream (see
  `/review-experiment-results`).

### Step 5: Name and owners

- `name`: must match `^[A-Za-z][-_A-Za-z0-9]*$`, max 100 chars, immutable.
  No spaces - if the user gives a human title like "Checkout Conversion",
  derive a valid `name` (e.g. `checkout_conversion`) and confirm it rather
  than sending the title verbatim and hitting an unhelpful 400.
- `owners`: required for now - the backend rejects an empty/missing list
  with 400 `"Owners cannot be empty"` until the planned owners deprecation
  ships. Each entry is `{type: "USER", email: "..."}` or
  `{type: "GROUP", identifier: "..."}`. A `GROUP` `identifier` is matched
  against the ids of the groups in the project - the `id` an existing
  `GROUP` owner shows on read, not its display name. An unmatched
  identifier fails with `group owner not found`.

  **Stop condition** if no owner was specified, or one turns out to be
  invalid - see `references/stop-conditions.md`.

### Step 6: Optional fields

- `filterEventType` - `{eventTypeId, filterAggregation, propertyFilters}`,
  resolved the same way as Step 3. Two uses, selected by
  `filterAggregation`:
  - `"RATE"` - HAS_DONE filter: only count units that did this event.
  - `"COUNT"` with `aggregation: COUNT` - ratio metric ("ratio of two
    events per unit"): `baseEventTypes` is the numerator, `filterEventType`
    the denominator.

- `triggerEventType` - `{eventTypeId}`, resolved the same way as Step 3.
  Before/trigger relationship (HAS_DONE_BEFORE): only count units that did
  this event *before* the base event. Use this when the user asks for
  "only count users who did X before Y", "prior to", or "as a trigger" -
  don't substitute a plain `filterEventType` (HAS_DONE, no ordering) for
  this, since it drops the ordering constraint the user asked for. On
  update, omitting the field leaves it unchanged; `null` clears it.

  **Stop condition** if the request is ambiguous between a plain "has done
  this event" filter and a before/trigger relationship - see
  `references/stop-conditions.md`.
- `cap` - outlier capping; 7 sub-fields (`baseEventCountCap`,
  `baseEventSumCap`, `baseEventValueCap`, `filterEventCountCap`,
  `filterEventSumCap`, `filterEventValueCap`, `metricValueCap`, all default
  `0` = no cap) plus `granularity` (`MINUTES|HOURS|DAYS|WEEKS`, default
  `DAYS`) - the time window each cap value is evaluated over, e.g.
  `baseEventCountCap: 5` + `granularity: DAYS` caps at 5 base events per
  unit per day. Only the cap field matching the metric's `aggregation` has
  any effect - don't set others; ask which cap the user wants if they
  mention capping without specifying.
- `tags` - each entry `{name: "..."}` (bare strings are auto-wrapped).

### Step 7: Draft and confirm

Present the full payload before calling anything:

```
name: <name>
trafficType: <name>
format: <FORMAT>
aggregation: <AGGREGATION>
isPositive: <true|false>
baseEventTypes: [{ eventTypeId: <resolved id> }]
owners: [{ type: "USER", email: <email> }]
# + filterEventType / triggerEventType / cap / tags if applicable
```

**STOP HERE. Do not call `harness_create` yet.** Wait for the user to
explicitly confirm the draft.

### Step 8: Create

```
Call MCP tool: harness_create
Parameters:
  resource_type: "fme_metric"
  org_id: "<org_id>"
  project_id: "<project_id>"
  body: { ...confirmed payload }
```

**On a 409, go back to Step 7 - every single time, not just the first
attempt**, and name the specific conflicting metric before drafting a
revision. Full protocol, including how to handle a long chain of
consecutive 409s and how to avoid reusing an already-invalidated field
value: `references/retry-and-troubleshooting.md`.

### Step 9: Verify

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_metric"
  org_id: "<org_id>"
  project_id: "<project_id>"
  resource_id: "<id from create response>"
```

Use the literal `id` string from the `harness_create` response rather than
retyping it. Confirm the returned `format`/`aggregation` match what was
requested; if `format` was coerced (Step 4), tell the user. Never report a
create as successful without this `harness_get` succeeding.

### Step 10: Hand off if needed

Creating the metric does **not** attach it to anything. If this was for an
experiment, tell the user the metric ID and that attaching it (via the
experiment's `keyMetrics`/`supportingMetrics`) is a separate step -
`/choose-metric` covers which list it belongs in.

## Examples

- "Create a metric for checkout conversion rate" - resolve traffic type +
  event, `aggregation: RATE` (percent of users who converted), draft,
  confirm, create.
- "Add a revenue metric based on the purchase_completed event" - Step 3
  resolves `purchase_completed` via `fme_event_type`; `aggregation: TOTAL`,
  `format: DOLLAR`.
- "I want to track average session length" - `aggregation: AVERAGE`,
  `format: SECONDS` or `MILLISECONDS` per the event's value unit.
- "Checkout completions per cart view" - ratio metric: `aggregation: COUNT`,
  `baseEventTypes: checkout_completed`, `filterEventType: {eventTypeId:
  cart_viewed, filterAggregation: COUNT}`.

## Performance Notes

- Resolve traffic type and event type once, not per field.
- `create` has `retryPolicy: do_not_retry`. If a create 400s, list
  `fme_metric` by name before retrying - a rejected create can still leave
  a persisted metric, so don't assume a 400 means nothing happened.
- Don't call `harness_describe` for fields already covered above; use it
  only if the API introduces a field this skill doesn't document.

## Troubleshooting

409s, 400s, and other failure modes, plus the full anti-patterns table:
`references/retry-and-troubleshooting.md`.
