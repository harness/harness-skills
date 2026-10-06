---
name: update-flag-targeting
description: >-
  Change how a Harness FME feature flag serves traffic in environments. Covers
  percentage rollout, individual targets, targeting rules (attribute/segment/flag-dependency),
  defaultTreatment, trafficAllocation, treatments, kill/restore, and copying or
  initializing a definition in an environment. Use when asked to ramp a flag, add rules/users, change allocation,
  kill/restore, or promote config. Not for creating flags (create-feature-flag), metadata
  like tags/owners/archive (manage-flag-lifecycle), segment keys (manage-segments),
  pipeline rollouts (fme-pipeline), or flag analysis (explain-flag). Trigger phrases:
  update targeting, ramp flag, percentage rollout, add rule, add users, kill flag, restore,
  copy config.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Update Flag Targeting

Change how an existing Harness FME feature flag serves traffic in one or more environments. **Always read the current definition first**, then merge-patch only what changes. Show a diff of just what changed and use plain-language before/after to describe who gets what.

Related: Segment membership changes are `/manage-segments`; deep flag analysis (impact, dependencies, single-flag state) is `/explain-flag`. Reverse-lookup scans (dependents, segment usage) are in [tool-map.md](../../references/fme/tool-map.md#reverse-lookup-scans).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List flag definitions | `harness_list` · `fme_feature_flag_definition` · `params: { feature_flag_name }` · `compact: false` | `harness list feature_flag:definition <flag> --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |
| Get parent flag definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name: <parent>, environment_id }` | `harness get feature_flag:definition <parent> --env <env-id> --json` |
| Update definition | `harness_update` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { <fields>, comment, title? }` | `harness update feature_flag:definition <flag> --env <env-id> -f patch.json` (include `comment`/supported `title` in the file) |
| Create definition | `harness_create` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments, defaultTreatment, defaultRule, rules?, baselineTreatment?, trafficAllocation?, comment? }` | `harness create feature_flag:definition <flag> --env <env-id> -f def.json` |
| Kill flag | `harness_execute` · `fme_feature_flag` · `action="kill"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:kill <flag> --env <env-id> --comment <text>` |
| Restore flag | `harness_execute` · `fme_feature_flag` · `action="restore"` · `params: { feature_flag_name, environment_id }` · `body: { comment?, title? }?` | `harness execute feature_flag:restore <flag> --env <env-id> --comment <text>` |
| Get segment metadata (all types) | `harness_get` · `fme_segment` · `params: { segment_name, segment_type }` | `harness get segment <segment> --segment-type <type> --json` |
| Get STANDARD segment definition | `harness_get` · `fme_segment_definition` · `params: { segment_name, environment_id }` | `harness get segment:definition <segment> --env <env-id> --json` |
| List experiments | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, environment_id, status: ["ACTIVE", "PAUSED"] }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <flag> --env <env-id> --status ACTIVE --json`, then again with `--status PAUSED` |

## Instructions

See [concepts.md](../../references/fme/concepts.md) for FME evaluation order, killed state, treatments vs control, and round-tripping shapes. See [write-safety.md](../../references/fme/write-safety.md) for the confirm-before-write protocol; this skill links to it and does not duplicate it.

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Ask for `org_id` and `project_id` if not already known. Restate: `Working in org=..., project=...`

### Phase 2: Gather intent

Ask only for what's missing:
1. **Flag name** (case-sensitive identifier)
2. **Target environments** (names or IDs, or "all")
3. **What to change** (map the user's request to one or more operations in the table below)

### Phase 3: Read current state

Always **List flag definitions** for every target environment before planning changes. Never compose rules, targets, or matchers from memory — copy shapes from the live definition or another flag in the project that already uses that shape. If no example exists, warn that the shape is unverified, try it in a non-production env first, and let the API's 400 messages guide you (see [schema-validation-loop.md](../../references/schema-validation-loop.md)).

Note per environment from the definition:
- `isKilled` (boolean), `defaultTreatment`, `treatments` (case-sensitive; read them, don't guess)
- `defaultRule` (array of `{treatment, size}` summing to 100)
- `rules` (array, replaced whole on update)
- `trafficAllocation` (0-100; keys outside it get `defaultTreatment`)
- individual targets and segment references (shapes undocumented; round-trip them)
- `impressions.lastImpressionAt` (usage signal; `null` = never received traffic; absent = unknown)

**List environments** to resolve names to IDs and note `isProduction`.

### Phase 4: Safety checks (before planning)

Run these checks before composing the plan. Stop at the first failure and report it to the user.

| Check | How | What to report |
|-------|-----|----------------|
| **Experiment** | **List experiments** for the flag (and environment), filtering to ACTIVE and PAUSED. Apply the [experiment check](../../references/fme/write-safety.md#experiment-check) protocol | ACTIVE: explicit acknowledgement required; PAUSED: warn + acknowledgement; COMPLETED: ignore |
| **Segment reference** | For every new/changed rule matcher or treatment membership, resolve STANDARD/LARGE/RULE_BASED metadata and verify the target-env definition through [that type's workflow](../manage-segments/SKILL.md#phase-3-execute-operation). The listed definition endpoint is STANDARD-only | Distinguish confirmed missing from unverified because the current tool lacks the operation. Stop the dependent write until verified; never use a STANDARD lookup for LARGE/RULE_BASED or silently switch to legacy scope |
| **Flag dependency (IN_SPLIT)** | For each `depends: {splitName, treatment}` in a new or updated rule, **Get parent flag definition** and verify the treatment exists in `treatments` | "Flag `<parent>` has no definition (or treatment `<treatment>` doesn't exist) in `<env>`." |
| **Treatment reference** | Every treatment in rules, defaultRule, individual targets, and `defaultTreatment` must exist in the `treatments` array | "Treatment `<treatment>` not found. Add it to `treatments` first." |
| **Bucket sum** | The `size` fields across all `{treatment, size}` buckets in `defaultRule` or a rule must sum to 100 | "Bucket sizes sum to `<sum>`, not 100. Fix the split." |
| **Killed flag** | Write/read back approved targeting while killed, then separately confirm restore and re-run the [experiment check](../../references/fme/write-safety.md#experiment-check). Inspect the entire patch first: changing `defaultTreatment`, removing/renaming it, or changing its configuration affects killed traffic immediately | Name the current served treatment/config and any immediate change. Only promise unchanged traffic if that pair remains unchanged; never restore stale targeting first |

### Phase 5: Plan the change

Based on the user's intent and current state, compose the updated definition. See [targeting-recipes.md](references/targeting-recipes.md) for per-operation shape details.

Map user intent to operations:

| User wants | Recipe | Fields to update |
|-----------|--------|------------------|
| Percentage rollout / ramp | (a) | Change `defaultRule` buckets, or a specific rule's `buckets` |
| Ramp one rule | (b) | Copy full `rules` array, change that rule's `buckets` |
| Add/edit/remove/reorder targeting rules | (c) | Replace full `rules` array |
| Add/remove individual targets | (d) | Round-trip the individual-targets structure |
| Change defaultTreatment | (e) | Update `defaultTreatment` |
| Change trafficAllocation | (f) | Update `trafficAllocation` (0-100) |
| Add/rename treatment or edit configurations | (g) | Replace full `treatments` array; update all references |
| Copy one env's definition to another | (h) | Copy create/update body fields; check segments and IN_SPLIT parents exist |
| Initialize a definition where none exists | (i) | Create with safe default: flag's treatments (or `on`/`off`), everyone off, no rules |
| Kill / restore | (j) | Emergency path: **Kill flag** or **Restore flag** |

Show a **diff** of just the fields that changed and state the **before/after in plain language** per environment. For non-production first, then production. For production environments, say: "This changes live production traffic in `<env>`."

### Phase 6: Confirm and execute

Follow [write-safety.md](../../references/fme/write-safety.md) for the protocol (present plan → STOP → explicit confirmation → execute non-prod first → production). Comment format: `"update-flag-targeting: <what> — <why>"`, e.g. `"update-flag-targeting: ramp new-checkout to 25% in staging — FME-123"`.

On errors: 400 (read API error, fix field, retry once per [schema-validation-loop.md](../../references/schema-validation-loop.md)); 404 (re-check identifiers, never create to fill); 409 (report as-is, stop).

### Phase 7: Verify and restate

Re-read each changed environment's definition, then describe the **live** behavior in the same plain-language form. If it doesn't match the plan, stop.

Summarize per [operation-summary.md](../../templates/operation-summary.md): operation, environments changed, before/after, what was confirmed, verification, risks, UI link.

## Examples

- "Ramp new-checkout to 10% in staging" — (a) Percentage rollout.
- "Add a targeting rule for beta users in production" — (c) Add targeting rule.
- "Add user-key-123 to the on treatment" — (d) Add individual targets.
- "Kill the flag in production" — (j) Kill (emergency path).
- "Copy staging config to production" — (h) Copy env to env.
- "Set up the flag in qa, it has no definition there" — (i) Initialize safe default.

## Performance Notes

- One **List flag definitions** for the flag returns all envs at once — prefer over N separate gets.
- Merge-patch update: omit a field to leave it unchanged. `treatments`, `rules`, and `defaultRule` can't be `null` and are replaced whole, so always send the complete array.
- Large multi-env changes: run non-production envs first to verify the shape works before touching production.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| 400: buckets don't sum to 100 | Bucket `size` fields across `{treatment, size}` in `defaultRule` or a rule must sum to 100 | Adjust the sizes to sum to 100 |
| 400: unknown treatment | A rule, defaultRule, or defaultTreatment references a treatment not in the `treatments` array | Add the treatment to `treatments` first, or fix the reference |
| Targeting changed but traffic is unchanged | The flag is killed | Verify the approved targeting while it remains killed, re-check experiments, then obtain explicit approval before restoring. Never restore stale targeting first |
| 409 governance/approval | OPA policy blocked the write or turned it into a pending approval | Report the response as-is. Never retry around it or try another route. |
| Concurrent edit detected | Another user or process modified the definition between your read and write | Stop and re-plan from the new state |

Generic errors: see [tool-map.md](../../references/fme/tool-map.md#common-errors).

## References

- [targeting-recipes.md](references/targeting-recipes.md) — per-operation shape details
- [concepts.md](../../references/fme/concepts.md) — FME evaluation order, treatments, killed state
- [tool-map.md](../../references/fme/tool-map.md) — tool names, params, common errors
- [write-safety.md](../../references/fme/write-safety.md) — confirm-before-write protocol, experiment check
- [scope-establishment.md](../../references/scope-establishment.md) — org/project scope rules
- [schema-validation-loop.md](../../references/schema-validation-loop.md) — validation error recovery
- [operation-summary.md](../../templates/operation-summary.md) — structured completion summary
