---
name: fme-pipeline
description: >-
  Generate Harness FME pipelines for flag rollout scenarios: progressive ramp,
  multi-env promotion, beta cohorts, config promotion, bootstrap, retirement,
  segment sync, test targeting. Composes Custom/FeatureFlag stages with FmeFlag*
  steps plus optional Harness/Jira/ServiceNow approvals, Wait steps, and ticket
  integration. Use when asked to build a flag rollout pipeline, promote flags
  across environments, add approval gates, or automate flag lifecycle. Do not use
  for direct flag operations (manage-feature-flags) or general CI/CD
  (create-pipeline). Trigger phrases: FME pipeline, feature flag pipeline, flag rollout pipeline,
  progressive rollout, multi-environment promotion, flag bootstrap.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# FME Pipeline

Compose Harness FME pipeline stages and native `FmeFlag*` steps for flag rollout scenarios. Generate tailored pipelines — progressive ramp, multi-environment promotion, beta cohorts, config promotion, bootstrap, retirement, segment sync, and test targeting — rather than a single fixed template.

Direct flag operations via MCP → `/manage-feature-flags`. General CI/CD → `/create-pipeline`. Running pipelines → `/run-pipeline`.

## Instructions

**Allowed MCP tools only:** `harness_list`, `harness_get`, `harness_create`, `harness_update`.

**Allowed resource types only:** `pipeline`, `fme_environment`, `fme_feature_flag`, `fme_feature_flag_definition`, `fme_rollout_status`, `user_group`, `connector`, and `project` (existence check only — do not create projects).

**Confirm before write.** Do not call `harness_create` or `harness_update` until the user explicitly confirms the plan.

**No automatic metric rollback.** Harness does not auto-rollback flags on metric regression. `FmeMetricCheck` fails the step when its JEXL condition is true — it does not kill the flag. Rollback is an explicit `FmeFlagKill` stage or failure path.

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Ask for `org_id` and `project_id` if missing. Restate: `Working in org=..., project=...`

### Phase 2: Choose mode

| Mode | User signal | Outcome |
|------|-------------|---------|
| **Design** (default if ambiguous) | "How should we roll out…?", "What steps do we need?" | Pattern + stage plan only; no YAML write |
| **New pipeline** | "Create a rollout pipeline for…" | Plan + YAML draft; `harness_create` only after explicit confirm |
| **Update existing** | "Add FME stages to pipeline X" | Fetch pipeline, merge stages, show diff; `harness_update` only after explicit confirm |

### Phase 3: Pick scenario(s)

Map user intent to scenario codes in [scenarios.md](references/scenarios.md):

| User intent | Scenario | Primary steps |
|-------------|----------|---------------|
| Increase traffic in one environment | **R1** Progressive ramp | `FmeFlagRestore` → `FmeFlagDefaultAllocation` (5→25→50→100) |
| Promote across dev/qa/staging/prod | **R2** Multi-environment promotion | ONE STAGE PER ENVIRONMENT, each with restore + allocation + optional gates |
| Beta users first, then everyone | **R3** Beta cohort | `FmeFlagAddRemoveIndividualTargets` or `FmeFlagSetTargetingRules` → default allocation |
| Copy validated staging config to prod | **R4** Config promotion | `FmeFlagDefinitionInstructions` or `FmeFlagPatchDefinition` |
| Create flag with initial targeting | **L1** Flag bootstrap | `FmeFlagCreate` → treatments → kill/restore/targets per env → flagsets |
| Archive a fully-launched flag | **L2** Flag retirement | Verify 100% → `FmeFlagUpdate` (rolloutStatus) → remove flagsets → `FmeFlagArchive` |
| Import user keys from external system | **L3** Segment sync | `ShellScript` fetches keys → `FmeSegmentAddRemoveTargets` |
| Add test keys, run tests, clean up | **L4** Test-user targeting | `FmeFlagAddRemoveIndividualTargets` add → `ShellScript` tests → remove keys |

Scenarios can be combined (e.g., R3 inside each environment of R2). See [scenarios.md](references/scenarios.md) for full patterns.

### Phase 4: Gather inputs

Collect only what is missing. Do not guess environment names, treatments, or approver groups.

**For all scenarios:**
1. Flag name (`feature_flag_name`, case-sensitive)
2. Test treatment and control treatment (or boolean on/off)
3. Target environments
4. Existing pipeline URL/identifier (update mode only)

**For R2 (multi-environment promotion), gather per-env plan:**

| Environment | Ramp schedule | Gate before env | Gate between steps |
|-------------|---------------|-----------------|-------------------|
| dev | 100 | none | none |
| qa | 100 | none | none |
| staging | 100 | none | Wait 1h |
| prod-us | 1, 5, 25, 50, 100 | Harness approval | Wait 2h |

**Ask:** Reusable pipeline with flag name as `<+input>` variable, or one-off pipeline with literal flag name?

**Gate policy:** Never add a gate or metric check the user didn't explicitly agree to. You may suggest one approval before production ONCE; if declined, drop it.

**Ask:** Which building blocks to include (see [building-blocks.md](references/building-blocks.md)):
- Gates: `HarnessApproval`, `Wait`, `FmeMetricCheck`
- Rollback: `FmeFlagKill` stage when `pipelineStatus: Failure`
- Ticket integration: `JiraCreate`/`JiraUpdate` or `ServiceNowCreate`/`ServiceNowUpdate` at milestones
- Metric checks: `FmeMetricCheck` after each allocation (does NOT auto-roll back)
- Answer "none" is valid — not all rollouts need approvals or ticket integration

**For approval gates:**
- Approvers: user groups, minimum count

### Phase 5: Discover FME context via MCP

**MCP v2 identifier nesting** — required; bare top-level FME field names are stripped by the tool schema:

| Call | Where identifiers go |
|------|----------------------|
| `harness_list` with required list filters | `filters: { feature_flag_name: "..." }` |
| `harness_get` for `fme_feature_flag` / `fme_feature_flag_definition` | `params: { feature_flag_name: "...", environment_id: "..." }` (`environment_id` when per-env) |
| `harness_get` / `harness_update` for `pipeline` | top-level `resource_id` |
| `harness_list` project verify (pre-create only) | top-level `resource_type: "project"`, `org_id` |

**Discover per scenario/block:**

- **Environments** (`fme_environment`): List all FME environments via `harness_list`. Build promotion-order proposal: non-production first, production last (use `isProduction` when present). **Confirm order with the user.**
- **Flag state** (`fme_feature_flag`, `fme_feature_flag_definition`): Get flag metadata and per-env definitions via `harness_get` (flag) + `harness_list` with `filters: { feature_flag_name: "..." }` (definitions). Note per environment: `isKilled`, `defaultTreatment`, `defaultRule` (treatment % split), `trafficAllocation` (experiment participation only — NOT proof of full rollout), `rules`, treatment targeting lists. Use this to avoid contradicting live state. A killed flag cannot take traffic — plan `FmeFlagRestore` before allocation.
- **Rollout status values** (`fme_rollout_status`): For L2 (retirement), discover valid rollout status values via `harness_list`.
- **Approvers** (`user_group`): For approval gates, list user groups via `harness_list` to confirm approver group names.
- **Ticket connectors** (`connector`): If ticket integration is requested, list `connector` via `harness_list` and pick ones whose type is Jira or ServiceNow. If none exist, hand off to `/create-connector`.

**One `fme_feature_flag_definition` list via filters returns all envs** — prefer over N gets during planning. Per-env detail: `harness_get` with `params: { feature_flag_name, environment_id }` if needed.

If MCP is unavailable, skip discovery, say so, and ask the user for environment names and treatments — do not guess.

### Phase 6: Present plan and wait

Before any pipeline write, show:

1. Scenario name(s) and rationale
2. Environment promotion order (confirm from MCP `fme_environment` list)
3. Stage table:

| Stage | Environment | Steps in order | Gates | Notes |
|-------|-------------|----------------|-------|-------|
| ff_dev | dev | FmeFlagRestore, FmeFlagDefaultAllocation (100% on) | none | Full launch |
| ff_staging | staging | FmeFlagRestore, FmeFlagDefaultAllocation (100% on) | Wait 1h after | Full launch + soak |
| ff_prod | prod | HarnessApproval, FmeFlagRestore, FmeFlagDefaultAllocation (10, 25, 50, 100% on) | Wait 2h between | Approval inline, progressive ramp |

4. **Pipeline variables** (for reusable pipelines): `flagName` as `<+input>`, treatment names as variables (e.g., `onTreatment` default `on`, `offTreatment` default `off`). **Treatment `<+input>` directly in allocation is rejected by the schema** — use pipeline variables instead: `<+pipeline.variables.onTreatment>`.
5. **Prerequisites:** Verify project exists, confirm flag exists (or will be created in bootstrap), confirm approver groups and connectors exist.
6. **Per-env:** Held vs released on pipeline run.
7. **Rollback path:** `FmeFlagKill` stage when `pipelineStatus: Failure`, or manual rollback stage.
8. **Current FME state vs planned end state** (from definitions).
9. **New vs update**, and MCP action if any.

**Do not proceed until the user explicitly confirms.**

### Phase 7: Generate YAML

Compose from [blueprints.md](references/blueprints.md) (full scenario patterns) and [building-blocks.md](references/building-blocks.md) (reusable gates, rollback, ticket integration). Get exact step field names and shapes from [references/step-catalog.md](references/step-catalog.md).

**YAML rules:**

- Dedicated FME stages: `type: Custom` (default per Harness docs). Mixed FME + Wait/tests: also `type: Custom`. The schema also allows `type: FeatureFlag`, but Custom is more flexible.
- Every `Custom` stage that mutates flags needs `failureStrategies` (use `MarkAsFailure` on errors; do not use `StageRollback` — Custom stages have no rollback section).
- Stage names: `^[a-zA-Z_0-9-.][-0-9a-zA-Z_\s.]{0,127}$` (no commas).
- Step identifiers: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`.
- `environment` in step spec = FME environment **name or ID** (case-sensitive); confirm from `fme_environment` list.
- Allocation amounts are integers 0–100 summing to 100. **Quote treatment names that YAML treats as booleans** (`"on"`, `"off"`, `"yes"`, `"no"`).
- Stage `when.pipelineStatus` is `Success`, `Failure`, or `All` — not `Failed`.
- **Pipeline YAML must include the `pipeline:` root key** and be passed to MCP as a **string** (`yamlPipeline`) — do not pass a nested JSON `pipeline` object.
- **Treatment `<+input>` directly in allocation is rejected by the schema** — use pipeline variables: define `variables` under `pipeline:` spec, reference as `<+pipeline.variables.onTreatment>`.

**Step type naming traps:** Step YAML `type:` strings are strict and can differ from colloquial names or UI display labels. Always use the exact step `type:` strings from [references/step-catalog.md](references/step-catalog.md) (e.g., `FmeFlagSetIndividualTargets` not `FmeFlagSetTargets`, `FmeFlagAddRemoveIndividualTargets` not `FmeFlagAddRemoveTargets`, `FmeSegmentAddRemoveTargets` not `FmeSegmentAddRemoveKeys`). Do not "correct" these to UI-only or shorthand names.

**If update mode**, fetch current pipeline YAML before merging:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<org>"
  project_id: "<project>"
```

Merge new FME stages surgically; show diff. Never replace unrelated stages unless the user asked.

Show the YAML (or diff) to the user before MCP write.

### Phase 8: Create or update pipeline (after confirmation)

1. **Verify the project exists** — `harness_list` with `resource_type: "project"` and `org_id`. If missing, stop and ask (do not create a project in this skill).
2. **Create or update** using `yamlPipeline` as a **string**. Do not pass a nested JSON `pipeline` object.

**New pipeline:**

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<full pipeline YAML string, including 'pipeline:' root key>" }
```

**Update existing:**

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<full updated pipeline YAML string>" }
```

**Verify:**

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

On validation errors, read the API message, fix fields, retry.

Do **not** run the pipeline in this skill. Point the user to `/run-pipeline`.

### Phase 9: Hand-off summary

Summarize following [templates/operation-summary.md](../../templates/operation-summary.md):

- Operation (create/update pipeline), scope (org/project), pipeline identifier
- What each stage does (environment, steps, gates)
- What was confirmed (environments, treatments, current definition state, approvers, connectors)
- Rollback path (`FmeFlagKill` stage)
- How to run (`/run-pipeline`)
- Follow-up: further % increases may need another run or additional stages

## Not covered

These are explicitly out of scope for this skill. Refer users to the listed alternatives:

- **Triggers (webhook, scheduled, cron)**: This skill only creates pipelines. After the pipeline exists, use `/create-trigger` to automate it.
- **Scheduled launches**: Not covered. Manual pipeline execution only.
- **CD/CI coupling**: No CD or CI stages in this skill. Use `/create-pipeline` for CI/CD stages.
- **Governance and OPA**: Not covered as standalone scenarios.
- **Kill-switch runbook pipelines**: Kill-switch rollback is covered within scenarios (rollback stage), but dedicated runbook pipelines are out of scope.
- **Experiment launch and analysis**: FME experiments are separate from rollouts.
- **`FmeFlagSetImpressionTracking` and `FmeChangeProposalSubmit` steps**: Never generate these steps. They are out of scope.
- **Running pipelines**: This skill only creates/updates pipelines. Point users to `/run-pipeline`.
- **Direct flag changes via MCP**: This skill only creates pipelines with FME steps. For direct flag kill/restore/allocation via MCP, point users to `/manage-feature-flags`.

## Examples

**R1 — Progressive ramp in one environment:**
- "Build a pipeline to roll out `new-checkout-flow` 10% at a time in staging with approval before each increase" → Progressive % + approval gates.

**R2 — Multi-environment promotion (reusable pipeline):**
- "Promote `dark-mode` from dev → staging → prod, with prod needing approval and a slower ramp" → R2 with flag name as `<+input>`, per-env ramp schedules, approval before prod.
- "Create a reusable rollout pipeline that I can run for multiple flags" → R2 with flag name as `<+input>`, treatment names as variables.

**R3 — Beta cohort:**
- "Enable `new-search` for beta users first, then ramp to 10% → 50% → 100% for everyone" → Beta targeting + progressive ramp.

**R4 — Config promotion:**
- "Copy the staging targeting rules and allocation to prod" → Config promotion pattern.

**L1 — Flag bootstrap:**
- "Create `dark-mode` flag with `on` and `off` treatments, keep it killed in prod, restore it in dev" → Bootstrap pattern.

**L2 — Flag retirement:**
- "Archive `old-checkout-flow` now that it's at 100% `off` everywhere" → Retirement pattern (verify 100% first).

**L3 — Segment sync:**
- "Sync the `premium-users` segment from our database every night" → Segment sync pattern (ShellScript + FmeSegmentAddRemoveTargets).

**L4 — Test-user targeting:**
- "Add `test-user-1` and `test-user-2` to `new-checkout-flow` on in QA, run tests, then remove them" → Test targeting pattern.

**Combining scenarios:**
- "Promote `feature-x` across dev/staging/prod, with beta users first in each environment" → R3 inside each environment of R2.

**Update mode:**
- "Add FME stages to pipeline `payments_deploy` to restore the flag in prod" → Update mode.

**Rollback:**
- "Kill the flag if the pipeline fails" → Rollback stage with `FmeFlagKill` when `pipelineStatus: Failure`.

**Metric checks:**
- "Canary rollout with metric checks" → Design: Approval + Wait + `FmeMetricCheck` + `FmeFlagKill`; explain no auto-rollback.

**Out of scope (redirect):**
- "Create a flag right now (not a pipeline)" → `/manage-feature-flags`. A pipeline that bootstraps flags is L1.
- "Remove flag from code" → Out of scope.
- "Trigger the rollout pipeline on every commit" → Use `/create-trigger` after the pipeline exists.
- "Add CI/CD stages to build and deploy" → Use `/create-pipeline` for CI/CD.

## Performance Notes

- **One `fme_feature_flag_definition` list via filters returns all envs** — prefer over N gets during planning. Per-env detail: `harness_get` with `params: { feature_flag_name, environment_id }` if needed.
- **Design mode avoids pipeline API writes entirely** — fastest for brainstorming rollout plans.
- **Large multi-env pipelines**: Propose incremental delivery (staging first, prod in a follow-up) when the user has not committed to full promotion.
- **Keep SKILL.md focused**: Load step catalog and YAML examples from references on demand.

## Troubleshooting

### Environments disagree on targeting

Do not generate prod steps that contradict staging without calling it out. Offer config promotion (`FmeFlagPatchDefinition`) or manual alignment first.

### Flag is killed in target environment

Plan must include `FmeFlagRestore` before allocation. Mention current `isKilled` state in the plan.

### User wants metric-based auto-rollback

Explain Harness does not auto-kill on metric regression. Offer `FmeMetricCheck` or Custom checks that **fail the step**, plus an explicit `FmeFlagKill` rollback stage.

### `HarnessApproval` validation error

Add `approvers.disallowPipelineExecutor: true` — API requirement.

### Pipeline update overwrote unrelated stages

Always fetch current YAML, merge surgically, show diff. Never replace the full pipeline unless the user asked.

### FME environment name mismatch

FME environment names are case-sensitive and distinct from Harness CD environment identifiers. List `fme_environment` and confirm with the user.

### Treatment `<+input>` rejected in allocation

Treatment `<+input>` directly in allocation is rejected by the schema. Use pipeline variables: define `variables` under `pipeline:` spec (e.g., `onTreatment` default `on`), reference as `<+pipeline.variables.onTreatment>`.

### Jira or ServiceNow connector missing

For ticket integration building blocks, confirm connector exists via `harness_list` with `resource_type: "connector"` and pick ones whose type is Jira or ServiceNow. If missing, offer to create connector first via `/create-connector`.

### JiraApproval needs issue key from JiraCreate

When using `JiraApproval`, the issue key comes from `JiraCreate` step output. Reference as `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.issue.key>`.

### User asks to comment on Jira ticket

There's no dedicated Jira comment step. Offer a status transition via `JiraUpdate.transitionTo` or field update via `JiraUpdate.fields` instead.

### FME environment approval settings don't gate pipeline runs

FME environment-level approval settings are not enforced on pipeline runs (per Harness docs). To gate pipeline runs, add `HarnessApproval`, `JiraApproval`, or `ServiceNowApproval` steps in the pipeline.

### StageRollback on Custom stage

Do not use `StageRollback` with Custom stages — Custom stages have no rollback section. Use `MarkAsFailure` on errors, plus an explicit `FmeFlagKill` stage with `when: pipelineStatus: Failure`.

### Misnamed step fields

Step YAML `type:` strings must match the exact identifiers from [references/step-catalog.md](references/step-catalog.md). Common naming traps: `FmeFlagSetIndividualTargets` (not `FmeFlagSetTargets`), `FmeFlagAddRemoveIndividualTargets` (not `FmeFlagAddRemoveTargets`), `FmeSegmentAddRemoveTargets` (not `FmeSegmentAddRemoveKeys`). Do not "correct" these to UI-only or shorthand names.

### `trafficAllocation` is not proof of full rollout

`trafficAllocation` (0–100) is experiment participation, NOT which treatment wins. A flag at 50% test treatment can have `trafficAllocation: 100` (all traffic participates in the experiment). To verify full rollout, check `defaultRule` bucket `size` values sum to 100 with the winning treatment at 100%, and `rules` is empty.

## References

- [scenarios.md](references/scenarios.md) — R1–R4 rollout scenarios, L1–L4 lifecycle scenarios
- [building-blocks.md](references/building-blocks.md) — reusable gates, rollback, ticket integration, metric checks
- [blueprints.md](references/blueprints.md) — full scenario YAML patterns
- [references/step-catalog.md](references/step-catalog.md) — FME step types and field shapes
- [scope-establishment.md](../../references/scope-establishment.md) — account, org, and project scope rules
- [templates/operation-summary.md](../../templates/operation-summary.md) — structured completion summary contract
- `/manage-feature-flags` — direct MCP flag operations (kill, restore, allocation)
- `/create-trigger` — automate pipelines with triggers
- `/create-pipeline` — CI/CD stages, `HarnessApproval` requirements
- `/run-pipeline` — execute after pipeline exists
