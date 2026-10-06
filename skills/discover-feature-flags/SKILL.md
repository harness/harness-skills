---
name: discover-feature-flags
description: >-
  Audit Harness FME feature flags across a project. Read-only; never writes.
  Four modes: inventory (list flags with metadata), rollout-report (per-env
  rollout state with stalled-promotion detection across a confirmed env
  sequence), stale-audit (find flags with no impressions via
  lastImpressionAt), pattern-search (find flags whose rule conditions
  structurally match an attribute name, matcher type, literal value, segment
  reference, or flag dependency — not a text grep). Use when asked to
  "show me all flags", "which flags are stale", "what flags are rolled out",
  "flag inventory", "flag health", "cleanup candidates", "find flags targeting
  segment X", "which flags depend on flag Y", or "find flags with rule
  matching attribute Z". Do not use for single-flag deep dive (explain-flag),
  creating flags (create-feature-flag), updating targeting
  (update-flag-targeting), archiving/deleting (manage-flag-lifecycle),
  pipeline rollouts (fme-pipeline), or code removal (cleanup-feature-flags).
metadata:
  author: Harness
  version: 1.3.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Discover Feature Flags

Audit Harness FME feature flags across a project: list all flags with metadata, show rollout status per environment, find stale flags, or search rule conditions structurally. Read-only. Never writes. Related: `explain-flag` (single flag), `cleanup-feature-flags` (code removal), `manage-flag-lifecycle` (archive).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list fme_environment --json` |
| List rollout statuses | `harness_list` · `fme_rollout_status` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list rollout_status --json` |
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `filters: { name?, tags?, rollout_status_id?, offset? }` · `compact: false` | `harness list feature_flag [--search <name>] [--status <ACTIVE\|ARCHIVED>] --limit 50 --json` |
| Get flag | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name> --json` |
| List definitions | `harness_list` · `fme_feature_flag_definition` · `params.feature_flag_name` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list feature_flag:definition <name> --json` |
| List segments | `harness_list` · `fme_segment` · `filters: { segment_type, status?, offset: 0, limit: 100 }` · `compact: false` | `harness list segment --segment-type <STANDARD\|LARGE\|RULE_BASED> --json`; cover ACTIVE and ARCHIVED with declared status filters |
| List experiments | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, status: ["ACTIVE", "PAUSED"], offset: 0, limit: 100 }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <name> --status ACTIVE --json`, then again with `--status PAUSED` |

For each filter: apply it server-side if declared by the installed transport (verify via `--help`); otherwise fetch the complete inventory and filter client-side. Paginate every list to completion per [tool-map.md](../../references/fme/tool-map.md#pagination).

## Output

Fixed shape per mode:

**Inventory:** `| Flag | Traffic type | Status | Rollout status | Tags | Owners | Created | Updated |`

**Rollout report:** `| Flag | <Env 1>* | <Env 2>* | … | Promotion | Notes |` (production envs `*`; cells use actual treatment names/percentages, `killed→<fallback>`, `targeted`, `limited`, `missing`, `unknown` or `archived`). Promotion: `stalled?`, `ahead`, `ok`, `behind (no alert)`, `divergence`, `both killed`, `missing`, `unknown`, `intended ✓`, `not comparable`, `archived`, or `—` for neutral-only. Label each hop in multi-env chains; see [promotion-check.md](references/promotion-check.md).

**Stale audit:** `| Flag | Bucket | Last Impression Per Env | Config | Next Step |` (buckets: stale / active / unknown / never evaluated; verdicts: ready / caution / blocked)

**Pattern search:** `| Flag | Env | Rule # | Combiner | Negated | Matcher type | Predicate match | Status | Notes |` (coverage footer: matched N / no-match M / unparsed P / unchecked U; see [rule-patterns.md](references/rule-patterns.md))

Summary: counts per class, truncation line if paginated, hand-offs to sibling skills.

## Instructions

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Restate: `Working in org=..., project=...`.

### Phase 2: Collect inputs

Ask only for missing items relevant to the user's goal:
- **Mode:** inventory (default) / rollout-report / stale-audit / pattern-search. Infer from prompt.
- **Filters:** name substring, tag, rollout status name, traffic type, status (ACTIVE / ARCHIVED), owner — apply server-side where declared; client-side otherwise on the complete inventory.
- **Environment subset** (rollout-report / stale-audit / pattern-search): default all.
- **Staleness threshold** (stale-audit only): default 30 days per [concepts.md](../../references/fme/concepts.md#staleness-and-readiness).
- **Pattern-search predicates:** collect per [rule-patterns.md §Clarification](references/rule-patterns.md#clarification-protocol).
- **Promotion check:** both the environment sequence and intended target treatment must be confirmed before promotion classifications; otherwise show neutral differences. See [promotion-check.md §Inputs](references/promotion-check.md#required-inputs).

### Phase 3: List environments and rollout statuses

List environments through every page: ID → `{ name, isProduction }`. Default display order: non-production first, production last. **The environment sequence for promotion checks must be confirmed explicitly by the user — do not derive order from `isProduction` alone.** List rollout statuses through every page: name → ID. Apply pagination completeness checks from [tool-map.md](../../references/fme/tool-map.md#pagination).

### Phase 4: List flags

Apply declared server-side filters (name, tags, rollout_status_id); handle remaining filters client-side on the complete inventory. Page through every offset to a short page. **Inventory mode stops here.** Skip to Phase 6.

**Cost guard (rollout-report / stale-audit / pattern-search):** If >50 flags after filtering, STOP: "This will fetch N paginated definition inventories. Narrow by tag, name, rollout status, or status, or confirm to proceed." See [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

### Phase 5: List and classify definitions

For each flag, list definitions (all pages, `filters.limit: 100`, advance offset). Failed or skipped pages → incomplete; never label unseen definitions missing.

**Rollout-report:** Classify each (flag, env) cell per [concepts.md](../../references/fme/concepts.md): killed → no definition → allocation < 100 → rules/targets present → defaultRule shape. For the confirmed promotion sequence, apply [promotion-check.md](references/promotion-check.md) to produce the Promotion column. Archived flags (global `status: ARCHIVED`): include in table as `archived` row; exclude from stalled/divergence alerts.

**Stale-audit:** Buckets per [concepts.md §Staleness](../../references/fme/concepts.md#staleness-and-readiness). `impressions.lastImpressionAt`: ISO-8601 (`null` = never evaluated; absent = unknown). For ready/caution candidates, run the experiment check (ACTIVE and PAUSED) per [write-safety.md](../../references/fme/write-safety.md#experiment-check). Next Step: hand off to `cleanup-feature-flags` (code) or `manage-flag-lifecycle` (archive).

**Pattern-search:** Apply structural rule matching per [rule-patterns.md](references/rule-patterns.md). To resolve a segment name to its type, list that segment type's metadata via List segments (one complete paginated inventory per type; reuse across all flags). Killed flag definitions: scan rules but annotate matches `inactive (killed)`. Archived flags included by the requested status filter: retain structural matches and annotate `inactive (archived)`; do not imply live exposure.

### Phase 6: Output

Present the fixed table for the mode. Summary counts per class or bucket. Pagination alone is not truncation: report truncation/incomplete coverage only if the inventory was not finished.

**Hand-offs:** Single-flag → `explain-flag`. Cleanup candidate → `cleanup-feature-flags`. Archive → `manage-flag-lifecycle`. Update targeting → `update-flag-targeting`. Pipeline rollout → `fme-pipeline`.

## Examples

- "Show me all feature flags" — Inventory mode.
- "Which flags are stale?" — Stale-audit mode, default 30 days.
- "Where is `new-checkout-flow` rolled out?" — Route to `explain-flag` for one flag.
- "List flags with tag `payments`" — Inventory mode, filter by tag.
- "Find cleanup candidates" — Stale-audit mode, bucket `stale` + fully rolled out.
- "Show rollout status for all flags in production" — Rollout-report mode, environment subset.
- "Find flags that target segment `beta-users` (STANDARD)" — Pattern-search, segment reference predicate.
- "Which flags depend on `flag-A`?" — Pattern-search, flag dependency predicate (`IN_SPLIT`).
- "Are flags stalled between staging and prod?" — Rollout-report with promotion check; requires confirmed env IDs, sequence, and intended treatment per flag.

## Performance Notes

- **Inventory mode:** One paginated flag inventory; no definitions.
- **Rollout-report / stale-audit / pattern-search:** One paginated definition inventory per flag. Cost guard at 50 flags; narrow first by tag, name, rollout status, or status.
- **Stale-audit experiment check:** Run only for ready/caution candidates, not every flag. Paginate ACTIVE and PAUSED separately.
- **Pattern-search segment resolution:** List each needed segment type once; reuse across all flags.
- **Parallelizing definition reads:** Batch list-definitions calls where the client supports parallel calls.
- **Pagination:** See [tool-map.md](../../references/fme/tool-map.md#pagination).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `impressions.lastImpressionAt` absent | Treat as `unknown` bucket; never infer "unused" |
| Definitions call fails with 404 | Re-list flags; confirm exact name (case-sensitive) |
| "Too many requests" or timeout | Narrow by tag, rollout status, or name; or process in batches |
| Pattern-search returns unparsed rows | See [rule-patterns.md §Unparsed Shapes](references/rule-patterns.md#unparsed-shapes) |
| Promotion check cannot compare | Confirm env IDs, sequence, and intended treatment per [promotion-check.md](references/promotion-check.md) |

See [tool-map.md](../../references/fme/tool-map.md#common-errors) for generic errors.
