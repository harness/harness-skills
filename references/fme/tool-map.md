# FME Tool Map: MCP ↔ CLI

This is the single source of truth for FME resource names, operations, and MCP-to-CLI translation. Skills must copy names from here exactly as written; `scripts/validate-skills.sh` checks `fme_*` names against this file.

## Translation Rules

| MCP Tool | CLI Verb | Notes |
|----------|----------|-------|
| `harness_list` | `harness list <noun>` | MCP `resource_type` → CLI noun; MCP `filters` → CLI `--<filter-name>` |
| `harness_get` | `harness get <noun> <id>` | Primary `params` identifier → CLI positional `<id>`; secondary `params` (e.g. `environment_id`) → CLI flags (`--env`) |
| `harness_create` | `harness create <noun> <id>` | MCP `body` → CLI `-f <file>` or `--set <field>=<value>` |
| `harness_update` | `harness update <noun> <id>` | MCP `body` → CLI `--set` / `--del` (merge patch) or `-f` (full body) |
| `harness_delete` | `harness delete <noun> <id>` | Primary `params` identifier → CLI positional `<id>` |
| `harness_execute` | `harness execute <noun>:<action> <id>` | MCP `action` → CLI `:<action>` qualifier; MCP `body` → CLI flags or `-f` |

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
- MCP `harness_execute(resource_type="fme_segment_definition", action="list_keys")` ↔ CLI `harness execute segment:list_keys <segment> --env <env-id>`
- MCP `harness_execute(resource_type="fme_segment_definition", action="add_keys")` ↔ CLI `harness execute segment:add_keys <segment> --env <env-id> -f keys.json`
- MCP `harness_execute(resource_type="fme_segment_definition", action="remove_keys")` ↔ CLI `harness execute segment:remove_keys <segment> --env <env-id> -f keys.json`

## Conventions

### Scope

**Harness-native (preferred):** Pass `org_id` + `project_id`. Never use deprecated `workspace_id`.

MCP: `org_id` and `project_id` at top level.
CLI: `--org <org>` and `--project <project>` flags; or set `HARNESS_ORG` / `HARNESS_PROJECT` env vars.

### Identifiers, Filters, and Translation

**Identifiers always go in `params`** by field name: `feature_flag_name`, `environment_id`, `segment_name`, `segment_type`, `metric_id`, `experiment_id`, `event_type_id`. Never `resource_id`, never top-level args (MCP silently drops anything not in `params`/`filters`). List filters and pagination (`name`, `tags`, `rollout_status_id`, `status`, `parent_type`, `offset`, `limit`) go in `filters`.

**CLI translation:** MCP `params` → CLI positional `<id>` for the primary identifier, flags for secondary identifiers (e.g., `environment_id` → `--env <env-id>`). MCP `filters.foo_bar` → CLI `--foo-bar`. Exception: experiment list uses `--search <name>` (not `--name`).

CLI: always pass `--json` to get full output.

## Pagination

`harness_list` defaults `size: 20`; MCP maps `size` → API `limit`. Passing both `size` and `filters.limit` is safe (limit wins). Max page for `fme_feature_flag` is 50; others 100.

For `fme_feature_flag`, `fme_feature_flag_definition`, `fme_segment`, `fme_segment_definition` lists, MCP reports `total` = page length (v4 doesn't report `totalCount`), so never use `total` to decide completeness—stop only when a page returns fewer rows than requested.

V4 lists (`fme_environment`, `fme_traffic_type`, `fme_rollout_status`, `fme_metric`, `fme_experiment`) do map `totalCount` → `total`.

## Compact mode

`harness_list` defaults `compact: true`, which keeps only identity/status/type/tags/timestamp/id fields and strips `isKilled`, `impressions`, `treatments`, `rules`, `defaultRule`, `trafficAllocation`, `rolloutStatus`, `baseEventTypes`, etc. It also rewrites `name` into a markdown link `[name](url)` when `openInHarness` is present.

Skills must pass `compact: false` on any list whose config fields you read or whose names you exact-match. `compact` has no effect on `harness_get` (gets are always full)—don't pass it there.

## Common errors

| Status | Cause | Fix |
|--------|-------|-----|
| Fields missing (e.g., `isKilled`, `impressions`) | List called with `compact: true` (default) | Pass `compact: false` |
| Only 20 rows returned | Default page size | Pass `size: 50` (flags) or `size: 100` + `filters.limit: 100` |
| 401 Unauthorized | MCP auth expired or missing | Run `harness auth login` (CLI) or refresh MCP token |
| 403 Forbidden | Insufficient RBAC permissions | Check role grants for the resource type at the scope |
| 400 validation | Invalid field value or shape | Read the error message, fix the named field, retry once (see [schema-validation-loop.md](../schema-validation-loop.md)) |
| 404 Not found | Identifier typo or wrong scope | Re-check identifiers; never create to fill the gap |
| 409 governance/approval | OPA policy or pending approval blocked the write | Report as-is; never retry around it |

## Reverse-lookup scans

No reverse-lookup API exists. To find segment usage, scan flag definitions' `rules`/`targets` for the segment name. To find IN_SPLIT dependents, scan rules for `depends.splitName`. To find metric usage, scan experiments for both parent types' `keyMetrics`/`supportingMetrics`.

**Cost guard:** one list call per flag; if >50 flags, stop and ask the user to narrow (tag/name/rollout status) or confirm. Report "unchecked" when skipped.

### Updates (JSON Merge Patch RFC 7396)

Harness-native updates use JSON Merge Patch: omit a field to leave it unchanged, pass a value to update, pass `null` (or `[]` for arrays) to clear clearable fields. Non-clearable fields (e.g., name, trafficType, isProduction) reject explicit `null` with 400.

MCP: `body: { description: "New desc", tags: null }` (clears tags)
CLI: `--set description="New desc" --del tags` (or `--set tags=`)

### Confirm

`harness_create`, `harness_update`, `harness_delete`, and `harness_execute` may require a `confirm: true` arg on clients without elicitation support (e.g., managed MCP that doesn't advertise `elicitation`, or elicitation that fails at runtime). Has no effect on low-risk ops; does not override user decline.

### Audit Fields (Comment / Title)

Many FME write operations accept optional `comment` and/or `title` in the body for audit trails. These are write-only metadata — never stored on or returned by definitions.

Operations supporting audit fields: kill/restore/reallocate, archive/unarchive, definition updates, segment key ops.

MCP: `body: { comment: "Rolling out to beta users", title: "Beta rollout" }`
CLI: `--comment "Rolling out to beta users" --title "Beta rollout"`

### Output / Links

MCP `harness_get` and `harness_list` responses may include an `openInHarness` URL linking to the Harness UI. This is a convenience field, not stored state.

---

## fme_environment

Harness FME environment. Name max 15 characters. Delete returns 400 `hasDependents` while SDK API keys, flags, or segments remain.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment` | Offset/limit pagination |
| **Get** | `harness_get` · `fme_environment` · `params.environment_id` | `harness get fme_environment <env-id>` | Native only |
| **Create** | `harness_create` · `fme_environment` · `body: { name, isProduction? }` | `harness create fme_environment <name> [--production]` | Native only. `production` accepted as alias for `isProduction` |
| **Update** | `harness_update` · `fme_environment` · `params.environment_id` · `body: { name?, isProduction? }` | `harness update fme_environment <env-id> --set name=foo` | Native only. Merge patch; name/isProduction not clearable |
| **Delete** | `harness_delete` · `fme_environment` · `params.environment_id` | `harness delete fme_environment <env-id>` | No body sent—comment/title silently dropped. Returns 400 `hasDependents` if SDK keys/flags/segments remain |

---

## fme_traffic_type

Read-only lookup. Discover valid traffic type IDs/names for flag and segment create.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type` | Native: offset/limit pagination |

---

## fme_rollout_status

Read-only lookup. Discover rollout status UUIDs for filtering flag lists.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_rollout_status` · `compact: false` | `harness list rollout_status` | Native: offset/limit pagination |

---

## fme_feature_flag

Feature flag metadata (cross-environment). Max page size 50.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_feature_flag` · `size: 50` · `filters: { name?, tags?, rollout_status_id?, offset? }` · `compact: false` | `harness list feature_flag [--search <name>] [--tags <tag>] [--rollout-status-id <id>] [--status <ACTIVE\|ARCHIVED>]` | Max size 50, default 20. MCP has **no status filter** — filter `status` client-side; CLI has `--status` |
| **Get** | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name>` | Returns metadata without requiring environment |
| **Create** | `harness_create` · `fme_feature_flag` · `body: { name, trafficType, description?, tags?, owners? }` | `harness create feature_flag <name> --traffic-type user` | Required: name + trafficType |
| **Update** | `harness_update` · `fme_feature_flag` · `params.feature_flag_name` · `body: { description?, tags?, owners?, rolloutStatus? }` | `harness update feature_flag <name> --set description=foo` | Merge patch. `rolloutStatus` shape: `{id: "<uuid>"}` (CLI: `--set rolloutStatus.id=<uuid>`). `owners` shape: `{type: "USER", id or email}` or `{type: "GROUP", identifier}`. Clear description/tags/owners with null/[] |
| **Delete** | `harness_delete` · `fme_feature_flag` · `params.feature_flag_name` | `harness delete feature_flag <name>` | No body sent—comment/title silently dropped |
| **Archive** | `harness_execute` · `fme_feature_flag` · `action="archive"` · `params.feature_flag_name` · `body: { comment?, title? }?` | `harness execute feature_flag:archive <name> [--comment <text>]` | OPA policy checks (409 on failure) |
| **Unarchive** | `harness_execute` · `fme_feature_flag` · `action="unarchive"` · `params.feature_flag_name` · `body: { comment?, title? }?` | `harness execute feature_flag:unarchive <name>` | 409 if flag has dependents |

---

## fme_feature_flag_definition

Per-environment flag config (treatments, rules, defaultRule, trafficAllocation). Native list requires `feature_flag_name`; does not take `environment_id`. Get/create/update/delete/kill/restore/reallocate require `environment_id`. Killed state is `isKilled` (boolean); last impression is `impressions.lastImpressionAt` (ISO-8601 date-time, `null` = never received traffic, absent = unknown).

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_feature_flag_definition` · `params.feature_flag_name` · `filters: { offset?, limit? }` · `compact: false` | `harness list feature_flag:definition <flag-name>` | Native only. Lists definitions across environments for one flag. Max 100, default 100 |
| **Get** | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag-name> --env <env-id>` | Returns full definition (treatments, rules, defaultRule, etc.) |
| **Create** | `harness_create` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments, defaultTreatment, defaultRule, rules?, baselineTreatment?, trafficAllocation?, comment?, title? }` | `harness create feature_flag:definition <flag-name> --env <env-id> -f def.json` | Required: treatments, defaultTreatment, defaultRule |
| **Update** | `harness_update` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments?, rules?, defaultRule?, defaultTreatment?, baselineTreatment?, trafficAllocation?, comment?, title? }` | `harness update feature_flag:definition <name> --env <env-id> --set trafficAllocation=80` | Merge patch (null not allowed for treatments/rules/defaultRule). Arrays (`treatments`, `rules`) are replaced whole — send the full array. comment/title write-only |
| **Delete** | `harness_delete` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness delete feature_flag:definition <flag-name> --env <env-id>` | No body sent—comment/title silently dropped |
| **Kill** | `harness_execute` · `fme_feature_flag` · `action="kill"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:kill <flag-name> --env <env-id>` | All traffic → defaultTreatment. Skills use `fme_feature_flag` to match the CLI noun |
| **Restore** | `harness_execute` · `fme_feature_flag` · `action="restore"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:restore <flag-name> --env <env-id>` | Re-enable after kill |
| **Reallocate** | `harness_execute` · `fme_feature_flag` · `action="reallocate"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:reallocate <flag-name> --env <env-id>` | Re-hash traffic without full update |

---

## fme_segment

Segment metadata (STANDARD, LARGE, or RULE_BASED). Native only. list/get/update/delete require `segment_type` per call. Create requires name + trafficType + segmentType in body.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_segment` · `filters: { segment_type, status?, offset?, limit? }` · `compact: false` | `harness list segment --segment-type STANDARD` | Native only. `segment_type` required (one kind per call). Optional `status` (ACTIVE\|ARCHIVED). Max 100, default 100 |
| **Get** | `harness_get` · `fme_segment` · `params: { segment_name, segment_type }` | `harness get segment <name> --segment-type STANDARD` | Native only. `segment_type` required |
| **Create** | `harness_create` · `fme_segment` · `body: { name, trafficType, segmentType, description?, tags?, owners? }` | `harness create segment <name> --traffic-type user --segment-type STANDARD` | Native only. Required: name, trafficType, segmentType |
| **Update** | `harness_update` · `fme_segment` · `params: { segment_name, segment_type }` · `body: { description?, tags?, owners? }` | `harness update segment <name> --segment-type STANDARD --set description=foo` | Native only. Merge patch. Clear with null/[] |
| **Delete** | `harness_delete` · `fme_segment` · `params: { segment_name, segment_type }` | `harness delete segment <name> --segment-type STANDARD` | No body sent—comment/title silently dropped. 400 `hasDependents` if definitions or flags still reference it |

---

## fme_segment_definition

Per-environment segment definition. Native only. list requires `environment_id`; get/create/update/delete require `segment_name` + `environment_id`. Segment key ops are execute actions.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_segment_definition` · `filters: { environment_id, status?, offset?, limit? }` · `compact: false` | `harness list segment:definition --env <env-id>` | Native only. Max 100, default 100 |
| **Get** | `harness_get` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness get segment:definition <segment-name> --env <env-id>` | Native only |
| **Create** | `harness_create` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }?` | `harness create segment:definition <segment-name> --env <env-id>` | Native only. Body optional; omit for empty shell |
| **Update** | `harness_update` · `fme_segment_definition` · `params: { segment_name, environment_id }` · `body: { description? }` | `harness update segment:definition <segment-name> --env <env-id> --set description=foo` | Native only. Merge patch; description is the only mutable field |
| **Delete** | `harness_delete` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness delete segment:definition <segment-name> --env <env-id>` | No body sent—comment/title silently dropped. 400 `hasDependents` while keys remain |
| **List Keys** | `harness_execute` · `fme_segment_definition` · `action="list_keys"` · `params: { segment_name, environment_id, offset?, limit? }` | `harness execute segment:list_keys <segment> --env <env-id>` | Native only. Pagination: offset/limit (max 100, default 100) |
| **Add Keys** | `harness_execute` · `fme_segment_definition` · `action="add_keys"` · `params: { segment_name, environment_id, replace? }` · `body: { keys, comment?, title? }` | `harness execute segment:add_keys <segment> --env <env-id> [--replace] -f keys.json` | Native only. `keys` max 10000. `replace=true` allows empty keys (full replace) |
| **Remove Keys** | `harness_execute` · `fme_segment_definition` · `action="remove_keys"` · `params: { segment_name, environment_id }` · `body: { keys, comment?, title? }` | `harness execute segment:remove_keys <segment> --env <env-id> -f keys.json` | Native only. `keys` must have at least 1, max 10000 |

---

## fme_metric

Metric definition. Native only. Addressed by `id` (UUID), not name. Create requires name + trafficType + format + aggregation + isPositive + baseEventTypes. Update cannot change name/trafficType. List CLI flags: `--name`, `--traffic-type-id`, `--event-type-id`, `--tag`, `--id`, `--sort-order`, `--limit`. `owners` shape: `{type: "USER", id or email}` or `{type: "GROUP", identifier}` (GROUP uses group identifier).

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_metric` · `filters: { name?, traffic_type_id?, event_type_ids?, tags?, ids?, sort_order?, offset?, limit? }` · `compact: false` | `harness list metric [--name <name>] [--traffic-type-id <id>] [--event-type-id <id>] [--tag <tag>] [--id <id>] [--sort-order <order>] [--limit <n>]` | Native only. Max 100, default 100 |
| **Get** | `harness_get` · `fme_metric` · `params.metric_id` | `harness get metric <metric-id>` | Native only |
| **Create** | `harness_create` · `fme_metric` · `body: { name, trafficType, format, aggregation, isPositive, baseEventTypes, filterEventType?, triggerEventType?, description?, tags?, owners?, cap? }` | `harness create metric <name> --traffic-type user --event-type signup --set format=NUMBER --set aggregation=COUNT --set isPositive=true` | Native only. Backend rejects empty owners (until feature flag ships); pass at least one. 409 'Duplicate Definition' on shape collision |
| **Update** | `harness_update` · `fme_metric` · `params.metric_id` · `body: { description?, format?, aggregation?, isPositive?, spread?, baseEventTypes?, filterEventType?, triggerEventType?, tags?, owners?, cap? }` | `harness update metric <metric-id> --set description=foo` | Native only. Merge patch. name/trafficType immutable. format/aggregation/isPositive/spread not clearable |
| **Delete** | `harness_delete` · `fme_metric` · `params.metric_id` | `harness delete metric <metric-id>` | No body sent—comment/title silently dropped. Hard delete, no archive/restore |

---

## fme_event_type

Read-only lookup. Discover valid event type IDs for metric baseEventTypes. Only event types with events in last 30 days are visible. List `filters.name` is case-insensitive substring match, not exact. Get is exact; 404 = absent or idle > 30 days.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_event_type` · `filters: { name?, traffic_type?, offset?, limit? }` · `compact: false` | `harness list event_type [--name <name>]` | Native only. Max 100, default 100. `name` filter is substring |
| **Get** | `harness_get` · `fme_event_type` · `params.event_type_id` | `harness get event_type <event-type-id>` | Native only. 404 = absent or idle > 30 days |

---

## fme_experiment

Experiment against a feature flag or AI Config. Native only. Addressed by `id` (ULID). Create requires parent + name + startAt + endAt + baselineTreatment + comparisonTreatments. Status transitions (ACTIVE/PAUSED/COMPLETED/ARCHIVED) are done via update `status` field. List CLI uses `--search <name>` (exception to translation rule). Tags shape: `{name}` objects.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **List** | `harness_list` · `fme_experiment` · `filters: { parent_type, parent_name?, environment_id?, name?, status?: ["ACTIVE","PAUSED"], tags?, offset?, limit? }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG [--parent-name <name>] [--env <env-id>] [--search <name>] [--status ACTIVE]` (repeat with `--status PAUSED`) | Native only. `parent_type` required. Max 100, default 20. `status` is an array in MCP, single value in CLI. Defaults to [ACTIVE] if omitted—never omit for ACTIVE+PAUSED |
| **Get** | `harness_get` · `fme_experiment` · `params.experiment_id` | `harness get experiment <experiment-id>` | Native only |
| **Create** | `harness_create` · `fme_experiment` · `params: { environment_id }` · `body: { parent: { type, id?, name? }, name, startAt, endAt, baselineTreatment, comparisonTreatments, description?, hypothesis?, keyMetrics?, supportingMetrics?, owners?, rule: "default rule", tags? }` | `harness create experiment <name> --parent-type FEATURE_FLAG --parent-name my-flag --env <env-id> --start-at <iso8601> --end-at <iso8601> --baseline-treatment off --comparison-treatment on [--key-metric <id>] [--supporting-metric <id>]` | Native only. Do not send assignmentSource (400). Pass `rule: "default rule"` (the label of the flag's default rule); results only count impressions whose label matches the experiment's `rule` |
| **Update** | `harness_update` · `fme_experiment` · `params.experiment_id` · `body: { name?, description?, hypothesis?, startAt?, endAt?, baselineTreatment?, comparisonTreatments?, keyMetrics?, supportingMetrics?, owners?, rule?, tags?, status? }` | `harness update experiment <experiment-id> --set description=foo --set status=PAUSED` | Native only. Merge patch. Status transitions via `status` field (ACTIVE/PAUSED/COMPLETED/ARCHIVED). name/startAt/endAt/baselineTreatment/comparisonTreatments/status not clearable. comparisonTreatments rejects [] |
| **Delete** | `harness_delete` · `fme_experiment` · `params.experiment_id` | `harness delete experiment <experiment-id>` | No body sent—comment/title silently dropped. Hard delete, not archive |

---

## fme_experiment_settings

Experiment statistical settings. Native only. Update creates/updates experiment-level override.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **Get** | `harness_get` · `fme_experiment_settings` · `params: { experiment_id }` | `harness get experiment:settings <experiment-id>` | Native only |
| **Update** | `harness_update` · `fme_experiment_settings` · `params: { experiment_id }` · `body: { statisticalTestType?, significanceThreshold?, multipleComparisonCorrection?, minimumSampleSize?, reviewPeriod?, varianceReduction? }` | `harness update experiment:settings <experiment-id> --set significanceThreshold=0.1` | Native only. Merge patch. varianceReduction clearable with null. Others not clearable |
| **Delete** | `harness_delete` · `fme_experiment_settings` · `params: { experiment_id }` | `harness delete experiment:settings <experiment-id>` | Native only. Resets to defaults |

---

## fme_experiment_alerting

Experiment alerting subscription. Native only.

| Operation | MCP Call | CLI Command | Notes |
|-----------|----------|-------------|-------|
| **Get** | `harness_get` · `fme_experiment_alerting` · `params: { experiment_id }` | `harness get experiment:alerts <experiment-id>` | Native only |
| **Update** | `harness_update` · `fme_experiment_alerting` · `params: { experiment_id }` · `body: { isEnabled }` | `harness update experiment:alerts <experiment-id> --set isEnabled=true` | Native only. isEnabled required, not clearable with null |

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
| `fme_rule_based_segment_definition` | Legacy workspace_id contract only. | `fme_segment_definition` |
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
