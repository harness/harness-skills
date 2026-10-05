---
name: manage-segments
description: >-
  Create, inspect, and maintain Harness FME targeting segments (STANDARD, LARGE,
  RULE_BASED) and their per-environment key membership. Manage segment metadata
  (name, traffic type, description, tags, owners), per-environment definitions,
  and key operations (add, remove, replace). Check usage before deletion. Use
  when asked to create a segment, add keys to a segment, list segments, update
  segment metadata, remove keys, replace keys, check segment usage, or delete
  segments. Do not use for making a flag USE a segment (update-flag-targeting),
  flag CRUD (create-feature-flag, manage-flag-lifecycle), or flag discovery
  (discover-feature-flags). Trigger phrases: create segment, add keys, list
  segments, segment membership, segment targeting, update segment, remove keys,
  replace segment keys, segment definition, check segment usage, delete segment.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Manage Segments

Create, inspect, and maintain Harness FME targeting segments and their per-environment key membership. Segments are reusable audience definitions that flags reference in their targeting rules.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List traffic types | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type --json` |
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `compact: false` | `harness list feature_flag --json --limit 50` |
| List flag definitions | `harness_list` · `fme_feature_flag_definition` · `params: { feature_flag_name }` · `compact: false` | `harness list feature_flag:definition <flag> --json` |
| List segments | `harness_list` · `fme_segment` · `filters: { segment_type, status?, offset?, limit? }` · `compact: false` | `harness list segment --segment-type STANDARD --json` |
| Get segment | `harness_get` · `fme_segment` · `params: { segment_name, segment_type }` | `harness get segment <name> --segment-type STANDARD --json` |
| Create segment | `harness_create` · `fme_segment` · `body: { name, trafficType, segmentType, description?, tags?, owners? }` | `harness create segment <name> --traffic-type user --segment-type STANDARD` |
| Update segment | `harness_update` · `fme_segment` · `params: { segment_name, segment_type }` · `body: { description?, tags?, owners? }` | `harness update segment <name> --segment-type STANDARD --set description=foo` |
| Delete segment | `harness_delete` · `fme_segment` · `params: { segment_name, segment_type }` | `harness delete segment <name> --segment-type STANDARD` |
| List definitions | `harness_list` · `fme_segment_definition` · `filters: { environment_id, status?, offset?, limit? }` · `compact: false` | `harness list segment:definition --env <env-id> --json` |
| Get definition | `harness_get` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness get segment:definition <name> --env <env-id> --json` |
| Create definition | `harness_create` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }?` | `harness create segment:definition <name> --env <env-id>` |
| Update definition | `harness_update` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }` | `harness update segment:definition <name> --env <env-id> --set description=foo` |
| Delete definition | `harness_delete` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness delete segment:definition <name> --env <env-id>` |
| List keys | `harness_execute` · `fme_segment_definition` · `action="list_keys"` · `params: { segment_name, environment_id, offset?, limit? }` | `harness execute segment:list_keys <segment> --env <env-id> --limit 1` |
| Add keys | `harness_execute` · `fme_segment_definition` · `action="add_keys"` · `params: { segment_name, environment_id, replace? }` · `body: { keys, comment?, title? }` | `harness execute segment:add_keys <segment> --env <env-id> -f keys.json --comment <text>` |
| Remove keys | `harness_execute` · `fme_segment_definition` · `action="remove_keys"` · `params: { segment_name, environment_id }` · `body: { keys, comment?, title? }` | `harness execute segment:remove_keys <segment> --env <env-id> -f keys.json --comment <text>` |

## Instructions

Load references on demand:
- [concepts.md](../../references/fme/concepts.md) — segments section explains STANDARD vs LARGE vs RULE_BASED and how flags reference segments
- [write-safety.md](../../references/fme/write-safety.md) — confirm-before-write protocol (production gates, verify before/after)

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Ask for the org and project if missing. Restate: `Working in org=..., project=...`

### Phase 2: Discover intent and segment context

Ask only for what is missing:
1. **Operation** — list, create, add keys, remove keys, replace keys, update metadata, delete, check usage
2. **Segment name** (case-sensitive; discover from list when ambiguous)
3. **Segment type** (STANDARD, LARGE, or RULE_BASED; required for all segment metadata operations; choose during create)
4. **Target environments** (one or more; **List environments** to resolve names to IDs and note `isProduction`)
5. **Traffic type** (for create only; must match the flags that will use the segment; **List traffic types** to discover)

### Phase 3: Execute operation

Choose path based on intent:

#### Find / List

- **Without segment name:** **List segments** for all three types (STANDARD, LARGE, RULE_BASED) and merge. Say it took 3 calls.
- **With segment name:** If type unknown, try all three with **Get segment**. For each environment, **Get definition** and **List keys** (first page, max 100). Report key count and show up to 10 sample keys. When truncated: "≥ N keys (showing first 100)".
- Pagination: see [tool-map.md](../../references/fme/tool-map.md#pagination).

#### Create

1. Explore naming conventions from existing segments. Recommend a pattern if clear.
2. Confirm traffic type exists (**List traffic types**) and explain: "The traffic type must match the flags that will use this segment."
3. Choose segment type: **STANDARD** (explicit key list, most common), **LARGE** (optimized for very large key lists), or **RULE_BASED** (membership by rules, no key list; viewing rules supported, editing not available through native API yet). Type cannot be changed after creation.
4. Plan: segment name, type, traffic type, description, environments. STOP. Ask: "Create this segment?"
5. On confirmation: (1) **Create segment**. (2) Per environment, **Create definition**. (3) Optionally **Add keys** (if provided).
6. Verify: Re-read segment and definitions. Describe live state.

#### Add Keys

1. Parse bulk input: accept pasted list (one key per line) or file path. If CSV, extract key column. Trim whitespace, dedupe, count.
2. Show: "Adding <count> keys to <segment> in <env>. Sample: <first 10 keys>."
3. Batch ≤ 10,000 keys per call. If more, plan multiple batches and show the plan.
4. Production gate per [write-safety.md](../../references/fme/write-safety.md): If any environment is production, show: "This changes live production traffic in <env>. Add?" Otherwise: "Add these keys?"
5. STOP and wait for confirmation.
6. Execute per environment: **Add keys**. Comment: `"manage-segments: add <count> keys to <segment> in <env> — <reason>"`.
7. Verify: **List keys** (first page) and spot-check sample. Report new count: "Now <N> keys in <env> (was <M>)."

#### Remove Keys

1. Parse keys (same bulk input handling as add).
2. Show: "Removing <count> keys from <segment> in <env>. Sample: <first 10 keys>."
3. Run the [usage check](#usage-check).
4. Warn: "These keys will stop matching every flag rule that uses this segment in <env>. Remove?"
5. STOP and wait for confirmation.
6. Execute per environment: **Remove keys**. Comment: `"manage-segments: remove <count> keys from <segment> — <reason>"`.
7. Verify: **List keys** and report new count.

#### Usage check

Opt-in, before removing or replacing keys. **List flags**, then **List flag definitions** for each and scan `rules` and `targets` for the segment name in the target environment(s). Cost: one call per flag; above 50 flags, ask the user to narrow by tag, name or rollout status, or to confirm. Show which flags and environments use the segment. If skipped, report "Usage: unchecked." See [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

#### Replace All Keys (Destructive)

1. Parse new keys (bulk input).
2. **List keys** (first page; if truncated, note "≥ N").
3. Show: "Replacing all keys in <segment> in <env>. Current: <M> keys. New: <N> keys. Keys being dropped: <sample of removed keys or 'all current keys'>."
4. Run the [usage check](#usage-check).
5. Stricter confirmation: "This is a destructive replace operation. All current keys will be replaced. Replace?"
6. STOP and wait for explicit confirmation.
7. Execute: **Add keys** with replace on. Comment: `"manage-segments: replace all keys in <segment> — <reason>"`.
8. Verify: **List keys** and confirm new count matches expectations.
9. Never allow replace with empty keys unless user explicitly asked to clear the segment. If they did, say "This will clear all keys from <segment>. Clear?" before executing.

#### Update Description / Tags

- **Update segment** (metadata) or **Update definition** (per-env description).
- Use JSON Merge Patch: omit a field to leave it unchanged; pass `null` (or `[]` for tags/owners) to clear.

#### Delete Definition (One Environment)

1. Check if keys remain: **List keys** for one key.
2. If keys exist, the delete will fail with 400 `hasDependents`. Offer: "Remove all keys first? This is a separate confirmed step."
3. If confirmed, follow remove keys flow above, then retry delete.
4. Plan and confirm per [write-safety.md](../../references/fme/write-safety.md), using production wording if the environment is production. Rules that reference this segment in that environment stop matching anyone.
5. **Delete definition** (note: deletes take no comment — body is ignored).

#### Delete Segment

1. Check dependencies: 400 `hasDependents` if definitions or flags still reference it. Offer the [usage check](#usage-check).
2. Double confirmation: "This permanently deletes <segment> in all environments. This cannot be undone. Delete?"
3. STOP and wait for explicit confirmation.
4. **Delete segment**.
5. If flags still reference the segment, change their targeting first with `update-flag-targeting`.

#### RULE_BASED Rules (View Only)

The native update only changes `description`. Editing rule-based segment rules is not available through the native API yet. Say plainly: "Editing rule-based segment rules is not supported through the native API. You can view rules via **Get definition**, but editing must be done through the Harness UI."

### Phase 4: Output

After each operation, summarize per [operation-summary.md](../../templates/operation-summary.md): Operation, segment (name, type), environments, what was confirmed, verification (per env key count, sample keys, or "definition removed"), usage (checked or unchecked), flags that reference this segment, warnings, recommended next step. Include a Harness UI link when available.

## Examples

- "Create a segment for beta users with traffic type user" — Create flow.
- "Add 500 keys to the beta_users segment in staging" — Add keys flow.
- "Replace all keys in early_access with the ones from this CSV" — Replace flow.
- "Check which flags use the beta_users segment" — Usage check.
- "Delete the old_experiment segment" — Delete segment.

## Performance Notes

- One **List segments** call per segment type. Listing all types takes 3 calls.
- Key operations: batch ≤ 10,000 keys per call. Large key lists may need multiple batches.
- Usage check: cost = one call per flag. Narrow the flag set first (by tag or name) per [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `segment_type is required` (400) | Segment type is required on get/update/delete of a segment | Specify segment type (STANDARD, LARGE, or RULE_BASED) |
| `hasDependents` on delete segment | Definitions or flags still reference it | Run usage check; remove definitions first; prefer leaving segment instead |
| `hasDependents` on delete definition | Keys remain in that environment | **List keys**, confirm removal, then retry delete |
| Keys not matching flags | Traffic type mismatch, or flag rule references a different segment, or no definition in that env | Check traffic types match; verify flag rule; **Create definition** if missing |
| `keys must have at least 1` on remove keys | The key list is empty | Remove operations require at least one key |
| `keys max 10000` | Batch too large | Split into batches ≤ 10,000 keys per call |
| Rule-based segment rules not editable | Native API does not support editing rules yet | View rules via **Get definition**; edit through the Harness UI |

Generic errors: see [tool-map.md](../../references/fme/tool-map.md#common-errors).
