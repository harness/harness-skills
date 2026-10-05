---
name: manage-experiments
description: >-
  Create, update (metrics, dates, description, hypothesis, baseline/comparison
  treatments, status), or delete Harness FME experiments. Delegates metric
  selection to choose-metric, metric creation to create-metric, event wiring to
  instrument-metric, results to review-experiment-results, flag/definition prep
  to create-feature-flag and update-flag-targeting. Use when asked to create,
  modify, pause, resume, complete, or delete an experiment. Do not use for
  explaining results (review-experiment-results). Trigger phrases: create
  experiment, set up A/B test, design experiment, launch test, update
  experiment, pause/resume/complete experiment, delete experiment.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Manage Experiments

Create, update, or delete FME experiments. Orchestrates decisions and delegates
metric selection, flag setup, and results interpretation to specialist skills.

Related: [choose-metric](../choose-metric/SKILL.md) (metric selection),
[create-metric](../create-metric/SKILL.md) (metric creation),
[instrument-metric](../instrument-metric/SKILL.md) (event wiring),
[review-experiment-results](../review-experiment-results/SKILL.md) (results),
[create-feature-flag](../create-feature-flag/SKILL.md),
[update-flag-targeting](../update-flag-targeting/SKILL.md).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| **List experiments** | `harness_list` · `fme_experiment` · `filters: { parent_type, parent_name?, environment_id?, status?: ["ACTIVE", "PAUSED"], … }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG [--search <name>] [--status ACTIVE]`, then again with `--status PAUSED` |
| **Get experiment** | `harness_get` · `fme_experiment` · `params: { experiment_id }` | `harness get experiment <experiment-id>` |
| **Create experiment** | `harness_create` · `fme_experiment` · `params: { environment_id }` · `body: { parent, name, startAt, endAt, baselineTreatment, comparisonTreatments, rule: "default rule", … }` | `harness create experiment <name> --parent-type FEATURE_FLAG --parent-name <flag> --env <env-id> --start-at <iso8601> --end-at <iso8601> --baseline-treatment <t1> --comparison-treatment <t2>` |
| **Update experiment** | `harness_update` · `fme_experiment` · `params: { experiment_id }` · `body: { description?, hypothesis?, startAt?, endAt?, keyMetrics?, status?, … }` | `harness update experiment <experiment-id> --set description=foo` |
| **Delete experiment** | `harness_delete` · `fme_experiment` · `params: { experiment_id }` | `harness delete experiment <experiment-id>` |
| **List environments** | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| **Get definition** | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag-name> --env <env-id>` |

## Instructions

### Phase 1: Establish scope
Follow [scope-establishment.md](../../references/scope-establishment.md).

### Phase 2: Choose operation

**Create**: new experiment on a flag/AI Config.  
**Update**: change description, hypothesis, dates, metrics, baseline/comparison
treatments, or status (pause/resume/complete/archive).  
**Delete**: hard delete (permanent, no archive/restore).

---

### Create experiment

#### Step 1: Resolve parent and environment

Default parent type: `FEATURE_FLAG`. If flag doesn't exist, route to [create-feature-flag](../create-feature-flag/SKILL.md), then return here. **List environments**; ask which environment if not stated.

#### Step 2: Confirm treatments against live definition

**Get definition** for the flag in the chosen environment. 404 = no definition; route to [update-flag-targeting](../update-flag-targeting/SKILL.md) to initialize it, then return here.

Read `treatments[].name`. Experiment's `baselineTreatment` and `comparisonTreatments` must match real treatment names. Default baseline = definition's `baselineTreatment`, but confirm with user. Fewer than 2 treatments → stop (see [stop-conditions.md](./references/stop-conditions.md)).

Check traffic readiness: `isKilled: false`, `trafficAllocation > 0`, baseline and each comparison treatment have `size > 0` in `defaultRule` buckets (or in the targeting rule the experiment will use). If any check fails, warn and ask whether to proceed. Fixing it requires [update-flag-targeting](../update-flag-targeting/SKILL.md).

**List experiments** for the parent flag and environment, with ACTIVE and PAUSED status. Apply the [experiment check](../../references/fme/write-safety.md#experiment-check): ACTIVE means confirm the user wants a second experiment; PAUSED means warn and require explicit acknowledgement.

#### Step 3: Hypothesis

Get hypothesis: *"if [change], then [metric] will increase/decrease because [reasoning]"* (max 500 chars). Link [concepts.md](../../references/fme/concepts.md#experiments-and-metrics). Missing or non-causal hypothesis → stop (see [stop-conditions.md](./references/stop-conditions.md)).

#### Step 4: Metrics

Hand off to [choose-metric](../choose-metric/SKILL.md) to select key and supporting metrics. If no suitable metric exists, route to [create-metric](../create-metric/SKILL.md) (and [instrument-metric](../instrument-metric/SKILL.md) if event missing). Return here with metric IDs once complete.

#### Step 5: Experiment window

`startAt`/`endAt` are required ISO-8601 timestamps. Ask explicitly; no default duration.

#### Step 6: Draft and confirm

Present full payload: parent (type, name), name (2-250 chars, unique), description, hypothesis, startAt/endAt (ISO-8601), baselineTreatment, comparisonTreatments, keyMetrics, supportingMetrics, rule (set to `"default rule"` unless the user wants results from a specific targeting rule label; results only count impressions whose label matches the experiment's `rule`), owners, tags. Link [write-safety.md](../../references/fme/write-safety.md). Do not send `assignmentSource` (400 if present). **STOP HERE.** Wait for explicit confirmation.

#### Step 7: Create

**Create experiment** with confirmed payload. 409 = duplicate name; report the conflict and ask the user for a new name (never rename silently). 404 = parent doesn't exist in environment; back to Step 1.

#### Step 8: Verify

**Get experiment** by id from create response. Compare `baselineTreatment`, `comparisonTreatments`, `keyMetrics.id`, `supportingMetrics.id` to draft. Report `status` (typically `ACTIVE` on create). Hand off to [review-experiment-results](../review-experiment-results/SKILL.md) once data collected.

---

### Update experiment

#### Step 1: Get current experiment

**Get experiment** by id or name (via **List experiments**). Show current `status`, `description`, `hypothesis`, `startAt`, `endAt`, `baselineTreatment`, `comparisonTreatments`, `keyMetrics`, `supportingMetrics`, `rule`.

#### Step 2: Draft changes

Ask what to update: description, hypothesis, dates, baseline/comparison treatments, metrics, status, rule, owners, tags. For metrics, route to [choose-metric](../choose-metric/SKILL.md) if selecting new ones.

When updating `baselineTreatment` or `comparisonTreatments`, verify the treatments exist in the flag definition for the experiment's environment (**Get definition** for that environment and check `treatments[].name`, same as create Step 2). See [stop-conditions.md](./references/stop-conditions.md).

Status transitions: `ACTIVE` ↔ `PAUSED` ↔ `COMPLETED`. Changing metrics or dates on ACTIVE experiment → explicit warning. Clearable fields: `description`, `hypothesis`, `rule`, `keyMetrics`, `supportingMetrics`, `tags`. Non-clearable: `name`, `startAt`, `endAt`, `baselineTreatment`, `comparisonTreatments`, `status`.

#### Step 3: Confirm and update

Show diff (current vs. new). Link [write-safety.md](../../references/fme/write-safety.md). If ACTIVE experiment and changing key fields, add explicit warning.

**Update experiment** with merge patch body. 409 = duplicate name. 400 = invalid field or null on non-clearable.

#### Step 4: Verify

**Get experiment** again. Compare updated fields. Report new `status` if changed.

---

### Delete experiment

#### Step 1: Get experiment

**Get experiment** by id or name (via **List experiments**). Show name, status, parent, environment, dates.

#### Step 2: Confirm delete

Hard delete = permanent, no archive/restore. Stricter confirmation required. Offer status update to `COMPLETED` instead (update operation). Link [write-safety.md](../../references/fme/write-safety.md).

#### Step 3: Delete

**Delete experiment**. Confirm deletion; parent flag not affected.

## Examples

- "Set up A/B test on new-checkout flag" → create flow
- "Pause experiment pricing_test_2" → update status
- "Update experiment abc-123 to end next Friday" → update endAt
- "Delete experiment old_test" → delete flow with confirmation

## Performance Notes

- Resolve environment and definition once (create Step 1-2), not per metric
- Metric selection is [choose-metric](../choose-metric/SKILL.md)'s scope
- Update uses merge patch: only changed fields in body

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| 404 on create even though flag exists | Parent must exist in chosen environment; check **Get definition** for that environment |
| User wants to change treatments | Route to [update-flag-targeting](../update-flag-targeting/SKILL.md) to modify definition, then return here |
| Experiment needs workspace guardrail metric | Guardrails apply automatically; never set via keyMetrics/supportingMetrics |
| 400 on update with null | Field is non-clearable; omit it to leave unchanged |
| Empty keyMetrics on create | Allowed but no winner criterion; warn and confirm before Step 6 draft |
| ACTIVE experiment blocks targeting change | See [write-safety.md](../../references/fme/write-safety.md#experiment-check); require explicit acknowledgement |
