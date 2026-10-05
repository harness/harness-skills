---
name: instrument-metric
description: >-
  Add a Harness FME track() call for a metric's event and verify it arrives.
  Doesn't create the metric (create-metric) or choose it
  (choose-metric). Trigger phrases: instrument this event, add a track call,
  wire up tracking, verify the event arrives.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Instrument Metric

Wire up the `track()` call an FME metric needs, then verify the event is actually arriving — don't declare success on code changes alone. Related: `/create-metric` creates metrics; `/choose-metric` recommends which metrics to use.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| Get metric | `harness_get` · `fme_metric` · `params: { metric_id }` | `harness get metric <id> --json` |
| Get event type | `harness_get` · `fme_event_type` · `params: { event_type_id }` | `harness get event_type <event-name> --json` |

## Instructions

### Phase 1: Establish scope

See [scope-establishment.md](../../references/scope-establishment.md). Confirm organization and project before any get operation.

### Phase 2: Detect the SDK

See [sdk-patterns.md](../../references/fme/sdk-patterns.md) for SDK detection (searching for existing `track()` calls or dependency manifests) and identifying whether it's a client-side or server-side SDK — the two have different `track()` signatures.

### Phase 3: Install and initialize if needed

**Stop condition:** if no SDK is present, ask before installing — state which SDK/package you'd add and get confirmation rather than picking a version unilaterally. Ask the user which environment's SDK key to use (server-side and client-side keys differ) and add initialization matching existing config patterns in the codebase (env var naming, secret management) — never hardcode the key.

### Phase 4: Find the right placement

Locate the exact point where the tracked action actually completes (e.g. after a successful purchase confirmation from the payment provider, not the button click that starts the flow). Wrong placement produces misleading metric data with no error to catch it.

**Stop condition:** if there's more than one plausible placement (e.g. optimistic UI vs. server-confirmed success), ask the user which one matches the metric's intent rather than guessing.

### Phase 5: Confirm the event name

The event name is case-sensitive and must match exactly what `/create-metric` used or will use. If the metric already exists, **Get metric** to read the event from `baseEventTypes[].eventTypeId` and use that exact string. If the metric doesn't exist yet, agree on the event name with the user now so `/create-metric` can reference it later without a mismatch.

### Phase 6: Write the `track()` call

Use the signature for the SDK's mode, reusing existing context objects (user key, traffic type / attributes) rather than constructing new ones. See [sdk-patterns.md](../../references/fme/sdk-patterns.md) for server-side vs. client-side `track()` signatures per language.

`trafficType` must be the metric's traffic type. Pass a numeric value only if the metric's `aggregation` is `TOTAL` / `AVERAGE` and it doesn't read the value from a property; `COUNT` / `RATE` need none. Pass `properties` whenever the metric uses property filters or reads values from properties — without them the event still arrives, but property filters don't match it and property-based values have nothing to read. If the codebase has an existing tracking wrapper/helper, extend it rather than calling the SDK directly.

### Phase 7: Trigger and verify

Ask the user to trigger the action (or state clearly that you cannot execute their running application yourself), then verify: **Get event type** using the event name exactly. Event types with traffic in the last 30 days return 200; 404 = absent or idle > 30 days.

A new event type takes about 90s from `track()` to appear. If absent, retry ~30s apart and don't conclude failure before ~2 minutes. A 200 confirms the event type is flowing in aggregate, not that your test invocation produced it (there's no per-event lookup). If other traffic already sends this event, treat a hit as encouraging, not proof; a never-before-seen event name is a much stronger signal.

If you're checking an event tied to an existing, previously working metric (not a fresh test), a 404 can mean either "never instrumented" or "instrumented but idle for 30+ days," not just "broken." Ask whether the flow that fires it has actually run recently before concluding the tracking call is wrong.

## Examples

- "Add tracking for checkout completion" — Phases 2-4 to place the call after payment confirmation, Phase 5 to agree the event name with `/create-metric`'s expected `checkout_completed`, Phases 6-7 to write and verify.
- "Is the signup event actually flowing?" — skip to Phase 7 only, using the event name already in an existing metric; if absent, apply the 30-day idle caveat before calling it broken.
- "Wire up a new SDK for this service" — Phases 2-3 focus (no `track()` call yet), confirm before installing.

## Performance Notes

- Check for an existing `track()` pattern before assuming no SDK is present — a partial/unused SDK dependency without a live call is a different situation from no SDK at all.
- Don't poll **Get event type** in a tight loop — see Phase 7 for retry spacing (~30s apart).

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Event never appears after several minutes | Exact casing mismatch (event type name is case-sensitive); SDK initialized with wrong environment's key; client not flushed/closed before process exit; traffic type in `track()` call doesn't match metric's `trafficType` | Check casing of event name sent vs. returned `id`; verify SDK key; add flush/close; verify traffic type |
| Can't tell if the event I see is from my test or from other traffic | Other traffic already sends this event | Use a distinctive, never-before-used event name for the initial verification pass if the codebase allows it, then rename to the real event name once confirmed — or accept the weaker signal and say so explicitly |
| No SDK exists and user hasn't said which language/framework | SDK choice depends on codebase's language and runtime (client vs. server), which the metric definition doesn't encode | Ask — don't infer the SDK from the metric's traffic type or format |
