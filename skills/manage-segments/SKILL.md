---
name: manage-segments
description: >-
  Create, inspect, and maintain Harness FME segments (STANDARD, LARGE,
  RULE_BASED). Manage metadata, select type-specific definition and membership
  workflows, and check usage before deletion. Use
  when asked to create a segment, add keys to a segment, list segments, update
  segment metadata, remove keys, replace keys, check segment usage, or delete
  segments. Do not use for making a flag USE a segment (update-flag-targeting),
  flag CRUD (create-feature-flag, manage-flag-lifecycle), or flag discovery
  (discover-feature-flags). Trigger phrases: create segment, add keys, list
  segments, segment membership, segment targeting, update segment, remove keys,
  replace segment keys, segment definition, check segment usage, delete segment.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires Harness MCP or CLI; available definition and membership operations depend on segment type and tool version
---

# Manage Segments

Manage all three FME segment types: **STANDARD**, **LARGE**, and **RULE_BASED**. Use each type's membership model rather than treating every segment as a standard key list. Distinguish a missing operation in the current tool version from product support.

## Tools

Works through Harness MCP or CLI. [tool-map.md](../../references/fme/tool-map.md#segment-type-capabilities) distinguishes metadata for all three types from type-specific operations. `STANDARD` in metadata examples is a placeholder for the selected type; the definition/key rows document the audited STANDARD routes, not a universal segment API.

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
| List keys | `harness_execute` · `fme_segment_definition` · `action="list_keys"` · `params: { segment_name, environment_id, offset?, limit? }` | **Not supported in the CLI** (absent from the `fme` spec) — use MCP, or stop and tell the user key listing needs the MCP server |
| Add keys | `harness_execute` · `fme_segment_definition` · `action="add_keys"` · `params: { segment_name, environment_id, replace? }` · `body: { keys, comment?, title? }` | **Not supported in the CLI** (absent from the `fme` spec) — use MCP, or stop and tell the user key operations need the MCP server |
| Remove keys | `harness_execute` · `fme_segment_definition` · `action="remove_keys"` · `params: { segment_name, environment_id }` · `body: { keys, comment?, title? }` | **Not supported in the CLI** (absent from the `fme` spec) — use MCP, or stop and tell the user key operations need the MCP server |

## Instructions

Load references on demand:
- [concepts.md](../../references/fme/concepts.md) — segments section explains STANDARD vs LARGE vs RULE_BASED and how flags reference segments
- [write-safety.md](../../references/fme/write-safety.md) — confirm-before-write protocol (production gates, verify before/after)

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Ask for the org and project if missing. Restate: `Working in org=..., project=...`

### Phase 2: Discover intent and segment context

Ask only for what is missing:
1. **Operation** — list, create, change membership, edit rules/exclusions, update metadata, delete, check usage
2. **Segment name** (case-sensitive; discover from list when ambiguous)
3. **Segment type** (STANDARD, LARGE, or RULE_BASED; required for all segment metadata operations; choose during create)
4. **Target environments** (one or more; **List environments** to resolve names to IDs and note `isProduction`)
5. **Traffic type** (for create only; must match the flags that will use the segment; **List traffic types** to discover)

### Phase 3: Execute operation

Resolve type, then choose the workflow below. Discover the exact operation/schema exposed by the installed MCP/CLI before a write. If that operation is missing, offer an approved alternate tool or the corresponding administration workflow; do not call another type's endpoint, silently switch scope contracts, or declare the segment type unsupported.

| Type | Membership model | Workflow |
|------|------------------|----------|
| STANDARD | Explicit key set | Definition and key flows below; audited key actions require MCP |
| LARGE | Large key set, asynchronous bulk upload/drain | [Large-segment workflow](#large-segment-workflow); not STANDARD key batching |
| RULE_BASED | Conditions, matchers and exclusions | [Rule-based workflow](#rule-based-workflow); not a flat key-list replacement |

#### Find / List

- **Without segment name:** fully paginate all three metadata types and merge; report actual coverage, not a fixed call count.
- **With segment name:** resolve type and get metadata, then inspect definitions/membership through that type's workflow. Fully paginate key inventories; distinguish a completed LARGE upload from a pending job and RULE_BASED conditions from observed matching keys. If the current tool cannot inspect a part, report that part unverified. Prefer counts or redacted samples over raw user keys.
- Pagination: see [tool-map.md](../../references/fme/tool-map.md#pagination).

#### Create

1. Explore naming conventions from existing segments. Recommend a pattern if clear.
2. Confirm traffic type exists (**List traffic types**) and explain: "The traffic type must match the flags that will use this segment."
3. Choose STANDARD, LARGE or RULE_BASED from the membership model above; type is immutable. Check the required type-specific operations are available before promising an end-to-end create.
4. Plan: segment name, type, traffic type, description, environments. STOP. Ask: "Create this segment?"
5. On confirmation: create metadata, then follow the selected type's definition/membership workflow for each environment. If tooling cannot complete a step, ask whether the user wants metadata-only creation plus a handoff **before** writing; never silently create an incomplete resource.
6. Re-read metadata and all supported changed definitions; distinguish metadata created from membership provisioned.

#### Add / Remove Keys (STANDARD)

Follow [standard-membership.md](references/standard-membership.md) for parsing, production-aware approval, ≤10,000-key append/removal batches and complete membership readback. A first-page check is not verification; report partial completion and never expose raw keys by default.

#### Usage check

Required before deleting a segment; offer it before removing/replacing keys and disclose any declined coverage. **List flags** (page through every offset), then **List flag definitions** for each. A segment reference can appear in two places per definition — check both, not just one: (1) `rules[].condition.matchers` (segment matchers), and (2) each entry in `treatments[]`, whose `segments`/`largeSegments`/`ruleBasedSegments` membership arrays hold per-treatment segment assignments. Scanning only `rules` misses segments wired as individual-target memberships on a treatment. Cost: one call per flag; above 50 flags, ask the user to narrow by tag, name or rollout status, or to confirm. If any flag or environment couldn't be checked (declined narrowing, call failure), report "Usage: incomplete — checked N of M flags" rather than treating it as clean. Never report a segment as unused unless every flag and every definition page was actually scanned. If skipped entirely, report "Usage: unchecked." See [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

#### Replace All Keys (STANDARD, Destructive)

Follow [Replace all keys](references/standard-membership.md#replace-all-keys): fully inventory the old set, preview removals, obtain destructive-write approval, replace in **one** call and verify exact set equality. Stop above 10,000 keys—never chunk replacements or silently remove-then-add. Empty replacement requires an explicit clear request and confirmation.

#### Update Description / Tags

- **Update segment** (metadata) or **Update definition** (per-env description).
- Draft the before/after change, obtain explicit approval, then update and re-read. MCP metadata uses merge patch; CLI uses declared field handlers, not guessed `--set` arrays. For per-environment changes, use the selected type's definition operation/schema.

#### Delete STANDARD Definition (One Environment)

1. Check if keys remain: **List keys** for one key.
2. If keys exist, the delete will fail with 400 `hasDependents`. Offer: "Remove all keys first? This is a separate confirmed step."
3. If confirmed, follow remove keys flow above, then retry delete.
4. Plan and confirm per [write-safety.md](../../references/fme/write-safety.md), using production wording if the environment is production. Rules that reference this segment in that environment stop matching anyone.
5. **Delete definition**, then confirm exact get returns 404 (not an authorization/error response). CLI-only sessions cannot verify key emptiness; stop or request approved MCP assistance first.

#### Delete Segment

1. Check dependencies using the selected type's workflow and run the [usage check](#usage-check). On 400 `hasDependents`, stop; do not bypass active definitions/references.
2. Double confirmation: "This permanently deletes <segment> in all environments. This cannot be undone. Delete?"
3. STOP and wait for explicit confirmation.
4. **Delete segment** with the selected type; verify exact get returns 404, not an authorization/error response.
5. If flags still reference the segment, change their targeting first with `update-flag-targeting` under separate approval.

#### Large-segment workflow

1. Inspect LARGE metadata and available environment definitions. Establish whether the request is create, export, upload/replace, drain or delete; read the dedicated operation schema and its upload semantics.
2. Preview the affected environment, current/new membership counts when available, usage impact and any removals. Obtain explicit confirmation; destructive replacement/drain needs its own approval.
3. Use the supported large-segment workflow, not STANDARD `add_keys`/`replace=true`. Track asynchronous status to completion and verify the resulting membership through the available export/read operation; acceptance is not completion.
4. The audited native MCP/CLI exposes LARGE metadata but not this bulk workflow. If the installed tools still lack it, guide the matching Harness administration flow and report pending verification. Never silently fall back to deprecated workspace APIs.

#### Rule-based workflow

1. Inspect RULE_BASED metadata, environment definition, ordered rules/matchers, exclusions and referenced segments through available rule-based operations. Do not infer rules from metadata or substitute a STANDARD definition lookup.
2. Draft the exact condition/exclusion changes, preserve unrelated configuration, verify references and run the usage check. Obtain explicit production-aware approval before updating, enabling/disabling or deleting.
3. Apply with the type-specific schema, re-read rules/exclusions and verify enabled state. Rule-based membership is evaluated dynamically; a flat key count is not equivalent verification.
4. The audited native MCP/CLI exposes RULE_BASED metadata but not rule editing; legacy rule-based MCP tools use a different scope contract. If no appropriate native operation is available, guide the Harness rule editor and mark verification pending; never invent commands or switch scope silently.

### Phase 4: Output

After each operation, summarize per [operation-summary.md](../../templates/operation-summary.md): Operation, segment (name, type), environments, what was confirmed, verification (STANDARD membership, LARGE upload completion/membership, RULE_BASED rules/exclusions, or confirmed deletion), usage (checked or unchecked), flags that reference this segment, warnings, recommended next step. Include a Harness UI link when available.

## Examples

- "Create a segment for beta users with traffic type user" — Create flow.
- "Add 500 keys to the beta_users segment in staging" — Add keys flow.
- "Replace all keys in early_access with the ones from this CSV" — Replace flow.
- "Upload this audience to our LARGE segment" — Large-segment workflow; verify bulk completion.
- "Change a RULE_BASED segment to exclude employees" — Rule-based workflow; preserve other rules.
- "Check which flags use the beta_users segment" — Usage check.
- "Delete the old_experiment segment" — Delete segment.

## Performance Notes

- One paginated metadata inventory per type; listing all types may take more than three calls.
- STANDARD add/remove: batches ≤10,000; replacement: one call ≤10,000. LARGE uses its dedicated bulk workflow, not this limit.
- Usage check: cost = one call per flag. Narrow the flag set first (by tag or name) per [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `segment_type is required` (400) | Segment type is required on get/update/delete of a segment | Specify segment type (STANDARD, LARGE, or RULE_BASED) |
| `hasDependents` on delete segment | Definitions or flags still reference it | Run usage check; remove definitions first; prefer leaving segment instead |
| `hasDependents` on delete definition | Keys remain in that environment | **List keys**, confirm removal, then retry delete |
| Keys not matching flags | Traffic type mismatch, or flag rule references a different segment, or no definition in that env | Check traffic types match; verify flag rule; **Create definition** if missing |
| `keys must have at least 1` on remove keys | The key list is empty | Remove operations require at least one key |
| `keys max 10000` | Request too large | Batch additive/removal operations only; stop oversized replacements |
| Required type-specific operation is absent | Tool/version capability gap, not an unsupported segment type | Discover an appropriate supported operation or guide the corresponding administration workflow; report exactly what remains unverified |

Generic errors: see [tool-map.md](../../references/fme/tool-map.md#common-errors).
