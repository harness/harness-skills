---
name: create-metric
description: >-
  Create an FME metric (fme_metric): resolves traffic type and event type
  IDs first, drafts the payload for confirmation, then creates. Doesn't
  attach metrics to experiments or add the tracking call - see
  instrument-metric. Trigger phrases: create/define a metric, new metric.
metadata:
  author: Harness
  version: 1.1.1
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

At every step marked **Stop condition**, present the real options found and
let the user pick - a search result is not itself a decision.

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
silently ignored and every metric comes back unfiltered (same for
`traffic_type` in Step 3). Keep `name` as specific as the request allows:
these are full metric definitions, so a broad substring like `purchase` can
return dozens of them.

The backend returns 409 for a duplicate name and for a duplicate
definition (same attribute combination) under a different name - catching
this early saves a round trip. If something close already exists, confirm a new
metric is actually needed rather than reusing/updating the existing one.

**Stop condition** if the request is vague (e.g. "track checkouts" with no
aggregation specified): list what already exists and ask which to reuse, or
what shape the new metric should have.

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

**Stop condition** if the event isn't in this list: present the real events
and ask, rather than inventing an ID or substituting the closest match. Note
that `fme_event_type` only shows event types with traffic in the last 30
days, so absence can also mean idle or misspelled. Creating a metric on a
nonexistent event is *allowed* - the backend doesn't validate `eventTypeId` -
but the metric silently never computes until the event flows; make sure the
user accepts that before proceeding, or hand off to `/instrument-metric`.

### Step 4: Decide aggregation, format, spread, isPositive

- **`aggregation`**: `COUNT` (count of events), `TOTAL` (sum of event
  values), `AVERAGE` (average event value), `RATE` (unique units that did
  the event). `TOTAL`/`AVERAGE` sum the `track()` value, or the property
  named in `baseEventTypes[].propertyForValue`.
- **`spread`**: send `PER` explicitly. `PER` = computed per unit, then
  compared across treatments (`RATE`+`PER` = percent of users who
  converted, `COUNT`+`PER` = events per user). `ACROSS` (one aggregate over
  the whole treatment) is a deprecated legacy value with no create path and
  no significance test in experiment results - don't offer it as a choice.
  Existing `ACROSS` metrics can still be read and patched via
  `fme_metric.update`.
- **`format`**: `NUMBER`, `DOLLAR`, `PERCENTAGE`, `SECONDS`,
  `MILLISECONDS`, `BYTES` - display only. `RATE`+`PER` always reads back as
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
  `{type: "GROUP", identifier: "..."}` (a `GROUP` owner must match a Split
  Team name, not a Harness user-group identifier).

  **Stop condition** if no owner was specified, or one turns out to be
  invalid - ask for a real `USER` email or `GROUP` name rather than
  substituting a plausible one.

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
  this event" filter (`filterEventType`) and a before/trigger ordering
  (`triggerEventType`) - ask which, since the two count different units.
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
spread: PER
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

On a 409, name the specific conflicting metric, then go back to Step 7 for
a fresh confirmation - on every attempt, not just the first. If the fix
changes what the metric measures (a different `aggregation` or
`baseEventTypes` than asked for), that's a new decision, not a retry.

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
  event, `aggregation: RATE`, confirm `PER` (percent of users) vs `ACROSS`,
  draft, confirm, create.
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

### 409 on create
A duplicate name, or a duplicate attribute combination
(`trafficType`+`aggregation`+`spread`+`baseEventTypes`+`filterEventType`)
under a different name. Re-run Step 1 with broader filters to find it.

### 400 "Owners cannot be empty"
Owners are required until the deprecation ships. A `GROUP` owner must match
a Split Team name, not a Harness user-group identifier.

### 400 on `name` with no field named in the message
Almost certainly the `^[A-Za-z][-_A-Za-z0-9]*$` pattern (no spaces, no
leading digit).

### Metric created but never computes
`eventTypeId` existence isn't validated at create time, so a typo or a
not-yet-instrumented event silently produces a metric with no data. Check
`fme_event_type` and route to `/instrument-metric`.

### Need to remove a metric
`fme_metric.delete` is a hard delete with no undo. Confirm explicitly, and
check the metric isn't still referenced by an experiment's
`keyMetrics`/`supportingMetrics` first.
