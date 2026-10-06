# FME SDK Patterns

Locate FME SDK usage in application code: detection, evaluation calls, tracking calls, and search patterns. Wrappers and enums often hide direct SDK calls—search the flag key string first. Search the **application** repo, not the skills repo.

## SDK Detection

Check dependencies and imports for these packages:

| Signal | Grep for |
|--------|----------|
| FME / Split server (Node) | `getTreatment`, `@splitsoftware/splitio` |
| FME / Split browser / React | `getTreatment("`, `useSplitTreatments`, `@splitsoftware/splitio-react` |
| FME / Split Python | `get_treatment`, `splitio` |
| FME / Split Go | `.Treatment(`, `splitio` |
| FME / Split Java | `getTreatment(`, `io.split.client` |
| FME / Split .NET | `GetTreatment`, `SplitFactory` |
| FME / Split Ruby | `get_treatment` |
| FME / Split iOS | `getTreatment`, `SplitClient` |
| FME / Split Android | `getTreatment`, `SplitClient` |
| OpenFeature | `getBooleanValue`, `getStringValue`, `@openfeature/` |
| Harness FF SDK | `@harnessio/ff-`, `boolVariation`, `variation(`, `useFeatureFlag` |
| Custom wrapper | flag key + `isEnabled`, `getFlag`, `FeatureFlagService` |

## Evaluation Call Patterns

**Server-side SDKs** (Java, Node, Python, Go, Ruby, .NET, PHP): `getTreatment(key, "flag-key")` or language equivalent (`get_treatment`, `.Treatment(`). Client must be initialized first (factory/manager → client).

**Client-side SDKs** (browser JS, iOS, Android, React, React Native): `getTreatment("flag-key")` only (key bound at client creation). React: `useSplitTreatments` hook.

**Batch / flag-set APIs** — the key may never appear as a literal string:
- Multiple flags: `getTreatments(key, ["flag1", "flag2"])` or `get_treatments`
- With config: `getTreatmentWithConfig`, `getTreatmentsWithConfig` (or `_with_config` variants)
- Flag sets: `getTreatmentsByFlagSet(key, "set-name")` or `getTreatmentsByFlagSets` (also `_with_config` variants)

If a flag is only referenced via a flag set, a plain key grep returns nothing.

**Classic FF vs FME:** Harness Classic FF (`@harnessio/ff-*`) is a separate system. If the repo uses only Classic FF and FME has no such flag, stop.

## Tracking Calls (`track()`)

The signatures below are illustrative pseudocode, not a literal per-language reference — the actual parameter order, casing (`track`/`Track`), and optional-argument handling vary by SDK and version. Before writing a call, inspect the installed SDK's version and its actual method signature/types (type definitions, installed package docs, or an existing call in the codebase) rather than assuming the pattern here applies verbatim.

**Server-side SDKs (illustrative):** `client.track(key, trafficType, eventType, value?, properties?)`. All params explicit.

**Client-side SDKs (illustrative):** `client.track(trafficType, eventType, value?, properties?)` (key bound at init), or `client.track(eventType, value?, properties?)` if traffic type also bound.

`value` is a number, only needed for aggregations TOTAL/AVERAGE when the metric doesn't read from a property (`propertyForValue`). When the value is meant to come from a property instead, don't guess a universal positional form for "value omitted" — check the installed SDK's actual signature for how it expects a skipped value (`null`, `undefined`, omitted trailing arg, or a named-args/options object), since this differs by language and SDK version. `properties` is a map/dict for property filters or `propertyForValue`.

## Search Patterns

**Grep/rg regexes** for finding evaluation sites:
- Basic: `grep -rE 'getTreatment\(|get_treatment\(|\.Treatment\(' <src-dir>`
- Batch: `grep -rE 'getTreatments\(|ByFlagSet\(|_with_config\(' <src-dir>`
- React: `grep -r 'useSplitTreatments' <src-dir>`
- Tracking: `grep -rE '\.track\(|\.Track\(|client\.track\(' <src-dir>` (include the capitalized `.Track(` form for Go/.NET SDKs)

**Dynamic keys** (`"prefix-" + id`, `` `flag-${id}` ``): if found, human review required.

**Localhost / offline config:** `split.yaml`, `.split`, `split.yml`, `localhost` sections in SDK bootstrap, test fixtures.

**Also search:** tests, config, fixtures, comments, control branches (`control`, `defaultTreatment`), fallback `else` paths.

## Other analytics calls

These mark outcomes the team already measures and are placement signals for FME `track()` calls. Look for them when deciding where to add `track()`:

| Tool | Pattern |
|------|---------|
| Segment | `analytics.track(` |
| Mixpanel | `mixpanel.track(` |
| Amplitude | `amplitude.track(`, `logEvent(` |
| Google Analytics | `gtag('event'` |
| PostHog | `posthog.capture(` |
