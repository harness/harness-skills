---
name: manage-flag-lifecycle
description: >-
  Manage metadata and lifecycle for a Harness FME feature flag: update description,
  tags, owners, rollout status; assess archive readiness (usage, experiments, dependents);
  archive/unarchive; delete definitions in one environment; delete the flag. Supports
  single flags or explicit small lists (≤ 20). Use when asked to change flag metadata,
  archive a flag, check if a flag is safe to archive, unarchive a flag, or delete a
  flag/definition. Do not use for targeting changes (update-flag-targeting), creating
  flags (create-feature-flag), discovering stale flags across a project (discover-feature-flags),
  removing flag code (cleanup-feature-flags), or rollout pipelines (fme-pipeline).
  Trigger phrases: update flag description, flag metadata, archive flag, unarchive flag,
  delete flag, archive readiness, is flag safe to archive, flag lifecycle.
metadata:
  author: Harness
  version: 1.2.1
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Manage Flag Lifecycle

Manage metadata, archive readiness, archive/unarchive, and deletion for Harness FME feature flags. Related: `update-flag-targeting` (targeting), `discover-feature-flags` (stale flags), `cleanup-feature-flags` (code removal).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `filters: { name?, tags?, rollout_status_id?, offset? }` · `compact: false` | `harness list feature_flag --search <name> --status <ACTIVE\|ARCHIVED> --json` (CLI has no `--tags`/`--rollout-status-id`; filter client-side on the full JSON, which MCP's `tags`/`rollout_status_id` filters do server-side) |
| Get flag | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name> --json` |
| Update flag | `harness_update` · `fme_feature_flag` · `params.feature_flag_name` · `body: { description?, tags?, owners?, rolloutStatus? }` | `harness update feature_flag <name> --set description="..." --set rollout_status=<uuid>` (CLI field id is `rollout_status`; `--set rolloutStatus.id=` doesn't match the spec's mutable field id and fails) |
| List definitions | `harness_list` · `fme_feature_flag_definition` · `params.feature_flag_name` · `filters: { offset: 0, limit: 100 }` (advance offset through every page) · `compact: false` | `harness list feature_flag:definition <flag> --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |
| Delete definition | `harness_delete` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness delete feature_flag:definition <flag> --env <env-id>` |
| Archive flag | `harness_execute` · `fme_feature_flag` · `action="archive"` · `params.feature_flag_name` · `body: { comment?, title? }` | `harness execute feature_flag:archive <name> --comment "..." --title "..."` |
| Unarchive flag | `harness_execute` · `fme_feature_flag` · `action="unarchive"` · `params.feature_flag_name` · `body: { comment?, title? }` | `harness execute feature_flag:unarchive <name> --comment "..."` |
| Delete flag | `harness_delete` · `fme_feature_flag` · `params.feature_flag_name` | `harness delete feature_flag <name>` |
| List experiments | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, environment_id?, status: ["ACTIVE", "PAUSED"], offset: 0, limit: 100 }` (apply [pagination completeness checks](../../references/fme/tool-map.md#pagination)) · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <name> --status ACTIVE --json`, then again with `--status PAUSED` |
| List rollout statuses | `harness_list` · `fme_rollout_status` · `compact: false` | `harness list rollout_status --json` |

## Output

Structured summary per [operation-summary.md](../../templates/operation-summary.md):
- **Metadata:** before → after for changed fields
- **Archive readiness:** verdict (ready / caution / blocked), per-env `impressions.lastImpressionAt`, active experiments, dependents (if checked)
- **Archive/unarchive/delete:** verification result (status or 404), per-env impact
- Next steps or follow-up actions

## Instructions

Follow [write-safety.md](../../references/fme/write-safety.md) for all writes. Concepts are in [concepts.md](../../references/fme/concepts.md).

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Restate scope before proceeding.

### Phase 2: Collect inputs

Ask for flag name(s) and the operation. For metadata updates, ask which fields to change. For delete definition, ask for the target environment ID. If the user asks "is this flag safe to archive", run the archive readiness gate (Phase 5) and stop there.

### Phase 3: Read current state

**Get flag** metadata. For archive/unarchive/delete operations, also **list definitions** through every page using explicit MCP `filters.limit: 100`; `size` does not control this list. Follow [pagination](../../references/fme/tool-map.md#pagination) for definitions, environments and experiments; incomplete inventories stop readiness/deletion checks. Report current metadata (description, tags, owners, rolloutStatus, status) and per-env definition summary (environment ID/name, impressions.lastImpressionAt, isKilled, defaultTreatment).

### Phase 4: Metadata update

If updating **rollout status**, **list rollout statuses** first, resolve the user's name to the UUID, then show the resolved name. Tags and owners are arrays and replaced whole in a merge patch. Read first, merge the user's change, and send the full new array.

Present the plan: `<flag> metadata update — <reason>`. Show before → after for each changed field. STOP and confirm per [write-safety.md](../../references/fme/write-safety.md).

**Update flag** with rolloutStatus as `{id: "<uuid>"}`. **Verify** and confirm fields match the plan.

### Phase 5: Archive readiness gate

Run **every time** before archive, even if checked earlier. Four checks gather data, then present the verdict per [concepts.md](../../references/fme/concepts.md#staleness-and-readiness) and [write-safety.md](../../references/fme/write-safety.md#experiment-check):

1. **Impressions per environment:** **List definitions** for the flag. Record `impressions.lastImpressionAt` (ISO-8601; `null` = never evaluated; absent = unknown) for each environment and note whether it's production.

2. **Experiment check:** **List experiments** for this flag across all environments with status ACTIVE and PAUSED, applying the shared pagination completeness checks (both status queries on CLI); a full page with a page-length `total` still needs another request. An incomplete scan stops the write. ACTIVE → **blocked** (STOP). PAUSED → **caution** (warn, require explicit acknowledgment per [write-safety.md](../../references/fme/write-safety.md#experiment-check)). COMPLETED → ignore.

3. **Dependent flags:** Opt-in scan per [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans). If declined, mark `dependents: unchecked`.

4. **Already archived:** Check the flag's status field. If ARCHIVED, report it and skip archive (no-op).

Present the verdict (**ready** / **caution** / **blocked**) per [concepts.md](../../references/fme/concepts.md#staleness-and-readiness), with every reason. **blocked** stops the archive; **caution** needs explicit acknowledgment. Recommend `cleanup-feature-flags` first if any production environment has recent traffic. STOP here if the user asked "is this safe to archive".

### Phase 6: Archive

Run the readiness gate (Phase 5). If **blocked**, STOP. If **caution**, require explicit acknowledgment. Explain: "Archiving `<flag>` affects **all** environments. SDKs will return `control`."

Confirm per [write-safety.md](../../references/fme/write-safety.md): "This archives `<flag>` in **all** environments. SDKs will return `control`. Archive?"

**Archive flag** with audit comment and title. On 409 (OPA governance): report it, never bypass, never delete instead. STOP. **Verify:** status field is ARCHIVED.

### Phase 7: Unarchive

Read the flag and all definitions first (Phase 3). Targeting resumes as it was when the flag was archived. Confirm per [write-safety.md](../../references/fme/write-safety.md): "Unarchiving `<flag>` will resume the previous targeting. <per-env summary>. Unarchive?"

**Unarchive flag** with audit comment and title. On 409 (dependents block it): report the error. STOP. **Verify:** status field is ACTIVE.

### Phase 8: Delete definition (one environment)

**List environments** to check isProduction. **List experiments** for the flag (ACTIVE and PAUSED) scoped to this environment, completing every page per the [experiment check](../../references/fme/write-safety.md#experiment-check). **ACTIVE → blocked: STOP; acknowledgement cannot permit definition deletion. PAUSED → caution: warn and require explicit acknowledgement. COMPLETED → ignore.** An incomplete or failed experiment scan also stops deletion. Do not pause/complete an experiment automatically to bypass the block; resolving its lifecycle is a separate approved workflow followed by a fresh check. Read the current definition and report its live `defaultTreatment` and whether it's killed, so the confirmation names what's being removed, not just the environment. Explain: "Deleting the `<flag>` definition in `<env>` (currently serving `<defaultTreatment>`) means SDKs in that environment will get `control`." Only after the gate passes, confirm per [write-safety.md](../../references/fme/write-safety.md).

**Delete definition.** **Verify** with a 404 on get. Expect 404. If still present, report failure.

### Phase 9: Delete flag

**Prefer archive.** Explain that delete is permanent and also deletes every environment's definition. Before deleting, run the dependent-flag scan (Phase 5 check 3), because a dependent makes the delete fail with an unhelpful error. Require archive first (run Phase 6) plus a second, separate confirmation naming the flag. Only proceed if the user explicitly confirms both steps.

Confirm: "This permanently deletes `<flag>` and all its definitions. This can't be undone. Delete?" **Delete flag.** If the delete fails, report the error and STOP. **Verify** with a 404 on get. Expect 404. If still present, report failure.

### Phase 10: Bulk (explicit list ≤ 20 flags)

For discovering candidates across a project, route to `discover-feature-flags`. Run the archive readiness gate (Phase 5) per flag. Present one table: Flag | Verdict | Reasons. Confirm once for the ready ones only. Each caution flag needs its own acknowledgment; blocked flags are skipped. Execute sequentially and report per-flag results.

## Examples

- "Update the description for `dark-mode` to 'Enable new dark theme UI'" — Metadata update; confirm and update.
- "Is `new-checkout-flow` safe to archive?" — Run readiness gate (Phase 5); report verdict and stop.
- "Archive `beta-feature`" — Readiness gate, confirm, archive, verify.
- "Unarchive `holiday-promo`" — Read definitions, show what will resume, confirm, unarchive, verify.
- "Delete the `test-flag` definition in staging" — Complete the environment-scoped experiment check; ACTIVE blocks, PAUSED needs acknowledgement. Only then confirm, delete and verify 404.
- "Delete `old-experiment`" — Prefer archive; if user insists, archive first, confirm again, delete flag, verify 404.
- "Change the rollout status to 'Complete' for `launched-feature`" — Resolve status name to UUID, confirm, update, verify.

## Performance Notes

- One fully paginated definition inventory covers a flag's environments; it can require multiple requests. Never treat a page as the complete set.
- Dependent flag scan cost: one paginated definition inventory per flag in the project. Offer it as opt-in per [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).
- Bulk operations (≤ 20): readiness checks are parallel reads; writes are sequential.

## Troubleshooting

| Issue | Action |
|-------|--------|
| 409 on archive (governance) | Report the error; never bypass, never delete instead |
| 409 on unarchive (dependents) | Report the error; STOP |
| Delete flag fails | Likely a dependent flag or pending approval. Run the dependents scan; report the error and STOP. Don't retry. |
| Tags not updating | Read first; send the full new array (merge patch replaces whole array) |
| Rollout status name not found | List rollout statuses; show available names to user |
| `impressions.lastImpressionAt` missing | Treat as unknown (not "unused"); recommend caution and require ack before archive |

See [tool-map.md](../../references/fme/tool-map.md#common-errors) for generic errors.
