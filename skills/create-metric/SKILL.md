---
name: create-metric
description: >-
  Create a Harness FME metric: resolves traffic type and event type
  IDs first, drafts the payload for confirmation, then creates. Doesn't
  attach metrics to experiments (manage-experiments) or add the tracking call
  (instrument-metric). Trigger phrases: create/define a metric, new metric.
metadata:
  author: Harness
  version: 1.3.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Create Metric

Create an FME metric definition, resolving every reference (traffic type, event type, owners) against real data first instead of guessing IDs. Related: `/manage-experiments` attaches metrics; `/instrument-metric` adds tracking calls.

For every phase marked **Stop condition**, see [stop-conditions.md](references/stop-conditions.md) before improvising.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List metrics | `harness_list` · `fme_metric` · `filters: { name?, traffic_type_id?, limit }` · `compact: false` | `harness list metric --name <substring> --traffic-type-id <id> --json` |
| List traffic types | `harness_list` · `fme_traffic_type` | `harness list traffic_type --json` |
| List event types | `harness_list` · `fme_event_type` · `filters: { traffic_type?, name? }` | `harness list event_type --traffic-type <name or id> --name <substring> --json` |
| **Get event type** | `harness_get` · `fme_event_type` · `params: { event_type_id }` | `harness get event_type <event-name> --json` |
| Create metric | `harness_create` · `fme_metric` · `body: { name, trafficType, format, aggregation, isPositive, baseEventTypes, owners, description?, filterEventType?, triggerEventType?, cap?, tags? }` | `harness create metric <name> --traffic-type <name> --event-type <id> --set format=<FORMAT> --set aggregation=<AGG> --set isPositive=<bool>` |
| Get metric | `harness_get` · `fme_metric` · `params: { metric_id }` | `harness get metric <id> --json` |
| Delete metric | `harness_delete` · `fme_metric` · `params: { metric_id }` | `harness delete metric <id>` |

## Instructions

### Phase 1: Establish scope

See [scope-establishment.md](../../references/scope-establishment.md). Confirm organization and project before any list or get operation. If `/choose-metric` already ran and found no suitable metric, reuse its context (hypothesis, traffic type).

### Phase 2: Check for an existing metric first

**List metrics** with full definitions, narrowed by name substring and traffic type if known — you need `aggregation` and `baseEventTypes` to judge duplicates. The backend returns 409 for a duplicate name or duplicate definition (same attribute combination under a different name). Catching this early saves a round trip. If something close exists, confirm a new metric is actually needed rather than reusing/updating the existing one.

**Stop condition** if the request is vague (e.g. "track checkouts" with no aggregation specified) — see [stop-conditions.md](references/stop-conditions.md).

### Phase 3: Resolve `trafficType`

**List traffic types** and use the traffic type **name** (immutable after creation, like `name` itself). Don't ask the user for an ID — resolve it from this list.

### Phase 4: Resolve `baseEventTypes[].eventTypeId`

**List event types** narrowed by traffic type and event name if the user named one. Both are substring matches.

**Stop condition** if the event isn't in this list, *or* if several events match and none is an exact match for what the user said — a substring search on a word like `purchase` routinely returns a dozen variants, so present the real ones and ask instead of picking the shortest or cleanest-looking name. Don't invent an ID and don't silently substitute the closest-looking real event; see [stop-conditions.md](references/stop-conditions.md).

### Phase 5: Decide aggregation, format, isPositive

- **`aggregation`**: `COUNT` (count of events), `TOTAL` (sum of event values), `AVERAGE` (average event value), `RATE` (unique units that did the event). `TOTAL` / `AVERAGE` sum the `track()` value, or the property named in `baseEventTypes[].propertyForValue`.
- **`spread`**: not part of the create body — every new metric is `PER`, so don't include it in the draft. `PER` = computed per unit, then compared across treatments (`RATE`+`PER` = percent of users who converted, `COUNT`+`PER` = events per user). `ACROSS` is deprecated with no create path and no significance test — don't offer it. Existing `ACROSS` metrics can be updated.
- **`format`**: `NUMBER`, `DOLLAR`, `PERCENTAGE`, `SECONDS`, `MILLISECONDS`, `BYTES` — display only. `NUMBER` is the default when the request implies no unit. `RATE`+`PER` always reads back as `PERCENTAGE`; `PERCENTAGE` on anything else reads back as `NUMBER`.
- **`isPositive`**: `true` if an increase is a good outcome. Get this right — it drives significance-direction interpretation (see `/review-experiment-results`).

### Phase 6: Name, description, and owners

- `name`: must match `^[A-Za-z][-_A-Za-z0-9]*$`, max 100 chars, immutable. No spaces — if the user gives a human title like "Checkout Conversion", derive a valid `name` (e.g. `checkout_conversion`) and confirm it rather than sending the title verbatim and hitting a 400.
- `description`: optional; may be provided in the create body.
- `owners`: required for now — the backend rejects an empty/missing list with 400 `"Owners cannot be empty"` until the planned owners deprecation ships. Each entry is `{type: "USER", email: "..."}` or `{type: "GROUP", identifier: "..."}`. A `GROUP` `identifier` must be the group's **identifier** (the `id` field an existing `GROUP` owner shows on read), not its display name. An unmatched identifier fails with `group owner not found`.

**Stop condition** if no owner was specified, or one turns out to be invalid — see [stop-conditions.md](references/stop-conditions.md).

### Phase 7: Optional fields

- `filterEventType` — `{eventTypeId, filterAggregation, propertyFilters}`, resolved the same way as Phase 4. Two uses, selected by `filterAggregation`:
  - `"RATE"` — HAS_DONE filter: only count units that did this event.
  - `"COUNT"` with `aggregation: COUNT` — ratio metric ("ratio of two events per unit"): `baseEventTypes` is the numerator, `filterEventType` the denominator.
- `triggerEventType` — `{eventTypeId}`, resolved the same way as Phase 4. Before/trigger relationship (HAS_DONE_BEFORE): only count units that did this event *before* the base event. Use this when the user asks for "only count users who did X before Y", "prior to", or "as a trigger" — don't substitute a plain `filterEventType` (HAS_DONE, no ordering), since it drops the ordering constraint.

**Stop condition** if the request is ambiguous between a plain "has done" filter and a before/trigger relationship — see [stop-conditions.md](references/stop-conditions.md).

- `cap` — outlier capping; 7 sub-fields (`baseEventCountCap`, `baseEventSumCap`, `baseEventValueCap`, `filterEventCountCap`, `filterEventSumCap`, `filterEventValueCap`, `metricValueCap`, all default `0` = no cap) plus `granularity` (`MINUTES|HOURS|DAYS|WEEKS`, default `DAYS`) — the time window each cap value is evaluated over. Only the cap field matching the metric's `aggregation` has any effect — don't set others; ask which cap the user wants if they mention capping without specifying.
- `tags` — send each entry as `{name: "..."}`.

### Phase 8: Draft and confirm

Present the full payload before calling anything:

```
name: <name>
trafficType: <name>
format: <FORMAT>
aggregation: <AGGREGATION>
isPositive: <true|false>
baseEventTypes: [{ eventTypeId: <resolved id> }]
owners: [{ type: "USER", email: <email> }]
description: <optional>
# + filterEventType / triggerEventType / cap / tags if applicable
```

**STOP HERE. Do not call Create yet.** Wait for the user to explicitly confirm the draft.

### Phase 9: Create

**Create metric** with the confirmed payload. See [write-safety.md](../../references/fme/write-safety.md) for the confirmation protocol.

**On a 409, go back to Phase 8 — every single time, not just the first attempt** — and name the specific conflicting metric before drafting a revision. Full protocol: [retry-and-troubleshooting.md](references/retry-and-troubleshooting.md).

### Phase 10: Verify

**Get metric** using the literal `id` string from the create response (don't retype it). Confirm the returned `format` / `aggregation` match what was requested; if `format` was coerced (Phase 5), tell the user. Never report a create as successful without this get succeeding.

### Phase 11: Hand off if needed

Creating the metric does **not** attach it to anything. If this was for an experiment, tell the user the metric ID and that attaching it (via the experiment's `keyMetrics` / `supportingMetrics`) is a separate step — `/manage-experiments` handles attachment; `/choose-metric` covers which list it belongs in.

## Examples

- "Create a metric for checkout conversion rate" — resolve traffic type + event, `aggregation: RATE` (percent of users who converted), draft, confirm, create.
- "Add a revenue metric based on the purchase_completed event" — Phase 4 resolves `purchase_completed`; `aggregation: TOTAL`, `format: DOLLAR`.
- "I want to track average session length" — `aggregation: AVERAGE`, `format: SECONDS` or `MILLISECONDS` per the event's value unit.
- "Checkout completions per cart view" — ratio metric: `aggregation: COUNT`, `baseEventTypes: checkout_completed`, `filterEventType: {eventTypeId: cart_viewed, filterAggregation: COUNT}`.

## Performance Notes

- Resolve traffic type and event type once, not per field.
- If a create 400s, **List metrics** by name before retrying — a rejected create can still leave a persisted metric, so don't assume a 400 means nothing happened.
- Check for metric usage before delete: see [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

## Troubleshooting

See [retry-and-troubleshooting.md](references/retry-and-troubleshooting.md) for: 409s, 400s, anti-patterns table, owner validation, name pattern failures.
