# Code search patterns

Always search the flag **key string** first. Wrappers and enums often hide the SDK call.

Search the **application** repo (not this skills repo).

## Find the SDK family

Check dependencies and imports (`package.json`, `go.mod`, `pom.xml`, `build.gradle`, `Gemfile`, `*.csproj`):

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

**Node vs browser Split:** server uses `getTreatment(key, "flag-key")`; browser uses `getTreatment("flag-key")` only.

**Batch / flag-set APIs** — the key may never appear as a literal string:

| API | Grep for (case-insensitive) |
|-----|----------|
| Multiple flags at once | `getTreatments(`, `get_treatments(`, `Treatments(` |
| Treatment with config | `TreatmentWithConfig`, `TreatmentsWithConfig`, `treatment_with_config`, `treatments_with_config` |
| Flag sets | `ByFlagSet`, `by_flag_set` (covers `getTreatmentsByFlagSet(s)`, `get_treatments_by_flag_set(s)`, `TreatmentsByFlagSet(s)`, and the `WithConfig` variants) |

If the flag is only referenced via a flag set, a plain key grep returns nothing → **caution**.

**Classic FF vs FME:** this skill’s readiness and archive use FME. If the repo only uses `@harnessio/ff-*` and FME has no such flag, stop.

## Localhost / offline mode

Search config files that seed flags without SDK calls:

- `split.yaml`, `.split`, `split.yml`
- `localhost` sections in SDK bootstrap config
- Test fixtures that mock Split responses

## Also search

- Tests, config, fixtures, comments
- Control branches: `control`, `defaultTreatment`, fallback `else` paths tied to the flag
- Dynamic keys (`"prefix-" + id`, `` `flag-${id}` ``) — if found, stop automated removal

## After removal

Re-run the key search plus batch/flag-set patterns. Remaining hits should be homonyms or other repos.
