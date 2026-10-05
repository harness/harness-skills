---
name: fme-pipeline
description: >-
  Generate Harness pipelines with FeatureFlag or Custom stages for flag rollout
  scenarios: progressive ramp, multi-env promotion, beta cohorts, config promotion,
  bootstrap, retirement, segment sync, test targeting. Composes FmeFlag* steps with
  optional HarnessApproval/Wait/Jira/ServiceNow/metric gates. Use when asked to build
  a flag rollout pipeline, promote flags across environments, or automate flag
  lifecycle. Do not use for direct flag operations (update-flag-targeting) or general
  CI/CD (create-pipeline). Related: create-trigger (automate), run-pipeline (execute).
  Trigger phrases: FME pipeline, feature flag pipeline, flag rollout pipeline,
  progressive rollout, multi-environment promotion, flag bootstrap.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# FME Pipeline

Compose Harness pipelines with FmeFlag* / FmeSegment* steps for flag rollout scenarios. Generates tailored pipelines — progressive ramp, multi-environment promotion, beta cohorts, config promotion, bootstrap, retirement, segment sync, and test targeting — rather than a single fixed template.

**Related:** Direct flag operations → `/update-flag-targeting`. Experiments → `/manage-experiments`, `/review-experiment-results`. Flag creation → `/create-feature-flag`. Lifecycle → `/manage-flag-lifecycle`. Segments → `/manage-segments`. State → `/explain-flag`. Discovery → `/discover-feature-flags`. Code removal → `/cleanup-feature-flags`. Running → `/run-pipeline`. Triggers → `/create-trigger`.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| **List environments** | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| **Get flag** | `harness_get` · `fme_feature_flag` · `params: { feature_flag_name }` | `harness get feature_flag <name> --json` |
| **List definitions** | `harness_list` · `fme_feature_flag_definition` · `params: { feature_flag_name }` · `filters: { offset, limit }` · `compact: false` | `harness list feature_flag:definition <name> --json` |
| **List rollout statuses** | `harness_list` · `fme_rollout_status` · `compact: false` | `harness list rollout_status --json` |
| **List experiments** | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, status: ["ACTIVE", "PAUSED"] }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <flag> --status ACTIVE --json`, then again with `--status PAUSED` |
| **List user groups** | `harness_list` · `user_group` | `harness list user_group --json` |
| **List connectors** | `harness_list` · `connector` | `harness list connector --json` |
| **Get project** | `harness_list` · `project` · `org_id` | `harness list project --org <org> --json` |
| **Get pipeline** | `harness_get` · `pipeline` · `params: { pipeline_id }` · `org_id` · `project_id` | `harness get pipeline <id> --org <org> --project <proj> --json` |
| **Create pipeline** | `harness_create` · `pipeline` · `org_id` · `project_id` · `body: { yamlPipeline }` | `harness create pipeline -f pipeline.yaml --org <org> --project <proj>` |
| **Update pipeline** | `harness_update` · `pipeline` · `params: { pipeline_id }` · `org_id` · `project_id` · `body: { yamlPipeline }` | `harness update pipeline <id> -f pipeline.yaml --org <org> --project <proj>` |

## Instructions

**Confirm before write.** Do not create or update until the user explicitly confirms the plan.

**No automatic metric rollback.** `FmeMetricCheck` fails the step when its JEXL condition is true — it does not kill the flag. Rollback requires an explicit `FmeFlagKill` stage.

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Restate: `Working in org=..., project=...`

### Phase 2: Choose mode

| Mode | User signal | Outcome |
|------|-------------|---------|
| **Design** (default) | "How should we roll out…?" | Pattern + stage plan; no YAML write |
| **New pipeline** | "Create a rollout pipeline for…" | Plan + YAML draft; create after confirm |
| **Update existing** | "Add FME stages to pipeline X" | Fetch, merge, show diff; update after confirm |

### Phase 3: Pick scenario(s)

Map user intent to [scenarios.md](references/scenarios.md):

| User intent | Scenario | Primary steps |
|-------------|----------|---------------|
| Increase traffic in one environment | **R1** Progressive ramp | `FmeFlagRestore` → `FmeFlagDefaultAllocation` (5→25→50→100) |
| Promote across dev/qa/staging/prod | **R2** Multi-environment promotion | ONE STAGE PER ENVIRONMENT, restore + allocation + gates |
| Beta users first, then everyone | **R3** Beta cohort | `FmeFlagAddRemoveIndividualTargets` or `FmeFlagSetTargetingRules` → allocation |
| Copy staging config to prod | **R4** Config promotion | `FmeFlagDefinitionInstructions` or `FmeFlagPatchDefinition` |
| Create flag with initial targeting | **L1** Flag bootstrap | `FmeFlagCreate` → treatments → kill/restore/targets → flagsets |
| Archive fully-launched flag | **L2** Flag retirement | Verify 100% → update rolloutStatus → remove flagsets → archive |
| Import keys from external system | **L3** Segment sync | `ShellScript` fetch → `FmeSegmentAddRemoveTargets` |
| Add test keys, run tests, clean up | **L4** Test targeting | Add keys → `ShellScript` tests → remove keys |

### Phase 4: Gather inputs

Collect only what is missing. Do not guess environment names, treatments, or approver groups. For all scenarios: flag name, baseline and variant treatments, target environments, existing pipeline (update mode). For R2: per-env ramp schedule and gates. Ask: reusable pipeline (flag name as `<+input>`) or one-off (literal name)? Gate policy: never add a gate the user didn't agree to. Ask which building blocks: gates (`HarnessApproval`, `Wait`, `FmeMetricCheck`), rollback (`FmeFlagKill` stage on failure), ticket integration (Jira/ServiceNow), or none. For approvals: user groups, minimum count.

### Phase 5: Discover context

**List environments** to build promotion-order proposal (non-prod first, prod last via `isProduction`). **Confirm order.** **Get flag** + **List definitions** to note per environment: `isKilled`, `defaultTreatment`, `defaultRule`, `trafficAllocation`, `rules`, targeting. A killed flag serves `defaultTreatment` to everyone — plan `FmeFlagRestore` before allocation steps. For L2: **List rollout statuses**. For approvals: **List user groups**. For tickets: **List connectors** (type Jira or ServiceNow; if missing, hand off to `/create-connector`). If unavailable, skip and ask user for details.

### Phase 6: Present plan and wait

Before any write, show: scenario(s) and rationale, environment promotion order, stage table (stage | environment | steps | gates | notes), pipeline variables (flag name as `<+input>`, treatments as variables — treatment `<+input>` directly in allocation is rejected), prerequisites (project/flag/approvers/connectors exist), rollback path (`FmeFlagKill` when `pipelineStatus: Failure`), current vs planned state. Run [experiment check](../../references/fme/write-safety.md#experiment-check) with **List experiments** if targeting steps can invalidate experiments or for archive (L2) scenario; link and confirm acknowledgement. **Do not proceed until user confirms.**

### Phase 7: Generate YAML

Compose from [blueprints.md](references/blueprints.md) and [building-blocks.md](references/building-blocks.md). Get step fields from [step-catalog.md](references/step-catalog.md). YAML rules: FME stages use `type: Custom` (schema allows `type: FeatureFlag` for flag steps, but Custom is more flexible for mixing FME steps with Wait/approvals/scripts). Custom stages need `failureStrategies` (`MarkAsFailure`; no `StageRollback`). Stage names: `^[a-zA-Z_0-9-.][-0-9a-zA-Z_\s.]{0,127}$`. Step identifiers: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`. `environment` = FME environment name/ID (case-sensitive). Allocations: integers 0–100 summing to 100. **Quote boolean-like treatment names** (`"on"`, `"off"`). Stage `when.pipelineStatus`: `Success`, `Failure`, or `All`. **Pipeline YAML must include `pipeline:` root** and be passed as a **YAML string**. **Treatment `<+input>` rejected** — use pipeline variables. Step naming traps: `FmeFlagSetIndividualTargets` not `FmeFlagSetTargets`, `FmeFlagAddRemoveIndividualTargets` not `FmeFlagAddRemoveTargets`, `FmeSegmentAddRemoveTargets` not `FmeSegmentAddRemoveKeys`. If update mode, **Get pipeline** before merging; show diff. Show YAML before write.

### Phase 8: Create or update (after confirmation)

Follow [write-safety.md](../../references/fme/write-safety.md). Verify project (**Get project**), then **Create pipeline** or **Update pipeline** (YAML as string). On validation errors, read message, fix, retry. Do **not** run; point to `/run-pipeline`.

### Phase 9: Summary

Follow [operation-summary.md](../../templates/operation-summary.md): operation, scope, pipeline ID, what each stage does, what was confirmed, rollback path, how to run, follow-up.

## Not covered

Triggers (use `/create-trigger`), scheduled launches, CD/CI coupling (use `/create-pipeline`), governance/OPA, kill-switch runbooks, experiment launch/analysis (use `/manage-experiments`, `/review-experiment-results`, `/choose-metric`, `/create-metric`, `/instrument-metric`), guarded rollout (FME-18554 deferred), `FmeFlagSetImpressionTracking`/`FmeChangeProposalSubmit`, running pipelines (use `/run-pipeline`), direct flag changes (use `/update-flag-targeting`).

## Examples

- **R1**: "Build a pipeline to roll out `new-checkout-flow` 10% at a time in staging with approval before each increase"
- **R2**: "Promote `dark-mode` from dev → staging → prod, with prod needing approval and slower ramp"
- **R3**: "Enable `new-search` for beta users first, then ramp to 10% → 50% → 100% for everyone"
- **R4**: "Copy the staging targeting rules and allocation to prod"
- **L1**: "Create `dark-mode` flag with `on` and `off` treatments, keep it killed in prod, restore it in dev"
- **L2**: "Archive `old-checkout-flow` now that it's at 100% `off` everywhere"

## Performance Notes

- **One call to List definitions** returns all environments — prefer over N gets.
- **Design mode avoids writes** — fastest for brainstorming.
- **Large multi-env pipelines**: propose incremental delivery (staging first, prod follow-up).

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| **Environments disagree on targeting** | Don't generate prod steps contradicting staging. Offer config promotion or manual alignment. |
| **Flag killed in target** | Plan must include `FmeFlagRestore` before allocation. Mention `isKilled` state. |
| **User wants metric auto-rollback** | Explain no auto-kill on metric regression. Offer `FmeMetricCheck` that fails step + explicit `FmeFlagKill` rollback stage. |
| **`HarnessApproval` validation error** | Schema requires `includePipelineExecutionHistory` and `approvers` object with `disallowPipelineExecutor`, `minimumCount`, and either `userGroups` or `serviceAccounts`. |
| **Pipeline update overwrote stages** | Always **Get pipeline**, merge surgically, show diff. |
| **Environment name mismatch** | Names are case-sensitive. **List environments** and confirm. |
| **Treatment `<+input>` rejected** | Use pipeline variables: define under `pipeline:` spec, reference as `<+pipeline.variables.onTreatment>`. |
| **Connector missing** | **List connectors** (type Jira/ServiceNow). If missing, offer `/create-connector`. |
| **FME environment approval settings** | FME environment-level approval settings do not gate pipeline step execution — use a `HarnessApproval` step in the pipeline for gating. |
