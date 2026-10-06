---
name: manage-segments
description: >-
  Create, inspect, and maintain Harness FME segments (STANDARD, LARGE,
  RULE_BASED). Manage metadata, select type-specific definition and membership
  workflows, and check referencing flags before every mutation. Use
  when asked to create a segment, add keys to a segment, list segments, update
  segment metadata, remove keys, replace keys, check segment usage, or delete
  segments. Do not use for making a flag USE a segment (update-flag-targeting),
  flag CRUD (create-feature-flag, manage-flag-lifecycle), or flag discovery
  (discover-feature-flags). Trigger phrases: create segment, add keys, list
  segments, segment membership, segment targeting, update segment, remove keys,
  replace segment keys, segment definition, check segment usage, delete segment.
metadata:
  author: Harness
  version: 1.3.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires Harness MCP or CLI; RULE_BASED rule changes use the Harness rule editor
---

# Manage Segments

Manage metadata for **STANDARD**, **LARGE**, and **RULE_BASED** segments, STANDARD membership, and approved RULE_BASED editor changes. Every mutation requires a complete reference-impact check and explicit approval. LARGE bulk membership operations are outside this skill's scope.

## Tools

Works through Harness MCP or CLI with equivalent scope, confirmation and verification requirements. Discover exact CLI action syntax through command help; use [tool-map.md](../../references/fme/tool-map.md#segment-type-capabilities) for mappings. `STANDARD` in metadata examples stands for the selected type; definition/key rows apply only to STANDARD.

| Operation | MCP | CLI |
|-----------|-----|-----|
| List traffic types | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type --json` |
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `compact: false` | `harness list feature_flag --json --limit 50` |
| List experiments | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, environment_id, status: ["ACTIVE", "PAUSED"], offset: 0, limit: 100 }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <flag> --env <env-id> --status ACTIVE --json`, then PAUSED; fully paginate both |
| List flag definitions | `harness_list` · `fme_feature_flag_definition` · `params: { feature_flag_name }` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list feature_flag:definition <flag> --json` |
| List segments | `harness_list` · `fme_segment` · `filters: { segment_type, status?, offset: 0, limit: 100 }` · `compact: false` | `harness list segment --segment-type STANDARD --json`; safety gates list ACTIVE and ARCHIVED using declared status filters |
| Get segment | `harness_get` · `fme_segment` · `params: { segment_name, segment_type }` | `harness get segment <name> --segment-type STANDARD --json` |
| Create segment | `harness_create` · `fme_segment` · `body: { name, trafficType, segmentType, description?, tags?, owners? }` | `harness create segment <name> --traffic-type user --segment-type STANDARD` |
| Update segment | `harness_update` · `fme_segment` · `params: { segment_name, segment_type }` · `body: { description?, tags?, owners? }` | `harness update segment <name> --segment-type STANDARD --set description=foo` |
| Delete segment | `harness_delete` · `fme_segment` · `params: { segment_name, segment_type }` | `harness delete segment <name> --segment-type STANDARD` |
| List definitions | `harness_list` · `fme_segment_definition` · `filters: { environment_id, status?, offset: 0, limit: 100 }` · `compact: false` | `harness list segment:definition --env <env-id> --json` |
| Get definition | `harness_get` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness get segment:definition <name> --env <env-id> --json` |
| Create definition | `harness_create` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }?` | `harness create segment:definition <name> --env <env-id>` |
| Update definition | `harness_update` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }` | `harness update segment:definition <name> --env <env-id> --set description=foo` |
| Delete definition | `harness_delete` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness delete segment:definition <name> --env <env-id>` |
| List keys | `harness_execute` · `fme_segment_definition` · `action="list_keys"` · `params: { segment_name, environment_id, offset?, limit? }` | Discover the key-list action and pagination arguments through CLI help |
| Add keys | `harness_execute` · `fme_segment_definition` · `action="add_keys"` · `params: { segment_name, environment_id, replace? }` · `body: { keys, comment?, title? }` | Discover the key-add action and replacement argument through CLI help |
| Remove keys | `harness_execute` · `fme_segment_definition` · `action="remove_keys"` · `params: { segment_name, environment_id }` · `body: { keys, comment?, title? }` | Discover the key-remove action through CLI help |

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

Resolve exact name **and type**, then choose the workflow below. Before **every mutation**, including metadata creation, definition provisioning and key additions, complete the [usage check](#usage-check), present its impact with the plan, and obtain [production-aware approval](../../references/fme/write-safety.md). Incomplete checks block writes; approval never waives coverage. Discover the selected operation's exact schema before execution and preserve native org/project scope.

| Type | Membership model | Workflow |
|------|------------------|----------|
| STANDARD | Explicit key set | Metadata, environment definitions and key flows below |
| LARGE | Large key set | Metadata and reference-impact checks only |
| RULE_BASED | Conditions, matchers and exclusions | Metadata and [rule-editor workflow](#rule-based-workflow) |

#### Find / List

- **Without segment name:** fully paginate all three metadata types and merge; report actual coverage, not a fixed call count.
- **With segment name:** resolve type and get metadata. For STANDARD, inspect environment definitions and fully paginate keys. For RULE_BASED, inspect authoritative rule-editor configuration, not an observed sample of matching keys. For LARGE, report metadata and references only. Prefer counts or redacted samples over raw user keys.
- For MCP segment metadata, STANDARD segment definitions and flag definitions, `size` is ignored: explicitly set `filters.limit: 100`, advance `filters.offset`, and continue until a short page. Their `total` is page length, not inventory size. Follow [pagination](../../references/fme/tool-map.md#pagination) for the other resources; failed/skipped pages cannot establish absence or no usage.

#### Create

1. Explore naming conventions from existing segments. Recommend a pattern if clear.
2. Confirm traffic type exists (**List traffic types**) and explain: "The traffic type must match the flags that will use this segment."
3. Choose type (immutable), check exact-name/type uniqueness, and complete the usage gate even for a new name; existing rules can contain references to it.
4. Plan metadata and environment steps separately. LARGE creation is metadata-only; RULE_BASED includes an explicitly agreed editor step. List each environment and apply the production-aware confirmation gate before writing.
5. Create approved metadata, then provision each approved STANDARD definition or guide the RULE_BASED editor step. Revalidate the gate before dependent writes; stop on a conflict or changed state.
6. Re-read changed metadata/definitions. Report metadata creation separately from membership or rules saved; never imply an unfinished step succeeded.

#### Add / Remove Keys (STANDARD)

Follow [standard-membership.md](references/standard-membership.md) for parsing, production-aware approval, ≤10,000-key append/removal batches and complete membership readback. A first-page check is not verification; report partial completion and never expose raw keys by default.

#### Usage check

Follow [usage-check.md](references/usage-check.md) before every mutation. Scan **all ACTIVE and ARCHIVED project flags and all environments**, including rule matchers, treatment memberships and indirect RULE_BASED dependencies. Above 50 flags, obtain cost approval **before** definition reads; do not narrow a write's safety scan. Failed, skipped or unparsed coverage blocks the write. References require an explicit impact review; deletion is blocked until dependencies are separately resolved and the gate rerun.

#### Replace All Keys (STANDARD, Destructive)

Follow [Replace all keys](references/standard-membership.md#replace-all-keys): fully inventory the old set, preview removals, obtain destructive-write approval, replace in **one** call and verify exact set equality. Stop above 10,000 keys—never chunk replacements or silently remove-then-add. Empty replacement requires an explicit clear request and confirmation.

#### Update Description / Tags

- **Update segment** (metadata) or **Update definition** (per-env description).
- Complete the usage gate, draft the before/after change, obtain explicit approval, then update and re-read. Distinguish metadata-only edits from changes affecting evaluation. MCP metadata uses merge patch; CLI uses declared field handlers, not guessed `--set` arrays. STANDARD per-environment descriptions use **Update definition**.

#### Delete STANDARD Definition (One Environment)

1. Complete the usage gate. If any direct or indirect reference affects this environment, STOP; resolve it under separate approval with `update-flag-targeting` or the rule-editor workflow, then rerun the gate.
2. Check if keys remain: **List keys** for one key. If keys exist, offer removal as a separate confirmed operation; fully inventory keys before constructing that removal.
3. After any removal, rerun/revalidate the gate and verify the segment is empty. Do not bypass `hasDependents`.
4. Present the deletion plan and obtain explicit production-aware approval.
5. **Delete definition**, then verify exact get returns 404 (not an authorization/error response).

#### Delete Segment

1. Run the usage gate. For STANDARD, inspect all environment definitions with STANDARD calls. For other types, use authoritative configuration evidence and the delete operation's dependency validation, never STANDARD definition calls. **Before deletion**, STOP for any known remaining direct/indirect references or active definitions; resolve them separately, then rerun the gate. On `hasDependents`, stop and report the dependency; never bypass it.
2. Double confirmation: "This permanently deletes <segment> in all environments. This cannot be undone. Delete?"
3. STOP and wait for explicit confirmation; revalidate state immediately before writing.
4. **Delete segment** with the selected type; verify exact get returns 404, not an authorization/error response.

#### Rule-based workflow

1. Confirm exact RULE_BASED metadata and environment. Ask the user to open the Harness rule editor and provide current ordered rules, matchers, exclusions and enabled state, with personal keys redacted. Preserve structural identifiers needed for dependency checks; do not infer rules from metadata or use STANDARD definition/key calls.
2. Draft the exact before/after condition or exclusion change. Preserve rule order, combiners, negation and unrelated fields; verify referenced segment names/types and traffic types. For example, excluding STANDARD `employees` changes membership, not the flag's targeting rules.
3. Complete the usage gate and present impacted flags/environments. Obtain explicit production-aware approval for the precise rule edit or enable/disable action.
4. Have the user apply only the approved change in that environment's rule editor. Revalidate the gate and current configuration before saving; changed state requires a revised plan and approval. Respect any governance/approval requirement.
5. Obtain fresh saved configuration and compare rules, exclusions and enabled state with the approved plan. Record user-confirmed evidence separately from direct readback. A draft or unsaved editor view is **not** completion; report verification pending until saved state is confirmed.

### Phase 4: Output

Summarize per [operation-summary.md](../../templates/operation-summary.md): operation, exact name/type, environments, approved change, usage coverage and direct/indirect references, verification evidence (metadata, STANDARD membership, saved RULE_BASED configuration or confirmed deletion), and remaining work. Label incomplete checks as blocking and distinguish user-confirmed editor evidence from direct readback. Include a returned Harness UI link when available.

## Examples

- "Create a segment for beta users with traffic type user" — Create flow.
- "Add 500 keys to the beta_users segment in staging" — Complete the usage gate, then approve and add keys.
- "Replace all keys in early_access with the ones from this CSV" — Replace flow.
- "Update the description of our LARGE segment" — Metadata change with a usage check.
- "Change a RULE_BASED segment to exclude employees" — Draft, approve and verify a rule-editor change; preserve other rules.
- "Check which flags use the beta_users segment" — Usage check.
- "Delete the old_experiment segment" — Delete segment.

## Performance Notes

- One paginated metadata inventory per type; listing all types may take more than three calls.
- STANDARD add/remove: batches ≤10,000; replacement: one call ≤10,000.
- Usage check: one paginated definition inventory per project flag plus indirect-dependency evidence. Above 50 flags, obtain cost approval before definition reads. Never narrow a pre-write safety scan.

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `segment_type is required` (400) | Segment type is required on get/update/delete of a segment | Specify segment type (STANDARD, LARGE, or RULE_BASED) |
| `hasDependents` on delete segment | Definitions or references remain | Stop; resolve dependencies separately for the selected type, then rerun the usage gate; prefer leaving the segment intact |
| `hasDependents` on delete definition | Keys or dependencies remain in that environment | Complete the usage gate; resolve references separately, inventory and approve any key removal, then rerun the gate before retrying deletion |
| STANDARD keys not matching flags | Traffic type mismatch, wrong segment reference, or no STANDARD definition in that env | Verify traffic types and flag rule; if needed, create the STANDARD definition through the confirmed usage-gated flow |
| `keys must have at least 1` on remove keys | The key list is empty | Remove operations require at least one key |
| `keys max 10000` | Request too large | Batch additive/removal operations only; stop oversized replacements |
| Usage coverage is incomplete or unparsed | A page, rule shape or dependency chain is unresolved | Stop the write; obtain the missing configuration/coverage and rerun the gate |

Generic errors: see [tool-map.md](../../references/fme/tool-map.md#common-errors).
