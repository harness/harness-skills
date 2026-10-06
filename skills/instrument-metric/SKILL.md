---
name: instrument-metric
description: >-
  Wire up a track() call for a metric's event, placed at the real outcome, and
  verify it arrives. Doesn't create the metric (create-metric) or choose it
  (choose-metric). Trigger phrases: instrument this event, add a track call,
  wire up tracking, verify the event arrives.
metadata:
  author: Harness
  version: 1.2.1
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Instrument Metric

Wire up the `track()` call an FME metric needs, then verify the event is actually arriving — don't declare success on code changes alone. Key = the same key `getTreatment` uses (attribution fact); value units must match the metric's `format` (ms vs s, dollars vs cents) — a wrong unit gives silently wrong results. Related: `/create-metric` creates metrics; `/choose-metric` recommends which metrics to use.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| Get metric | `harness_get` · `fme_metric` · `params: { metric_id }` | `harness get metric <id> --json` |
| Get event type | `harness_get` · `fme_event_type` · `params: { event_type_id }` | `harness get event_type <event-name> --json` |

## Instructions

### Phase 1: Establish scope

See [scope-establishment.md](../../references/scope-establishment.md). Confirm the Harness organization and project before any get operation, separately from the local application repository and intended runtime environment. Never derive Harness scope from the repo name. If application source or runtime access is unavailable, stop at guidance and label implementation/delivery unverified — CLI/MCP access does not grant application access.

### Phase 2: Detect the SDK

Search existing FME `track()` calls first — they give the signature, key source, traffic type and wrapper in one shot; mirror them. See [sdk-patterns.md](../../references/fme/sdk-patterns.md) for SDK detection (searching for existing `track()` calls or dependency manifests) and identifying whether it's a client-side or server-side SDK — the two have different `track()` signatures.

### Phase 3: Install and initialize if needed

Detect the package manager from lockfiles. **Stop condition:** if no SDK is present, propose the runtime-appropriate SDK/package and get confirmation before installing or changing its version.

Confirm environment, client/server mode, and the existing environment-variable or secret-manager **reference**, not its value. SDK keys are not Harness admin API tokens; never put a server-side key in a browser bundle. These metric/event tools do not retrieve SDK keys. An authorized user must provision missing credentials through the supported UI/admin workflow. Reuse the application's config pattern; never hardcode keys, ask for pasted secrets, dump credential files, or expose values in tools/output. Inspect only non-secret configuration metadata; flag an environment mismatch for confirmation without printing values. Reuse existing deployment endpoint settings — don't infer custom hosts.

### Phase 4: Find the right placement

Locate the exact point where the tracked action actually completes (e.g. after a successful purchase confirmation from the payment provider, not the button click that starts the flow). Wrong placement produces misleading metric data with no error to catch it. Placement signals: existing analytics calls ([Segment, Amplitude, Mixpanel, gtag, PostHog](../../references/fme/sdk-patterns.md#other-analytics-calls)) for the same action, submit handlers, API route completions, mutation success callbacks, `TODO: track` comments. Identify the candidate `file:line` now; defer call approval until the full event contract is known (Phases 5–6). Ensure the event fires once per intended outcome, not again on re-renders, retries, or both client and server.

**Stop condition:** if there's more than one plausible placement (e.g. optimistic UI vs. server-confirmed success), ask the user which one matches the metric's intent rather than guessing.

### Phase 5: Confirm the event contract

The event name is case-sensitive and must match exactly what `/create-metric` used or will use. If the metric already exists, **Get metric** and read the full contract, not just the name: `trafficType`, `aggregation`/`format` (which determine value units and whether a numeric `value` is needed at all), and whether the value comes from `propertyForValue` or the positional `value` argument, plus any required `properties` for filters. If the metric doesn't exist yet, agree all of this with the user now — don't defer it to Phase 6 — so `/create-metric` can reference the same contract later without a mismatch. **Do not draft or get approval for the `track()` call in Phase 6 until this contract is settled**; writing the call against a guessed traffic type, aggregation, or value source is the same kind of guess Phase 4 placement already avoids.

For an existing metric, resolve the selected event's exact `eventTypeId`; if it uses multiple base/filter/trigger events, ask which one needs instrumentation. If RUM or an integration already covers this outcome, check the existing producer and event inventory before adding a duplicate call. Inventory visibility alone is historical evidence, not proof of current delivery — see [metric-design.md](../../references/fme/metric-design.md#auto-created-metrics).

### Phase 6: Write and test the `track()` call

Show the candidate `file:line` and exact call using the Phase 5 contract, and **wait for confirmation before editing**. Respect the installed SDK's readiness lifecycle and existing initialization/wrapper; don't create a second client for this event.

Use the signature for the SDK's mode, reusing existing context objects (user key, traffic type / attributes) rather than constructing new ones. See [sdk-patterns.md](../../references/fme/sdk-patterns.md) for the illustrative server-side vs. client-side `track()` shapes — then confirm the exact signature against the installed SDK's version/types or an existing call in the codebase, since the reference is pseudocode, not a promised per-language spec.

Key = the same key `getTreatment` uses (attribution fact). Value units must match the metric's `format` (ms vs s, dollars vs cents) from the Phase 5 contract — a wrong unit gives silently wrong results. `trafficType` must be the metric's traffic type (Phase 5). Pass a numeric value only if the contract calls for it (`TOTAL`/`AVERAGE` without `propertyForValue`); `COUNT`/`RATE`, or any aggregation reading from a property, need none — don't invent a placeholder value to fill a positional slot. Pass `properties` whenever the contract uses property filters or `propertyForValue`. If the codebase has an existing tracking wrapper/helper, extend it rather than calling the SDK directly.

Add or update focused tests using the repo's existing test framework: exact event name, evaluation subject key, traffic type, units/value source/properties, once on the intended outcome, and no success event on failure. Run them before asking for a live trigger. A mocked `track()` assertion verifies code behavior, **not ingestion**.

### Phase 7: Trigger and verify

First confirm the running application contains the edited revision and is connected to the intended environment; record the revision/build and environment as non-secret metadata. If it needs a restart/build/deployment, ask the user to perform or authorize that step—do not deploy automatically. Without it, stop at "code tested; live delivery unverified." Agree on an authorized integration test or runtime telemetry source that can establish actual delivery; the event inventory alone cannot.

Ask the user to trigger the action (or state clearly that you cannot execute their running application yourself), then verify: **Get event type** using the event name exactly. The response has only `id` and `trafficTypes` — check the returned `trafficTypes` includes the metric's traffic type; a hit under the wrong traffic type doesn't confirm this event. Event types with traffic in the last 30 days (across the whole project and all environments, not "currently flowing" in any narrower sense) return 200; 404 = absent or idle > 30 days.

Allow for asynchronous ingestion. As an initial check, retry roughly 30s apart for about 2 minutes; this is a polling heuristic, not a delivery guarantee. If still absent, report delivery unverified and investigate rather than declaring the code broken. A 200 confirms only historical event-type visibility across the project/environments, not that your test invocation produced it or reached the intended environment (there's no per-event or per-environment lookup).

If you're checking an event tied to an existing, previously working metric (not a fresh test), a 404 can mean either "never instrumented" or "instrumented but idle for 30+ days," not just "broken." Ask whether the flow that fires it has actually run recently before concluding the tracking call is wrong. If the user hasn't actually triggered the action yet, the result is **unknown**, not "no" — don't report a negative you haven't observed.

Most SDKs buffer events. For short-lived processes/tests, use and await the installed SDK's supported flush/shutdown behavior before exit. Don't flush per event in long-running applications or destroy a shared client just to force delivery.

Summarize separately: (1) event name/traffic type and **visible in the project's last-30-day inventory: yes/no/unknown**, (2) **code tests: passed/failed/not run**, (3) **target-environment test delivery and experiment attribution: verified separately/unverified**, naming the evidence. Only approved runtime telemetry or a real integration check can verify delivery; mocked tests and a bare 200 cannot. State the next step (`/create-metric` or `/manage-experiments`) and any remaining verification.

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
| Event never appears after several minutes | Exact casing mismatch (event type name is case-sensitive); SDK initialized with wrong environment's key; client not flushed/closed before process exit; traffic type in `track()` call doesn't match metric's `trafficType` | Check exact event name and traffic type; confirm environment and credential reference without exposing values; check readiness and SDK-specific shutdown behavior |
| Can't tell if the event I see is from my test or from other traffic | Other traffic already sends this event | Don't rename the event for a one-off verification pass — it creates a second, duplicate event type and can hide a real naming mismatch. Instead verify the agreed event name with a mocked/automated test (Phase 6) and treat a live 200 as corroborating, not proof |
| No SDK exists and user hasn't said which language/framework | SDK choice depends on codebase's language and runtime (client vs. server), which the metric definition doesn't encode | Ask — don't infer the SDK from the metric's traffic type or format |
