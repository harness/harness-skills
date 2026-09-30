---
name: instrument-metric
description: >-
  Add a Split/FME track() call for a metric's event and verify it arrives
  via fme_event_type. Doesn't create the metric or choose it - see
  create-metric / choose-metric. Trigger phrases: instrument this event,
  add a track call, wire up tracking, verify the event arrives.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 server (harness-mcp-v2) with fme_event_type, used
  for verification only - SDK install and the track() call itself are local
  code edits, not MCP calls. Verification is coarse (event-type existence,
  not per-invocation acknowledgment) - see Step 6.
---

# Instrument Metric

Wire up the `track()` call an FME metric needs, then verify the event is
actually arriving - don't declare success on code changes alone.

## Prerequisites

Establish `org_id` + `project_id` for the Step 4 and Step 6 lookups.

## Instructions

### Step 1: Detect the SDK

Search the codebase for existing `client.track(` (or SDK-specific
equivalents) first - an existing call reveals the SDK and calling
convention already in use, which you should match rather than introducing
a second style. If none exist, check the dependency manifest
(`package.json`, `pom.xml`, `requirements.txt`, etc.) for a Split SDK
package to identify the language/SDK, and whether it's a client-side or
server-side SDK - the two have different `track()` signatures.

### Step 2: Install and initialize if needed

**Stop condition:** if no SDK is present, ask before installing - state
which SDK/package you'd add and get confirmation rather than picking a
version unilaterally. Ask the user which environment's SDK key to use
(server-side and client-side keys differ) and add initialization matching
existing config patterns in the codebase (env var naming, secret
management) - never hardcode the key.

### Step 3: Find the right placement

Locate the exact point where the tracked action actually completes (e.g.
after a successful purchase confirmation from the payment provider, not
the button click that starts the flow). Wrong placement produces
misleading metric data with no error to catch it.

**Stop condition:** if there's more than one plausible placement (e.g.
optimistic UI vs. server-confirmed success), ask the user which one
matches the metric's intent rather than guessing.

### Step 4: Confirm the event name

The event name (`eventTypeId` in `fme_metric`'s `baseEventTypes`) is
case-sensitive and must match exactly what `/create-metric` used or will
use. If the metric already exists, get its `baseEventTypes[].eventTypeId`
from `fme_metric` and use that exact string. If the metric doesn't exist
yet, agree on the event name with the user now so `/create-metric` can
reference it later without a mismatch.

### Step 5: Write the `track()` call

Use the SDK's correct signature for its mode (client vs. server), reusing
existing context objects (user key, traffic type / attributes) rather than
constructing new ones. Pass a numeric value only if the metric's
`aggregation` is `TOTAL`/`AVERAGE` and it doesn't read the value from a
property (`baseEventTypes[].propertyForValue`); `COUNT`/`RATE` need none.
If the codebase has an existing tracking wrapper/helper, extend it rather
than calling the SDK directly.

### Step 6: Trigger and verify

Ask the user to trigger the action (or state clearly that you cannot
execute their running application yourself), then verify:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_event_type"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters:
    name: "<eventTypeId>"
```

The `name` filter is a case-insensitive **substring** match, not exact - a
search for `signup` also matches `signup_v2` or `Signup`. Confirm the
returned `id` string matches your event name byte-for-byte (including
case) before treating it as a hit; `fme_metric` matching is case-sensitive
even though this list filter isn't.

A new event type takes about 90s from `track()` to appear in
`fme_event_type`. If absent, retry ~30s apart and don't conclude failure
before ~2 minutes. A hit confirms the event type is flowing in aggregate,
not that your test invocation produced it (there's no per-event lookup). If
other traffic already sends this event, treat a hit as encouraging, not
proof; a never-before-seen event name is a much stronger signal.

`fme_event_type` only lists event types with events received in the last
30 days - if you're checking an event tied to an existing, previously
working metric (not a fresh test), an empty result can mean either "never
instrumented" or "instrumented but idle for 30+ days," not just "broken."
Ask whether the flow that fires it has actually run recently before
concluding the tracking call is wrong.

## Examples

- "Add tracking for checkout completion" - Steps 1-3 to place the call
  after payment confirmation, Step 4 to agree the event name with
  `/create-metric`'s expected `checkout_completed`, Step 5-6 to write and
  verify.
- "Is the signup event actually flowing?" - skip to Step 6 only, using the
  event name already in an existing metric; if absent, apply the 30-day
  idle caveat before calling it broken.
- "Wire up a new SDK for this service" - Steps 1-2 focus (no `track()` call
  yet), confirm before installing.

## Performance Notes

- Check for an existing `track()` pattern before assuming no SDK is
  present - a partial/unused SDK dependency without a live call is a
  different situation from no SDK at all.
- Don't poll `fme_event_type` in a tight loop - see Step 6 for retry
  spacing.

## Troubleshooting

### Event never appears after several minutes
Check, in order: exact casing of the event name vs. what was sent (the
`fme_event_type` list filter is case-insensitive and will mask a casing
mismatch - compare the returned `id` string directly, not just whether the
filtered list was non-empty); whether the SDK was initialized with the
correct environment's key (wrong environment sends the event somewhere
else, not nowhere); whether the client was flushed/closed before process
exit (buffered events can be dropped on abrupt termination, especially in
short-lived scripts/serverless functions); whether the traffic type used
in the `track()` call matches the metric's expected `trafficType`.

### Can't tell if the event I see is from my test or from other traffic
Use a distinctive, never-before-used event name for the initial
verification pass if the codebase allows it, then rename to the real event
name once confirmed - or accept the weaker signal and say so explicitly
rather than claiming certainty the API doesn't back up.

### No SDK exists and the user hasn't said which language/framework
Ask - don't infer the SDK from the metric's traffic type or format; the
SDK choice depends on the codebase's language and runtime (client vs.
server), which the metric definition doesn't encode.
