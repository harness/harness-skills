# FME Tool Map: MCP ↔ CLI

This is the shared reference for FME resource names, operations, and verified MCP/CLI differences. Skills must copy supported forms from here; `scripts/validate-skills.sh` checks `fme_*` names against this file. Source review: CLI `8768ee9`, MCP `427d5ac1`; deployed versions may differ. This is not a promise of full transport parity.

## Transport preflight and handoffs

- Load this map, [concepts.md](concepts.md), and the skill-local references needed for the selected operation. Load [write-safety.md](write-safety.md) before any mutation. Missing file/tool access is a stop condition, not permission to guess.
- Choose the available CLI or MCP transport before planning. Verify installed command/schema capabilities; generic `--help` can show flags unsupported by a particular endpoint. CLI flags and mutation field IDs are not mechanically derived from JSON names. Unsupported operations must stop; offer another available transport with explicit approval, never switch to bypass authorization or governance.
- CLI discovery: consult `harness <verb> <noun> --help` and the installed command specification for that operation. MCP discovery: use `harness_describe` when available. If neither source establishes a required payload, ask for the schema or stop; do not probe by writing guessed payloads.
- A skill handoff means load the linked workflow, not assume a host-specific slash-command tool exists. Carry confirmed account/org/project, transport, resource/environment IDs, intended change, approved payload/decisions, inventory completeness and unresolved risks. Return exact IDs, readback/test evidence and remaining unverified work. Approval applies only to the original plan, not a new mutation in the next skill.

## Translation Rules

| MCP Tool | CLI Verb | Notes |
|----------|----------|-------|
| `harness_list` | `harness list <noun>` | Use the noun and supported filters below; unsupported filters require complete-inventory client-side filtering |
| `harness_get` | `harness get <noun> <id>` | Primary `params` identifier → CLI positional `<id>`; secondary `params` (e.g. `environment_id`) → CLI flags (`--env`) |
| `harness_create` | `harness create <noun> <id>` | Use `-f <file>` only where the endpoint supports it, or the declared CLI mutation fields |
| `harness_update` | `harness update <noun> <id>` | Use declared `--set` / `--add` / `--del` fields; only some endpoints accept `-f`. No arbitrary JSON-path mutation |
| `harness_delete` | `harness delete <noun> <id>` | Primary `params` identifier → CLI positional `<id>` |
| `harness_execute` | `harness execute <noun>:<action> <id>` | Only registered CLI actions exist; some MCP actions have no CLI equivalent |

**Noun mapping:**
- MCP `fme_feature_flag` ↔ CLI `feature_flag` (alias `ff`)
- MCP `fme_feature_flag_definition` ↔ CLI `feature_flag:definition` (alias `ff:definition`)
- MCP `fme_environment` ↔ CLI `fme_environment` (alias `fme_env`)
- MCP `fme_segment` ↔ CLI `segment` (alias `seg`)
- MCP `fme_segment_definition` ↔ CLI `segment:definition`
- MCP `fme_metric` ↔ CLI `metric`
- MCP `fme_event_type` ↔ CLI `event_type`
- MCP `fme_traffic_type` ↔ CLI `traffic_type`
- MCP `fme_rollout_status` ↔ CLI `rollout_status`
- MCP `fme_experiment` ↔ CLI `experiment` (alias `exp`)
- MCP `fme_experiment_settings` ↔ CLI `experiment:settings`
- MCP `fme_experiment_alerting` ↔ CLI `experiment:alerts`
- MCP `fme_experiment_result` ↔ CLI `experiment:results`

**Execute actions mapping:**
- MCP `harness_execute(resource_type="fme_feature_flag", action="kill", params={feature_flag_name, environment_id})` ↔ CLI `harness execute feature_flag:kill <name> --env <env-id>`
- MCP `harness_execute(resource_type="fme_feature_flag", action="restore", params={feature_flag_name, environment_id})` ↔ CLI `harness execute feature_flag:restore <name> --env <env-id>`
- MCP `harness_execute(resource_type="fme_feature_flag", action="reallocate", params={feature_flag_name, environment_id})` ↔ CLI `harness execute feature_flag:reallocate <name> --env <env-id>`
- MCP `harness_execute(resource_type="fme_feature_flag", action="archive", params={feature_flag_name})` ↔ CLI `harness execute feature_flag:archive <name>`
- MCP `harness_execute(resource_type="fme_feature_flag", action="unarchive", params={feature_flag_name})` ↔ CLI `harness execute feature_flag:unarchive <name>`
- MCP `fme_segment_definition` actions `list_keys`, `add_keys`, `remove_keys`: STANDARD segments only; **not supported by the audited CLI**. Do not invent execute commands.

## Conventions

### Scope

**Harness-native (preferred):** Pass `org_id` + `project_id`. Never use deprecated `workspace_id`.

MCP: `org_id` and `project_id` at top level.
CLI: `--org <org>` and `--project <project>` flags; or set `HARNESS_ORG` / `HARNESS_PROJECT` env vars.

### Identifiers, Filters, and Translation

**Identifiers always go in `params`** by field name: `feature_flag_name`, `environment_id`, `segment_name`, `segment_type`, `metric_id`, `experiment_id`, `event_type_id`. Never `resource_id`, never top-level args (MCP silently drops anything not in `params`/`filters`). List filters and pagination (`name`, `tags`, `rollout_status_id`, `status`, `parent_type`, `offset`, `limit`) go in `filters`.

**CLI translation:** use the documented positional ID and secondary flags (e.g. `--env`), not inferred spellings. Flag/experiment name search uses `--search`; metric/event search uses `--name`. CLI mutation field IDs include `rollout_status`, `traffic_allocation`, `is_positive`, `significance_threshold`, and `is_enabled`; the JSON wire fields differ. Tags/owners use their declared `--add` / `--del` handlers, not `--set` arrays.

CLI: always pass `--json` to get full output.

## Pagination

`harness_list` defaults top-level `size` to **20**, but **only endpoint-mapped arguments reach the API**. Use `filters.offset`, not top-level `page` (ignored by these routes). A list call fetches one page, never an automatic full inventory.

| MCP list resources | Effective limit | Total semantics |
|---|---|---|
| `fme_feature_flag` | `size` → API `limit`; use **`size: 50`** (advertised maximum 50). **`filters.limit` is ignored**; do not assume an oversized size is clamped | No `totalCount` promotion; `total` can be just page length |
| `fme_environment`, `fme_traffic_type`, `fme_rollout_status`, `fme_metric`, `fme_experiment`, `fme_event_type` | Both `size` and `filters.limit` map to API `limit`; **explicit `filters.limit` wins**. Effective MCP default 20, maximum 100; use `filters.limit: 100` | API `totalCount` is promoted to `total`; if absent, the formatter falls back to page length |
| `fme_feature_flag_definition`, `fme_segment`, `fme_segment_definition` | **`size` is ignored**; explicitly send **`filters.limit: 100`**. Omitting it relies on the advertised API default 100 (maximum 100), not the MCP size default | No `totalCount` promotion; treat page-length `total` as non-global |

For every inventory:
1. Start at `filters.offset: 0` with the correct effective limit above. Keep scope and resource filters unchanged, use `compact: false` for configuration/name checks, and count returned rows **before** client-side filtering or deduplication.
2. Advance offset by that raw row count. Where a known API total is available, continue until it is covered—even if an intermediate page is shorter than requested. An empty/non-advancing page before that total is covered is incomplete, not clearance.
3. `total == returned rows` alone never establishes completeness: even promoted-total routes can fall back to page length. Without a trustworthy global total, continue until a page is shorter than the **effective** requested limit; a full page requires another request, including an extra empty page for exact multiples.
4. Failed, repeated/non-advancing, uncertain-limit or deliberately skipped pages mean **incomplete**. Stop safety-gated writes; never infer missing definitions, unused segments, no ACTIVE experiments or archive readiness from partial data. Offset pagination is not a snapshot; re-read relevant state before the approved write.

CLI list pagination uses `--offset` / `--limit`; use `--raw` with `--json` when response-level totals are needed. A conservative page size of 50 works for flag scans on both transports (CLI permits up to 100). CLI ACTIVE and PAUSED experiment queries must each be fully paginated. "List once" means one complete logical inventory, potentially many requests.

## Compact mode

`harness_list` defaults `compact: true`, which keeps only identity/status/type/tags/timestamp/id fields and strips `isKilled`, `impressions`, `treatments`, `rules`, `defaultRule`, `trafficAllocation`, `rolloutStatus`, `baseEventTypes`, etc. It also rewrites `name` into a markdown link `[name](url)` when `openInHarness` is present.

Skills must pass `compact: false` on any list whose config fields you read or whose names you exact-match. `compact` has no effect on `harness_get` (gets are always full)—don't pass it there.

## Common errors

| Status | Cause | Fix |
|--------|-------|-----|
| Fields missing (e.g., `isKilled`, `impressions`) | List called with `compact: true` (default) | Pass `compact: false` |
| Only one page returned | Effective limit differs by resource | Flags: `size: 50` (`filters.limit` ignored). Other lists above: explicit `filters.limit: 100`; definition/segment lists ignore `size`. Advance `filters.offset` per [Pagination](#pagination)—a larger page is not a complete inventory |
| 401 Unauthorized | MCP auth expired or missing | Run `harness auth login` (CLI) or refresh MCP token |
| 403 Forbidden | Insufficient RBAC permissions | Check role grants for the resource type at the scope |
| 400 validation | Invalid field value or shape | Read the error message, fix the named field, retry once (see [schema-validation-loop.md](../schema-validation-loop.md)) |
| 404 Not found | Identifier typo or wrong scope | Re-check identifiers; never create to fill the gap |
| 409 governance/approval | OPA policy or pending approval blocked the write | Report as-is; never retry around it |

## Reverse-lookup scans

No reverse-lookup API exists. To find segment usage, inspect rule matchers **and** each treatment's `segments`, `largeSegments`, and `ruleBasedSegments` memberships; individual `keys` also live inside treatments. There is no generic top-level `targets` array. To find IN_SPLIT dependents, scan rules for `depends.splitName`. To find metric usage, scan experiments for both parent types' `keyMetrics`/`supportingMetrics`.

**Cost guard:** one paginated definition inventory per flag; if >50 flags, ask the user to narrow or approve the cost. Finish all relevant flag/definition/experiment pages for a complete usage verdict. Report "unchecked" or "incomplete" when skipped or interrupted, never "unused".

### Updates (JSON Merge Patch RFC 7396)

Harness-native updates use JSON Merge Patch: omit a field to leave it unchanged, pass a value to update, pass `null` (or `[]` for arrays) to clear clearable fields. Non-clearable fields (e.g., name, trafficType, isProduction) reject explicit `null` with 400.

MCP: `body: { description: "New desc", tags: null }` (clears tags)
CLI: `--set description="New desc"`; remove a particular tag with its declared `--del tags.<name>` handler. For clearing all tags, enumerate and approve the removals or use a supported full-body endpoint. `--set tags=` is not supported by the tag handler.

### Confirm

`harness_create`, `harness_update`, `harness_delete`, and `harness_execute` may require a `confirm: true` arg on clients without elicitation support (e.g., managed MCP that doesn't advertise `elicitation`, or elicitation that fails at runtime). Has no effect on low-risk ops; does not override user decline.

### Audit Fields (Comment / Title)

Many FME write operations accept optional `comment` and/or `title` in the body for audit trails. These are write-only metadata — never stored on or returned by definitions.

Operations supporting audit fields: kill/restore/reallocate, archive/unarchive, definition updates, segment key ops.

MCP: `body: { comment: "Rolling out to beta users", title: "Beta rollout" }`
CLI: use `--comment` / `--title` only when the endpoint declares them. When using `-f`, put audit fields **inside the approved file**: file input takes precedence and separate body flags are not merged. Unsupported audit fields cannot be sent; record the reason in the operation summary instead.

### Output / Links

MCP `harness_get` and `harness_list` responses may include an `openInHarness` URL linking to the Harness UI. This is a convenience field, not stored state.

---

## fme_environment

Harness FME environment. Name max 15 characters. Delete returns 400 `hasDependents` while SDK API keys, flags, or segments remain.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_environment` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list fme_environment` | Apply [pagination completeness checks](#pagination), including the fallback-total guard; effective MCP default 20 without an explicit limit |
| **Get** | `harness_get` · `fme_environment` · `params.environment_id` | `harness get fme_environment <env-id>` | Native only |
| **Create** | `harness_create` · `fme_environment` · `body: { name, isProduction? }` | `harness create fme_environment <name> [--production]` | Native only. `production` accepted as alias for `isProduction` |
| **Update** | `harness_update` · `fme_environment` · `params.environment_id` · `body: { name?, isProduction? }` | `harness update fme_environment <env-id> --set name=foo` | Native only. Merge patch; name/isProduction not clearable |
| **Delete** | `harness_delete` · `fme_environment` · `params.environment_id` | `harness delete fme_environment <env-id>` | No body sent—comment/title silently dropped. Returns 400 `hasDependents` if SDK keys/flags/segments remain |

---

## fme_traffic_type

Read-only lookup. Discover valid traffic type IDs/names for flag and segment create.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_traffic_type` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list traffic_type` | Native; apply [pagination completeness checks](#pagination), including the fallback-total guard; effective MCP default 20 |

---

## fme_rollout_status

Read-only lookup. Discover rollout status UUIDs for filtering flag lists.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_rollout_status` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list rollout_status` | Native; apply [pagination completeness checks](#pagination), including the fallback-total guard; effective MCP default 20 |

---

## fme_feature_flag

Feature flag metadata (cross-environment). Max page size 50.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_feature_flag` · `size: 50` · `filters: { name?, tags?, rollout_status_id?, offset? }` · `compact: false` | `harness list feature_flag [--search <name>] [--status <ACTIVE\|ARCHIVED>] --json` | MCP max size 50. MCP status filtering is client-side. CLI tag/rollout-status filters are unavailable: filter the complete JSON inventory client-side |
| **Get** | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name>` | Returns metadata without requiring environment |
| **Create** | `harness_create` · `fme_feature_flag` · `body: { name, trafficType, description?, tags?, owners? }` | `harness create feature_flag <name> --traffic-type user` | Required: name + trafficType |
| **Update** | `harness_update` · `fme_feature_flag` · `params.feature_flag_name` · `body: { description?, tags?, owners?, rolloutStatus? }` | `harness update feature_flag <name> --set description=foo` | Merge patch. `rolloutStatus` shape: `{id: "<uuid>"}` (CLI: `--set rollout_status=<uuid>`). `owners` shape: `{type: "USER", id or email}` or `{type: "GROUP", identifier}`. Clear description/tags/owners with null/[] |
| **Delete** | `harness_delete` · `fme_feature_flag` · `params.feature_flag_name` | `harness delete feature_flag <name>` | No body sent—comment/title silently dropped |
| **Archive** | `harness_execute` · `fme_feature_flag` · `action="archive"` · `params.feature_flag_name` · `body: { comment?, title? }?` | `harness execute feature_flag:archive <name> [--comment <text>]` | OPA policy checks (409 on failure) |
| **Unarchive** | `harness_execute` · `fme_feature_flag` · `action="unarchive"` · `params.feature_flag_name` · `body: { comment?, title? }?` | `harness execute feature_flag:unarchive <name>` | 409 if flag has dependents |

---

## fme_feature_flag_definition

Per-environment flag config (treatments, rules, defaultRule, trafficAllocation). Native list requires `feature_flag_name`; does not take `environment_id`. Get/create/update/delete/kill/restore/reallocate require `environment_id`. Killed state is `isKilled` (boolean); last impression is `impressions.lastImpressionAt` (ISO-8601 date-time, `null` = never received traffic, absent = unknown).

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_feature_flag_definition` · `params.feature_flag_name` · `filters: { offset: 0, limit: 100 }` · `compact: false` | `harness list feature_flag:definition <flag-name>` | Native only. Paginate definitions across environments for one flag. `size` ignored; explicit `filters.limit` controls the page. API default/max 100 |
| **Get** | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag-name> --env <env-id>` | Returns full definition (treatments, rules, defaultRule, etc.) |
| **Create** | `harness_create` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments, defaultTreatment, defaultRule, rules?, baselineTreatment?, trafficAllocation?, comment?, title? }` | `harness create feature_flag:definition <flag-name> --env <env-id> -f def.json` | Required: treatments, defaultTreatment, defaultRule |
| **Update** | `harness_update` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments?, rules?, defaultRule?, defaultTreatment?, baselineTreatment?, trafficAllocation?, comment?, title? }` | `harness update feature_flag:definition <name> --env <env-id> -f patch.json --json`; scalar alternative: `--set traffic_allocation=80` without `-f` | CLI endpoint supports `file_body: optional`: the file is the merge-patch body using API field names, with no wrapper. `treatments`, `rules`, `defaultRule` replace whole arrays and are not scalar `--set` fields; null is not allowed. File input overrides mutation/body flags: put approved comment/title inside it, never rely on merging separate flags |
| **Delete** | `harness_delete` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness delete feature_flag:definition <flag-name> --env <env-id>` | No body sent—comment/title silently dropped |
| **Kill** | `harness_execute` · `fme_feature_flag` · `action="kill"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:kill <flag-name> --env <env-id>` | All traffic → defaultTreatment. Skills use `fme_feature_flag` to match the CLI noun |
| **Restore** | `harness_execute` · `fme_feature_flag` · `action="restore"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:restore <flag-name> --env <env-id>` | Re-enable after kill |
| **Reallocate** | `harness_execute` · `fme_feature_flag` · `action="reallocate"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:reallocate <flag-name> --env <env-id>` | Re-hash traffic without full update |

---

## fme_segment

Segment metadata (STANDARD, LARGE, or RULE_BASED). Native only. list/get/update/delete require `segment_type` per call. Create requires name + trafficType + segmentType in body.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_segment` · `filters: { segment_type, status?, offset: 0, limit: 100 }` · `compact: false` | `harness list segment --segment-type STANDARD` | Native only. `segment_type` required (one kind per call). Optional `status` (ACTIVE\|ARCHIVED). `size` ignored; use explicit `filters.limit` and paginate. API default/max 100 |
| **Get** | `harness_get` · `fme_segment` · `params: { segment_name, segment_type }` | `harness get segment <name> --segment-type STANDARD` | Native only. `segment_type` required |
| **Create** | `harness_create` · `fme_segment` · `body: { name, trafficType, segmentType, description?, tags?, owners? }` | `harness create segment <name> --traffic-type user --segment-type STANDARD` | Native only. Required: name, trafficType, segmentType |
| **Update** | `harness_update` · `fme_segment` · `params: { segment_name, segment_type }` · `body: { description?, tags?, owners? }` | `harness update segment <name> --segment-type STANDARD --set description=foo` | Native only. Merge patch. Clear with null/[] |
| **Delete** | `harness_delete` · `fme_segment` · `params: { segment_name, segment_type }` | `harness delete segment <name> --segment-type STANDARD` | No body sent—comment/title silently dropped. 400 `hasDependents` if definitions or flags still reference it |

---

### Segment type capabilities

Harness supports **STANDARD, LARGE and RULE_BASED**. These are different membership models, not different levels of product support. The following is a snapshot of the audited native tool contracts; discover installed capabilities before selecting an operation.

| Type | Metadata (MCP and CLI) | Environment/membership workflow |
|------|------------------------|---------------------------------|
| STANDARD | List/get/create/update/delete | `fme_segment_definition` / `segment:definition`; keys via MCP execute actions |
| LARGE | List/get/create/update/delete | Dedicated large-segment definitions and asynchronous bulk upload/drain/export; not exposed by the audited native MCP/CLI |
| RULE_BASED | List/get/create/update/delete | Dedicated rule conditions/matchers/exclusions; audited native tools expose metadata, while legacy rule-based MCP operations use a different workspace contract |

[manage-segments](../../skills/manage-segments/SKILL.md) routes all three types. If an installed tool lacks the required type-specific operation, offer a supported tool or the corresponding Harness administration workflow and report unverified steps. Never treat the type as unsupported or silently substitute a STANDARD route/legacy scope.

## fme_segment_definition

The audited native per-environment definition route handles **STANDARD** segments. LARGE and RULE_BASED use their own [type-specific workflows](#segment-type-capabilities); this route's shape is not evidence of product-wide restrictions. List requires `environment_id`; get/create/update/delete require `segment_name` + `environment_id`. Key operations are MCP execute actions only in the audited versions.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_segment_definition` · `filters: { environment_id, status?, offset: 0, limit: 100 }` · `compact: false` | `harness list segment:definition --env <env-id>` | Native only. `size` ignored; use explicit `filters.limit` and paginate. API default/max 100 |
| **Get** | `harness_get` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness get segment:definition <segment-name> --env <env-id>` | Native only |
| **Create** | `harness_create` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }?` | `harness create segment:definition <segment-name> --env <env-id>` | Native only. Body optional; omit for empty shell |
| **Update** | `harness_update` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }` | `harness update segment:definition <segment-name> --env <env-id> --set description=foo` | Native only. Merge patch; description is the only mutable field |
| **Delete** | `harness_delete` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness delete segment:definition <segment-name> --env <env-id>` | No body sent—comment/title silently dropped. 400 `hasDependents` while keys remain |
| **List Keys** | `harness_execute` · `fme_segment_definition` · `action="list_keys"` · `params: { segment_name, environment_id, offset?, limit? }` | Not supported by the audited CLI | STANDARD only. Exhaust offset/limit pages (max 100) for membership verification |
| **Add Keys** | `harness_execute` · `fme_segment_definition` · `action="add_keys"` · `params: { segment_name, environment_id, replace? }` · `body: { keys, comment?, title? }` | Not supported by the audited CLI | STANDARD only. Max 10000 keys; `replace=true` allows empty replacement. Never split a replacement into multiple replace calls |
| **Remove Keys** | `harness_execute` · `fme_segment_definition` · `action="remove_keys"` · `params: { segment_name, environment_id }` · `body: { keys, comment?, title? }` | Not supported by the audited CLI | STANDARD only. 1–10000 keys per request; verify against complete membership inventory |

---

## fme_metric

Metric definition. Native only. Addressed by `id` (UUID), not name. Create requires name + trafficType + format + aggregation + isPositive + baseEventTypes. Update cannot change name/trafficType. List CLI flags: `--name`, `--traffic-type-id`, `--event-type-id`, `--tag`, `--id`, `--sort-order`, `--limit`. In the audited CLI, repeated ID/tag/event-type filters send only the first value; do not comma-join values. Use one filter value per call or get each metric by ID. `owners` shape: `{type: "USER", id or email}` or `{type: "GROUP", identifier}` (GROUP uses group identifier).

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_metric` · `filters: { name?, traffic_type_id?, event_type_ids?, tags?, ids?, sort_order?, offset?, limit? }` · `compact: false` | `harness list metric [--name <name>] [--traffic-type-id <id>] [--event-type-id <id>] [--tag <tag>] [--id <id>] [--sort-order <order>] [--limit <n>]` | Native only. Maximum 100; effective MCP default 20. Set `filters.limit: 100` and apply [pagination completeness checks](#pagination), including the fallback-total guard |
| **Get** | `harness_get` · `fme_metric` · `params.metric_id` | `harness get metric <metric-id>` | Native only |
| **Create** | `harness_create` · `fme_metric` · `body: { name, trafficType, format, aggregation, isPositive, baseEventTypes, filterEventType?, triggerEventType?, description?, tags?, owners?, cap? }` | `harness create metric <name> -f metric.json --json` | Native only. File contains the complete confirmed body, including at least one owner (backend rejects empty owners until feature flag ships). 409 'Duplicate Definition' on shape collision |
| **Update** | `harness_update` · `fme_metric` · `params.metric_id` · `body: { description?, format?, aggregation?, isPositive?, spread?, baseEventTypes?, filterEventType?, triggerEventType?, tags?, owners?, cap? }` | `harness update metric <metric-id> --set description=foo` | Native only. Merge patch. name/trafficType immutable. format/aggregation/isPositive/spread not clearable |
| **Delete** | `harness_delete` · `fme_metric` · `params.metric_id` | `harness delete metric <metric-id>` | No body sent—comment/title silently dropped. Hard delete, no archive/restore |

**Metric payload parity:** send the same complete approved definition as MCP `body` or CLI `-f metric.json` (JSON/YAML; `-f -` accepts stdin). Use wire-field names such as `isPositive` inside the file. File input takes precedence over `--set` / `--add`; don't combine them expecting a merge. Without a file, the CLI mutation field is `is_positive`, and owners use `--add owners.user:<email-or-id>` or `--add owners.group:<identifier>`; arbitrary nested property filters are not exposed through `--set`. For base events without property settings, include `propertyFilters: []` and `propertyForValue: null` explicitly (MCP otherwise inserts these defaults).

---

## fme_event_type

Read-only lookup. Discover event type IDs for metric baseEventTypes. Visibility covers the project's last 30 days **across environments**; neither transport exposes an environment filter. List `filters.name` is a case-insensitive substring match; `traffic_type` resolves an ID or exact traffic type name. Get uses the exact event name; 404 = absent in this scope/window or idle > 30 days.

Responses contain `id` and `trafficTypes`, not an occurrence timestamp or per-invocation receipt. Check the intended traffic type is present. A 200 does not prove current traffic, delivery from the target environment, or experiment attribution.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_event_type` · `filters: { name?, traffic_type?, offset?, limit? }` · `compact: false` | `harness list event_type [--name <name>] [--traffic-type <name-or-id>] --json` | Native only. Maximum 100; effective MCP default 20. Set `filters.limit: 100` and apply [pagination completeness checks](#pagination), including the fallback-total guard. `name` filter is substring |
| **Get** | `harness_get` · `fme_event_type` · `params.event_type_id` | `harness get event_type <event-type-id> --json` | Native only. 404 = absent or idle > 30 days |

---

## fme_experiment

The API supports feature-flag and AI Config parents, but the current creation/treatment-validation skill implements FEATURE_FLAG only; it must not resolve an AI Config through a feature-flag definition. Read-only experiment/results lookup may use either parent type. Native only. Addressed by `id` (ULID). Create requires parent + name + startAt + endAt + baselineTreatment + comparisonTreatments. CLI full-body creation must include the approved `rule` and still pass `--env` for the query parameter; owners are optional. Status transitions (ACTIVE/PAUSED/COMPLETED/ARCHIVED) are done via update `status` field. List CLI uses `--search <name>` (exception to translation rule). Tags shape: `{name}` objects.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_experiment` · `filters: { parent_type, parent_name?, environment_id?, name?, match_type?, status?: ["ACTIVE","PAUSED"], tags?, offset?, limit? }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG [--parent-name <name>] [--env <env-id>] [--search <name>] [--status ACTIVE]` (repeat with `--status PAUSED`) | Native only. `parent_type` required. Maximum 100; effective MCP default 20. Set `filters.limit: 100` and apply [pagination completeness checks](#pagination), including the fallback-total guard. For name substring matching, set `match_type: "contains"` explicitly. `status` is an array in MCP, single value in CLI; paginate each CLI status separately. Defaults to [ACTIVE] if omitted—never omit for ACTIVE+PAUSED |
| **Get** | `harness_get` · `fme_experiment` · `params.experiment_id` | `harness get experiment <experiment-id>` | Native only |
| **Create** | `harness_create` · `fme_experiment` · `params: { environment_id }` · `body: { parent: { type, id?, name? }, name, startAt, endAt, baselineTreatment, comparisonTreatments, description?, hypothesis?, keyMetrics?, supportingMetrics?, owners?, rule: "default rule", tags? }` | `harness create experiment <name> --env <env-id> -f experiment.json --json` | Native only. Do not send assignmentSource (400). Pass `rule: "default rule"` (the label of the flag's default rule); results only count impressions whose label matches the experiment's `rule` |
| **Update** | `harness_update` · `fme_experiment` · `params.experiment_id` · `body: { name?, description?, hypothesis?, startAt?, endAt?, baselineTreatment?, comparisonTreatments?, keyMetrics?, supportingMetrics?, owners?, rule?, tags?, status? }` | `harness update experiment <experiment-id> --set description=foo --set status=PAUSED` | Native only. Merge patch. Status values via `status` (ACTIVE/PAUSED/COMPLETED/ARCHIVED); backend validates transitions. CLI cannot update `name` or `rule` and does not support file-body updates here: stop those requests or propose MCP with approval. CLI date/treatment/metric fields use snake_case IDs. name/startAt/endAt/baselineTreatment/comparisonTreatments/status not clearable. comparisonTreatments rejects [] |
| **Delete** | `harness_delete` · `fme_experiment` · `params.experiment_id` | `harness delete experiment <experiment-id>` | No body sent—comment/title silently dropped. Hard delete, not archive |

---

## fme_experiment_settings

Experiment statistical settings. Native only. Update creates/updates experiment-level override.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **Get** | `harness_get` · `fme_experiment_settings` · `params: { experiment_id }` | `harness get experiment:settings <experiment-id>` | Native only |
| **Update** | `harness_update` · `fme_experiment_settings` · `params: { experiment_id }` · `body: { statisticalTestType?, significanceThreshold?, multipleComparisonCorrection?, minimumSampleSize?, reviewPeriod?, varianceReduction? }` | `harness update experiment:settings <experiment-id> --set significance_threshold=0.1` | Native only. Merge patch. varianceReduction clearable with null. Others not clearable |
| **Delete** | `harness_delete` · `fme_experiment_settings` · `params: { experiment_id }` | `harness delete experiment:settings <experiment-id>` | Native only. Resets to defaults |

---

## fme_experiment_alerting

Experiment alerting subscription. Native only.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **Get** | `harness_get` · `fme_experiment_alerting` · `params: { experiment_id }` | `harness get experiment:alerts <experiment-id>` | Native only |
| **Update** | `harness_update` · `fme_experiment_alerting` · `params: { experiment_id }` · `body: { isEnabled }` | `harness update experiment:alerts <experiment-id> --set is_enabled=true` | Native only. isEnabled required, not clearable with null |

---

## fme_experiment_result

Read-only metric results for an experiment. Native only. Output: `{items, total, calculatedAt}`; CLI needs `--raw` to keep `calculatedAt`. `comparisons` filter is ignored by backend—filter client-side on each item's `comparison`. Results have no `rule` parameter; they follow the experiment's stored `rule`. Empty results on an experiment whose `rule` isn't `default rule` usually mean the label matches no impressions.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_experiment_result` · `filters: { experiment_id, metric_ids?, comparisons? }` | `harness list experiment:results <experiment-id> [--metric-id <id>] [--raw]` | Native only. `experiment_id` required. `comparisons` ignored by backend—filter client-side. CLI `--raw` keeps `calculatedAt` |

---

## pipeline

Harness CI/CD pipeline (used by FME skills for rollout automation). Addressed by `pipeline_id`.

| Operation | MCP | CLI |
|-----------|-----|-----|
| **Get** | `harness_get` · `pipeline` · `params.pipeline_id` | `harness get pipeline <id> --json` |
| **Create** | `harness_create` · `pipeline` · `body: { yamlPipeline }` | `harness create pipeline -f p.yaml` |
| **Update** | `harness_update` · `pipeline` · `params.pipeline_id` · `body: { yamlPipeline }` | `harness update pipeline <id> -f p.yaml` |

---

## Do Not Use (Legacy)

These resource types are deprecated or legacy-only. New skills must never use them. Use the native equivalents listed.

| Deprecated Resource | Reason | Use Instead |
|---------------------|--------|-------------|
| `fme_workspace` | Legacy Split.io concept. Only for discovering workspace_id for deprecated contract. | Pass `org_id` + `project_id` directly; skip fme_workspace entirely |
| `fme_standard_segment` | Legacy workspace_id contract only. | `fme_segment` with `segment_type: "STANDARD"` |
| `fme_rule_based_segment` | Legacy workspace_id contract only. | `fme_segment` with `segment_type: "RULE_BASED"` |
| `fme_rule_based_segment_definition` | Legacy workspace_id contract only. | Native rule-definition operations are unsupported; do not substitute the STANDARD definition route |
| `fme_segment_keys` | Legacy workspace_id contract only. | `fme_segment_definition` execute actions (list_keys / add_keys / remove_keys) |
| `fme_identity` | Legacy contract; native not implemented yet. | N/A (avoid identity operations until native support ships) |

---

## Copy-Paste: Tools Block for Skills

Every FME skill declares the operations it performs, in both forms, right after its intro. Copy rows from the tables above, keep only what the skill uses, and link back here:

```markdown
## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |
```
