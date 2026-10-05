---
name: discover-feature-flags
description: >-
  Audit Harness FME feature flags across a project — list all flags, show
  rollout status per environment, and identify stale or cleanup candidates.
  Read-only; never writes flags or definitions. Three modes: inventory (list
  flags with metadata), rollout-report (classify each flag per environment as
  killed/ramping/fully rolled out), or stale-audit (find flags with no
  impressions, using impressions.lastImpressionAt from definitions). Use when asked to
  "show me all flags", "which flags are stale", "what flags are rolled out",
  "flag inventory", "flag health", or "cleanup candidates". Do not use for
  single-flag deep dive (explain-flag), creating flags (create-feature-flag),
  updating targeting (update-flag-targeting), archiving/deleting
  (manage-flag-lifecycle), pipeline rollouts (fme-pipeline), or code
  removal (cleanup-feature-flags).
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Discover Feature Flags

Audit Harness FME feature flags across a project: list all flags with metadata, show rollout status per environment, or find stale flags. Read-only. Never writes. Related: `explain-flag` (single flag), `cleanup-feature-flags` (code removal), `manage-flag-lifecycle` (archive).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List rollout statuses | `harness_list` · `fme_rollout_status` · `compact: false` | `harness list rollout_status --json` |
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `filters: { name?, tags?, rollout_status_id?, offset? }` · `compact: false` | `harness list feature_flag --search <name> --tags <tag> --rollout-status-id <id> --json` |
| Get flag | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name> --json` |
| List definitions | `harness_list` · `fme_feature_flag_definition` · `params.feature_flag_name` · `filters: { offset?, limit? }` · `compact: false` | `harness list feature_flag:definition <name> --json` |
| List experiments | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, status: ["ACTIVE", "PAUSED"] }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <name> --status ACTIVE --json`, then again with `--status PAUSED` |

## Output

Fixed shape per mode:

**Inventory:** `| Flag | Traffic type | Status | Rollout status | Tags | Owners | Created | Updated |`

**Rollout report:** `| Flag | <Env 1>* | <Env 2>* | … | Notes |` (mark production envs; cells: `on 100%`, `on 25 / off 75`, `killed→off`, `targeted`, `—`)

**Stale audit:** `| Flag | Bucket | Last Impression Per Env | Config | Next Step |` (buckets: stale / active / unknown / never evaluated; verdicts: ready / caution / blocked)

Summary: counts per class, truncation line if paginated, hand-offs to sibling skills.

## Instructions

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Restate: `Working in org=..., project=...`.

### Phase 2: Collect inputs

Ask only for missing items relevant to the user's goal:
- **Mode:** inventory (default) / rollout-report / stale-audit. Infer from prompt.
- **Filters:** name substring, tag, rollout status name, traffic type (client-side), status (ACTIVE / ARCHIVED; filter client-side if the list doesn't support it), owner (client-side).
- **Environment subset** (rollout-report / stale-audit only): default all.
- **Staleness threshold** (stale-audit only): default 30 days per [concepts.md](../../references/fme/concepts.md#staleness-and-readiness).

### Phase 3: List environments and rollout statuses

**List environments** to build a map: ID → `{ name, isProduction }`. Sort: non-production first, production last.

**List rollout statuses** to build a map: name → ID (for resolving rollout status by name).

### Phase 4: List flags

**List flags**, filtering by name (substring), tags, rollout status ID, and pagination offset. Apply additional client-side filtering for status (ACTIVE / ARCHIVED), trafficType, and owners.

Stop pagination when a page returns fewer than requested. Report truncation: "First 50 of at least N flags". See [tool-map.md](../../references/fme/tool-map.md#pagination).

**Inventory mode stops here.** Skip to Phase 6.

### Phase 5: List definitions (rollout-report / stale-audit only)

For each flag (after client-side filtering), **list definitions**. Returns all environments for one flag.

**Cost guard:** If >50 flags after filtering, STOP and warn: "This will fetch definitions for N flags (N list calls). Narrow by tag, name, rollout status, or status to reduce cost, or confirm to proceed." See [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

Classify each (flag, environment) cell per [concepts.md](../../references/fme/concepts.md): killed (isKilled), no definition, fully rolled out, ramping, targeted, limited exposure. Evaluation order: killed → no definition → trafficAllocation < 100 → rules/targets present → defaultRule shape.

**Stale audit:** Buckets per [concepts.md](../../references/fme/concepts.md#staleness-and-readiness): stale / active / unknown / never evaluated. Field is `impressions.lastImpressionAt` (ISO-8601 date-time; `null` = never evaluated; absent = unknown). For flags that would otherwise be **ready** or **caution**, run the [experiment check](../../references/fme/write-safety.md#experiment-check) with **List experiments** (ACTIVE and PAUSED). Next Step column: ready / caution / blocked verdict per [concepts.md](../../references/fme/concepts.md#staleness-and-readiness) → hand off to `cleanup-feature-flags` (code) or `manage-flag-lifecycle` (archive).

### Phase 6: Output

Present the fixed table for the mode. Summary counts per class or bucket. If paginated, report truncation.

**Hand-offs:** Single-flag → `explain-flag`. Cleanup candidate → `cleanup-feature-flags`. Archive → `manage-flag-lifecycle`. Update targeting → `update-flag-targeting`. Pipeline rollout → `fme-pipeline`.

## Examples

- "Show me all feature flags" — Inventory mode.
- "Which flags are stale?" — Stale-audit mode, default 30 days.
- "Where is `new-checkout-flow` rolled out?" — Route to `explain-flag` for one flag.
- "List flags with tag `payments`" — Inventory mode, filter by tag.
- "Find cleanup candidates" — Stale-audit mode, bucket `stale` + fully rolled out.
- "Show rollout status for all flags in production" — Rollout-report mode, environment subset.

## Performance Notes

- **Inventory mode:** One list call (flags only), no definitions. Fast.
- **Rollout-report / stale-audit:** N list calls (one per flag). Cost guard at 50 flags. Narrow first by tag, name, rollout status, or status.
- **Stale-audit experiment check:** One or two calls per flag that's ready or caution after the impressions check. Run this check only for candidates, not every flag.
- **Pagination:** See [tool-map.md](../../references/fme/tool-map.md#pagination).
- **Parallelizing definition reads:** Batch list-definitions calls if the client supports parallel calls.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `impressions.lastImpressionAt` absent | Treat as `unknown` bucket; never infer "unused" |
| Definitions call fails with 404 | Re-list flags; confirm exact name (case-sensitive) |
| "Too many requests" or timeout | Narrow by tag, rollout status, or name; or process in batches |

See [tool-map.md](../../references/fme/tool-map.md#common-errors) for generic errors.
