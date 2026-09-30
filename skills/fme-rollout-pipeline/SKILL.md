---
name: fme-rollout-pipeline
description: >-
  Design and wire Harness FME pipeline stages and native FmeFlag* steps for
  feature-flag rollout patterns — progressive percentage, environment promotion,
  approval gates, and downstream gating. Composes FeatureFlag, Approval, and
  Custom stages rather than a single canned template. Use when asked to build a
  flag rollout pipeline, promote a flag across environments, add approval before
  prod, or gate prod until staging is at 100%. Do not use for direct flag CRUD
  (manage-feature-flags), code cleanup (cleanup-feature-flags), or generic CI/CD
  without FME steps (create-pipeline). Trigger phrases: FME pipeline, flag
  rollout pipeline, progressive rollout, environment promotion, approval before
  prod, feature flag stage, canary rollout, FME rollout.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# FME Rollout Pipeline

Help users **pick and wire** Harness FME pipeline steps for rollout use cases. Compose `FeatureFlag` stages, native `FmeFlag*` steps, `Approval` gates, and optional `Custom` / `Wait` stages. Do **not** ship one fixed pipeline shape.

Direct flag kill/restore/create via MCP is `/manage-feature-flags`. Post-launch code removal is `/cleanup-feature-flags`. General CI/CD structure is `/create-pipeline`.

## Instructions

Load references on demand:

- [rollout-patterns.md](references/rollout-patterns.md) — pattern catalog and plan checklist
- [fme-pipeline-steps.md](references/fme-pipeline-steps.md) — step types and evaluation order
- [pipeline-examples.md](references/pipeline-examples.md) — composable YAML snippets

**Allowed MCP tools only:** `harness_list`, `harness_get`, `harness_create`, `harness_update`.

**Allowed resource types only:** `pipeline`, `fme_environment`, `fme_feature_flag`, `fme_feature_flag_definition`, and `project` (pre-create existence check only — do not create projects).

**Prefer `org_id` + `project_id`.** Do not require deprecated `workspace_id`.

**Stop before mutating.** Do not `harness_create` / `harness_update` a pipeline until the user confirms the rollout plan.

**No automatic metric rollback.** Harness does not auto-rollback a flag on metric regression. Use `Approval`, `Wait`, `Custom` verification, or `FmeMetricCheck` (fails the **step**). Rollback is an explicit `FmeFlagKill` stage or failure path.

### Phase 1: Establish scope

Reuse [scope-establishment.md](../../references/scope-establishment.md). Ask for `org_id` and `project_id` if missing.

Restate: `Working in org=..., project=...`

### Phase 2: Choose mode

| Mode | User signal | Outcome |
|------|-------------|---------|
| **Design** (default if ambiguous) | "How should we roll out…?", "What steps do we need?" | Pattern + stage plan only; no YAML write |
| **New pipeline** | "Create a rollout pipeline for…" | Plan + YAML draft on first turn; **`harness_create` only after explicit confirm** |
| **Update existing** | "Add FME stages to pipeline X" | Fetch pipeline, merge stages, show diff; **`harness_update` only after explicit confirm** |

### Phase 3: Gather rollout intent

Collect (ask only for missing items):

1. **Flag name** (`feature_flag_name`, case-sensitive)
2. **Test treatment** and **control treatment** (or boolean on/off)
3. **Target environments** and whether any are **held** (not released yet)
4. **Pattern** — progressive %, env promotion, staging gate, approval, kill-switch rollback (see [rollout-patterns.md](references/rollout-patterns.md))
5. **Existing pipeline** URL/identifier (update mode)
6. **Approvers** for `HarnessApproval` (user groups, minimum count)
7. **Soak / gate between % increases** — `Wait`, `Approval`, `FmeMetricCheck`, or Custom tests (do not invent auto-rollback)

Do not guess environment names, treatments, or approver groups.

### Phase 4: Discover FME context

**MCP v2 identifier nesting** — required; bare top-level FME field names are stripped by the tool schema:

| Call | Where identifiers go |
|------|----------------------|
| `harness_list` with required list filters | `filters: { feature_flag_name: "..." }` |
| `harness_get` for `fme_feature_flag` / `fme_feature_flag_definition` | `params: { feature_flag_name: "...", environment_id: "..." }` (`environment_id` when per-env) |
| `harness_get` / `harness_update` for `pipeline` | top-level `resource_id` |
| `harness_list` project verify (pre-create only) | top-level `resource_type: "project"`, `org_id` |

If MCP is unavailable, skip discovery, say so, and ask the user for environment names and treatments — do not guess.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_environment"
  org_id: "<org>"
  project_id: "<project>"
```

Build a promotion-order proposal: non-production first, production last. Use `isProduction` when present. **Confirm order with the user.**

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_feature_flag"
  org_id: "<org>"
  project_id: "<project>"
  params: { feature_flag_name: "<flag_name>" }
```

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag_definition"
  org_id: "<org>"
  project_id: "<project>"
  filters: { feature_flag_name: "<flag_name>" }
```

Note per environment: `isKilled`, `defaultTreatment`, `defaultRule` (treatment % split), `trafficAllocation` (experiment participation only), `rules`, treatment targeting lists. Use this to avoid contradicting live state.

A killed flag cannot take traffic — plan `FmeFlagRestore` before allocation.

### Phase 5: Select pattern and wire stages

Using [rollout-patterns.md](references/rollout-patterns.md) and [fme-pipeline-steps.md](references/fme-pipeline-steps.md):

1. Map intent → pattern (mix patterns; do not force one canned pipeline)
2. List **stages in execution order** with step types per stage
3. Insert `Approval` where the user wants human gates
4. Insert `Wait` (Custom stage), `FmeMetricCheck`, or Custom tests between percentage or env promotions when soak or checks are needed
5. Define **hold** environments (omit stage or `FmeFlagKill` only)
6. Define **rollback** (`FmeFlagKill` stage)

**Stage types:**

| Stage `type` | Default use |
|--------------|-------------|
| `FeatureFlag` | Dedicated FME `FmeFlag*` steps (schema allows the same steps here as in Custom) |
| `Approval` | Human gate between percentages or environments |
| `Custom` | Mix FME steps with Wait, tests, or other non-FME work in one stage |
| `Pipeline` | Chain an existing CI/CD pipeline |

Do **not** use classic `FlagConfiguration` steps (legacy Feature Flags). Prefer native `FmeFlag*`.

**Step selection:**

| Goal | Steps |
|------|-------|
| Turn flag on in env | `FmeFlagRestore` |
| Set percentage split | `FmeFlagDefaultAllocation` (amounts sum to 100) |
| Cap exposure | `FmeFlagLimitExposure` |
| Emergency off | `FmeFlagKill` |
| Beta cohort | `FmeFlagAddRemoveIndividualTargets` or `FmeFlagSetTargetingRules` |
| Sync targeting across envs | `FmeFlagPatchDefinition` or replay allocation/rules steps |
| Attach flag to a flagset | `FmeFlagsetCreate` (if needed) + `FmeFlagAddRemoveFlagsets` |
| Multiple definition fields in one env | `FmeFlagDefinitionInstructions` (prefer single-purpose steps when one field changes) |
| Full launch | `FmeFlagRestore` + 100% allocation on test treatment |
| Metric gate (no auto-kill) | `FmeMetricCheck` — fails the step when JEXL `failureCriteria` is true |

Pair `FmeFlagRestore` with allocation when enabling traffic. Restore alone does not change percentages.

Recommend starting small (for example 5 → 25 → 50 → 100) unless the user specified otherwise.

For `HarnessApproval`, always set `approvers.disallowPipelineExecutor: true` (API requirement — see `/create-pipeline`).

### Phase 6: Present plan and wait

Before any pipeline write, show:

1. Pattern name and rationale
2. Environment promotion order
3. Stage diagram (ordered list: stage type, env, steps)
4. Per-env: held vs released on pipeline run
5. Approval / Wait / metric gates
6. Rollback path (`FmeFlagKill`)
7. Current FME state vs planned end state (from definitions)
8. New vs update, and MCP action if any

**Do not proceed until the user explicitly confirms.**

### Phase 7: Generate YAML

Compose from [pipeline-examples.md](references/pipeline-examples.md). Rules:

- Dedicated FME stages: `type: FeatureFlag`. Mixed FME + Wait/tests: `type: Custom`
- Every `FeatureFlag` and `Custom` stage that mutates flags needs `failureStrategies`
- Stage names: `^[a-zA-Z_0-9-.][-0-9a-zA-Z_\s.]{0,127}$` (no commas)
- Step identifiers: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- `environment` in step spec = FME environment **name or ID** (case-sensitive); confirm from `fme_environment` list
- Allocation amounts are integers 0–100 summing to 100. Quote treatment names that YAML treats as booleans (`"on"`, `"off"`, `"yes"`, `"no"`)
- Stage `when.pipelineStatus` is `Success`, `Failure`, or `All` — not `Failed`
- Pipeline YAML must include the `pipeline:` root key

If **update mode**, fetch current pipeline YAML before merging:

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

### Phase 9: Handoff

Summarize following `templates/operation-summary.md`:

- Operation, scope, pipeline identifier, and what each stage does
- What was confirmed (environments, treatments, current definition state)
- How to run (`/run-pipeline`)
- How to rollback (`FmeFlagKill` stage)
- Follow-up: further % increases may need another run or additional stages
- After full launch everywhere: `/cleanup-feature-flags` for code removal

## What NOT to do

- Ship one canned pipeline for every request — compose from patterns
- Call MCP tools other than `harness_list` / `harness_get` / `harness_create` / `harness_update`
- **Wire rollouts via direct flag MCP** — do not use `harness_update` on `fme_feature_flag_definition`, `harness_execute` (kill/restore/reallocate), or `harness_delete` for rollout wiring; use pipeline `FmeFlag*` stages (one-off ops → `/manage-feature-flags`)
- Assume automatic metric **auto-rollback** exists — `FmeMetricCheck` fails a step; it does not kill the flag
- Push pipeline YAML or call `harness_create` / `harness_update` before the user confirms the plan (including on "create pipeline" first turn)
- Use `Run` steps to call FME APIs when a native `FmeFlag*` step exists
- Use classic `FlagConfiguration` steps for FME
- Omit `disallowPipelineExecutor: true` on `HarnessApproval`
- Create/delete flags as the main rollout mechanism — use pipeline steps or `/manage-feature-flags`
- Require deprecated `workspace_id`
- Put a README inside this skill folder

## Examples

- "Build a pipeline to roll out `new-checkout-flow` 10% at a time in staging with approval before each increase" — Progressive % + approval gates.
- "Promote `dark_mode` from dev to staging to prod; prod needs approval" — Environment promotion pattern.
- "Gate production until staging is at 100%" — Staging gate + approval + prod stage.
- "What FME steps should we use for a canary rollout?" — Design mode only.
- "Add a FeatureFlag stage to pipeline `payments_deploy` to restore the flag in prod" — Update mode.
- "Kill the flag if the pipeline fails" — Rollback stage with `FmeFlagKill`.
- "Canary rollout with metric checks" — Design Approval + Wait/`FmeMetricCheck` + `FmeFlagKill`; explain no auto-rollback.
- "Create a dark mode flag" — Use `/manage-feature-flags`, not this skill.
- "Remove the flag from code" — Use `/cleanup-feature-flags`.

## Performance Notes

- One `fme_feature_flag_definition` **list** via `harness_list` with `filters: { feature_flag_name: "..." }` returns all envs — prefer over N gets during planning. Per-env detail: `harness_get` with `params: { feature_flag_name, environment_id }`.
- Design mode avoids pipeline API writes entirely.
- Keep SKILL.md focused; load step catalog and YAML examples from references.
- Large multi-env pipelines: propose incremental delivery (staging first, prod in a follow-up) when the user has not committed to full promotion.

## Troubleshooting

### Environments disagree on targeting

Do not generate prod steps that contradict staging without calling it out. Offer config promotion (`FmeFlagPatchDefinition`) or manual alignment first.

### Flag is killed in target environment

Plan must include `FmeFlagRestore` before allocation. Mention current `isKilled` state in the plan.

### User wants metric-based auto-rollback

Explain Harness does not auto-kill on metric regression. Offer `FmeMetricCheck` or Custom checks that **fail the step**, plus an explicit `FmeFlagKill` rollback stage.

### `HarnessApproval` validation error

Add `approvers.disallowPipelineExecutor: true`.

### Pipeline update overwrote unrelated stages

Always fetch current YAML, merge surgically, show diff. Never replace the full pipeline unless the user asked.

### FME environment name mismatch

FME environment names are case-sensitive and distinct from Harness CD environment identifiers. List `fme_environment` and confirm with the user.

### YAML rejected for FeatureFlag vs Custom

`FmeFlag*` steps are valid on both `FeatureFlag` and `Custom` stages. If the UI only offers FME in Custom, use `Custom`. Do not fall back to `FlagConfiguration`.

### Step type naming traps

Step YAML `type:` strings are strict and can differ from colloquial names or UI display labels. Always use the exact step `type:` strings from [fme-pipeline-steps.md](references/fme-pipeline-steps.md) (e.g. `FmeFlagSetIndividualTargets` not `FmeFlagSetTargets`, `FmeFlagAddRemoveIndividualTargets` not `FmeFlagAddRemoveTargets`, `FmeSegmentAddRemoveTargets` not `FmeSegmentAddRemoveKeys`). Do not "correct" these to UI-only or shorthand names.

## References

- [rollout-patterns.md](references/rollout-patterns.md) — pattern catalog
- [fme-pipeline-steps.md](references/fme-pipeline-steps.md) — `FmeFlag*` step reference
- [pipeline-examples.md](references/pipeline-examples.md) — YAML snippets
- [scope-establishment.md](../../references/scope-establishment.md) — account, org, and project scope rules
- [operation-summary.md](../../templates/operation-summary.md) — structured completion summary contract
- `/manage-feature-flags` — direct MCP flag operations
- `/cleanup-feature-flags` — post-launch code removal
- `/create-pipeline` — CI/CD stages, `HarnessApproval` requirements
- `/run-pipeline` — execute after pipeline exists
