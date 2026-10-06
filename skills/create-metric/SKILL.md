---
name: create-metric
description: >-
  Create a Harness FME metric: helps decide what to measure, suggests candidate
  metrics from application code, resolves traffic type and event type IDs,
  drafts the payload, then creates. Doesn't attach metrics to experiments
  (manage-experiments) or add the tracking call (instrument-metric). Trigger
  phrases: create/define a metric, new metric, what metrics should we create,
  suggest metrics.
metadata:
  author: Harness
  version: 1.4.1
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Create Metric

Create an FME metric definition, with guidance on what makes a good metric and what to measure. Resolves traffic types and events against real data and asks the user to select an owner instead of guessing IDs. Owner existence is validated by the API on creation/readback; the declared tools do not provide an owner-directory lookup. Design guidance lives in [metric-design.md](../../references/fme/metric-design.md). Related: `/manage-experiments` attaches metrics; `/instrument-metric` adds tracking calls.

For every phase marked **Stop condition**, see [stop-conditions.md](references/stop-conditions.md) before improvising.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List metrics | `harness_list` · `fme_metric` · `filters: { name?, traffic_type_id?, limit }` · `compact: false` | `harness list metric --name <substring> --traffic-type-id <id> --json` |
| List traffic types | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type --json` |
| List event types | `harness_list` · `fme_event_type` · `filters: { traffic_type?, name? }` · `compact: false` | `harness list event_type --traffic-type <name or id> --name <substring> --json` |
| **Get event type** | `harness_get` · `fme_event_type` · `params: { event_type_id }` | `harness get event_type <event-name> --json` |
| Create metric | `harness_create` · `fme_metric` · `body: { name, trafficType, format, aggregation, isPositive, baseEventTypes, owners, description?, filterEventType?, triggerEventType?, cap?, tags? }` | `harness create metric <name> -f metric.json --json` (file holds the full confirmed payload, including `owners` and any nested `filterEventType`/`triggerEventType`/`cap` objects — same fields as the MCP `body`) |
| Get metric | `harness_get` · `fme_metric` · `params: { metric_id }` | `harness get metric <id> --json` |
| Delete metric | `harness_delete` · `fme_metric` · `params: { metric_id }` | `harness delete metric <id>` |

## Instructions

### Phase 1: Establish scope

See [scope-establishment.md](../../references/scope-establishment.md). Confirm organization and project before any list or get operation — this is the Harness org/project, independent of the local application repo's name or git remote; never infer scope from the repo you're reading code in. If `/choose-metric` already ran and found no suitable metric, reuse its context (hypothesis, traffic type).

### Phase 2: Understand the intent

What decision does the metric support (experiment primary / guardrail / supporting, or rollout monitoring)? What should change in which direction? Reuse `/choose-metric` context if it ran. If the user doesn't know what to measure or asks for suggestions, run [Suggest metrics from code](../../references/fme/metric-design.md#suggest-metrics-from-code), show the coverage table, and let them pick one metric per pass. Pick the shape by asking the plain questions from [Intent to configuration](../../references/fme/metric-design.md#intent-to-configuration) ("how many times?", "did they at least once?", "how much / how long?"), not by asking for aggregation names.

### Phase 3: Check for an existing metric first

**List metrics** with full definitions, narrowed by name substring and traffic type if known — you need `aggregation` and `baseEventTypes` to judge duplicates. Read naming and tag conventions from this list. The backend returns 409 for a duplicate name or duplicate definition (same attribute combination under a different name). Catching this early saves a round trip. Check for [auto-created ` - Split Agents` metrics](../../references/fme/metric-design.md#auto-created-metrics) before creating a latency or error metric. If something close exists, confirm a new metric is actually needed rather than reusing/updating the existing one.

**Stop condition** if the request is vague (e.g. "track checkouts" with no aggregation specified) — see [Ambiguous metric intent](references/stop-conditions.md#ambiguous-metric-intent).

### Phase 4: Resolve `trafficType`

**List traffic types** and use the traffic type **name** (immutable after creation, like `name` itself). Don't ask the user for an ID — resolve it from this list.

### Phase 5: Resolve `baseEventTypes[].eventTypeId`

**List event types** narrowed by traffic type and event name if the user named one. The event name filter is a case-insensitive substring match; the traffic type filter accepts an ID or exact name, not a substring. Check pagination before treating a list as complete; use **Get event type** for an agreed exact name and verify the returned `trafficTypes` includes the intended type. Note: RUM/integration events may flow with no `track()` in code.

**Stop condition** if the event isn't in this list, *or* if several events match and none is an exact match for what the user said — a substring search on a word like `purchase` routinely returns a dozen variants, so present the real ones and ask instead of picking the shortest or cleanest-looking name. Don't invent an ID and don't silently substitute the closest-looking real event; see [Missing or ambiguous event](references/stop-conditions.md#missing-or-ambiguous-event). If instrumentation is needed, settle the aggregation/value contract and applicable property filters below **before** handing off. Pass scope, environment, exact event name, traffic type, units, value source and required properties; resume here with that same contract plus code-test and delivery evidence, not just a success claim.

### Phase 6: Decide aggregation, format, isPositive

Start from the matching row in the [intent table](../../references/fme/metric-design.md#intent-to-configuration). Key details:
- **`aggregation`**: `COUNT`, `TOTAL`, `AVERAGE`, `RATE` — see intent table for which fits.
- **`spread`**: not part of create body — every new metric is `PER`. Don't include it.
- **`format`**: `NUMBER`, `DOLLAR`, `PERCENTAGE`, `SECONDS`, `MILLISECONDS`, `BYTES`. `RATE`+`PER` coerces to `PERCENTAGE`.
- **`isPositive`**: `true` if increase is good. Drives significance-direction interpretation.
- **`baseEventTypes[].propertyForValue`**: for `TOTAL`/`AVERAGE`, the value can come from a named property on the event instead of the numeric `track()` value argument — set this when the user says the value lives in a property (e.g. `order_total`) rather than being passed positionally.
- **Cap recommended** for TOTAL/AVERAGE on unbounded values (revenue, durations) — reduces noise from heavy users.

This is the event **contract** (`trafficType`, `aggregation`, value units, value-vs-`propertyForValue`, and any required `properties`) that `/instrument-metric` must match exactly — if the event isn't instrumented yet, settle this contract now so the tracking call isn't written against a guess.

### Phase 7: Name, description, and owners

- `name`: must match `^[A-Za-z][-_A-Za-z0-9]*$`, max 100 chars, immutable. No spaces — if the user gives a human title, derive a valid name and confirm. Follow observed naming convention from Phase 3.
- `description`: [what is counted, where event fires, which direction is good](../../references/fme/metric-design.md#naming-description-and-tags).
- `owners`: required; `{type: "USER", email}` or `{type: "GROUP", identifier}` (group's `id` field, not display name).

**Stop condition** if no owner was specified, or one turns out to be invalid — see [Missing or invalid owner](references/stop-conditions.md#missing-or-invalid-owner). Don't claim the owner was directory-verified without an actual lookup.

### Phase 8: Optional fields

- `filterEventType` — `{eventTypeId, filterAggregation, propertyFilters}`, resolved the same way as Phase 5. Two uses, selected by `filterAggregation`:
  - `"RATE"` — HAS_DONE filter: only count units that did this event.
  - `"COUNT"` with `aggregation: COUNT` — ratio metric ("ratio of two events per unit"): `baseEventTypes` is the numerator, `filterEventType` the denominator.
- `triggerEventType` — `{eventTypeId}`, resolved the same way as Phase 5. Before/trigger relationship (HAS_DONE_BEFORE): only count units that did this event *before* the base event. Use this when the user asks for "only count users who did X before Y", "prior to", or "as a trigger" — don't substitute a plain `filterEventType` (HAS_DONE, no ordering), since it drops the ordering constraint.

**Stop condition** if the request is ambiguous between a plain "has done" filter and a before/trigger relationship — see [Filter versus ordered trigger](references/stop-conditions.md#filter-versus-ordered-trigger).

- `cap` — outlier capping; 7 sub-fields (`baseEventCountCap`, `baseEventSumCap`, `baseEventValueCap`, `filterEventCountCap`, `filterEventSumCap`, `filterEventValueCap`, `metricValueCap`, all default `0` = no cap) plus `granularity` (`MINUTES|HOURS|DAYS|WEEKS`, default `DAYS`) — the time window each cap value is evaluated over. Only the cap field matching the metric's `aggregation` has any effect — don't set others; ask which cap the user wants if they mention capping without specifying.
- `tags` — send each entry as `{name: "..."}`.

### Phase 9: Draft and confirm

Present the full payload before calling anything:

```
name: <name>
trafficType: <name>
format: <FORMAT>
aggregation: <AGGREGATION>
isPositive: <true|false>
baseEventTypes: [{ eventTypeId: <resolved id>, propertyForValue: null, propertyFilters: [] }]
owners: [{ type: "USER", email: <email> }]
description: <optional>
# + filterEventType / triggerEventType / cap / tags if applicable
```

Replace the template's property fields with the confirmed value property and filters when used; otherwise include `propertyForValue: null` and `propertyFilters: []` explicitly on each base event for CLI/MCP parity. Write the full approved body as JSON/YAML for CLI `-f`, or pass it as MCP `body`; don't combine a file with `--set`/`--add` expecting a merge.

Quality check (outside the payload, not part of the body sent to the API): [warnings from good-metric checklist that fail — e.g. no cap on revenue, direction unclear, event not flowing]

**STOP HERE. Do not call Create yet.** Wait for the user to explicitly confirm the draft.

### Phase 10: Create

**Create metric** with the confirmed payload. See [write-safety.md](../../references/fme/write-safety.md) for the confirmation protocol.

**On a 409, go back to Phase 9 — every single time, not just the first attempt** — and name the specific conflicting metric before drafting a revision. Full protocol: [retry-and-troubleshooting.md](references/retry-and-troubleshooting.md).

### Phase 11: Verify

**Get metric** using the literal `id` string from the create response (don't retype it). Read back every field against the confirmed Phase 9 draft, not just `format`/`aggregation`: `name`, `trafficType`, every event reference (`baseEventTypes`, and `filterEventType`/`triggerEventType` if set — including their `propertyForValue`/`propertyFilters`/`filterAggregation`), `aggregation`/`format`/`isPositive` (direction), `owners`, `cap`, `tags`. Account for documented defaults/normalization (such as omitted cap fields becoming zero). Report any substantive mismatch; don't silently update the metric to fix it. If `format` was coerced (Phase 6), tell the user. If the response includes a UI link, share that exact link — never construct or guess one. Never report a create as successful without this get succeeding.

### Phase 12: Hand off if needed

Creating the metric does **not** attach it to anything. If this was for an experiment, tell the user the metric ID and that attaching it (via the experiment's `keyMetrics` / `supportingMetrics`) is a separate step — `/manage-experiments` handles attachment; `/choose-metric` covers which list it belongs in.

## Examples

- "What metrics could we create for checkout?" — Phase 2 code suggestions via coverage table; user picks; resolve, draft, create.
- "Track average page load time" — Phase 3 checks for auto-created `Average Page Load Time - Split Agents` metric first; reuse if present.
- "Create a metric for checkout conversion rate" — resolve traffic type + event, `aggregation: RATE`, draft, confirm, create.
- "Add a revenue metric based on the purchase_completed event" — Phase 5 resolves `purchase_completed`; `aggregation: TOTAL`, `format: DOLLAR`.

## Performance Notes

- Resolve traffic type and event type once, not per field.
- If a create 400s, **List metrics** by name before retrying — a rejected create can still leave a persisted metric, so don't assume a 400 means nothing happened.
- Check for metric usage before delete: see [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

## Troubleshooting

See [retry-and-troubleshooting.md](references/retry-and-troubleshooting.md) for: 409s, 400s, anti-patterns table, owner validation, name pattern failures.
