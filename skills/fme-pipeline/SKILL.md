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
  version: 1.2.0
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
| Increase traffic in one environment | **R1** Progressive ramp | Initial allocation while killed → manual readback/approval → restore → soak/later allocations (5→25→50→100) |
| Promote across dev/qa/staging/prod | **R2** Multi-environment promotion | ONE STAGE PER ENVIRONMENT, initial allocation → readback/approval → restore → soak/ramps |
| Beta users first, then everyone | **R3** Beta cohort | 0% default + beta targeting → full-audience readback/approval → restore → soak/ramps |
| Copy staging config to prod | **R4** Config promotion | `FmeFlagDefinitionInstructions` or `FmeFlagPatchDefinition` |
| Create flag with initial targeting | **L1** Flag bootstrap | `FmeFlagCreate` → treatments → kill/restore/targets → flagsets |
| Prepare a fully-launched flag for retirement | **L2** Flag retirement (preparatory only) | Verify 100% at authoring time → update rolloutStatus → remove flagsets → hand off to `/manage-flag-lifecycle` for the archive step itself, re-checked at execution time |
| Import keys from external system | **L3** Segment sync | `ShellScript` fetch → `FmeSegmentAddRemoveTargets` |
| Add test keys, run tests, clean up | **L4** Test targeting | Add keys → `ShellScript` tests → remove keys |

### Phase 4: Gather inputs

Collect only what is missing. Do not guess environment names, treatments, or approver groups. For all scenarios: flag name, baseline and variant treatments, target environments, existing pipeline (update mode). For R2: per-env ramp schedule and gates. Ask: reusable pipeline (flag name as `<+input>`) or one-off (literal name)? Gate policy: never add a gate the user didn't agree to. Killed-flag resume requires the manual readback/approval checkpoint below; if declined, stop the automated resume and hand off rather than omitting the safeguard. Ask which building blocks: gates (`HarnessApproval`, `Wait`, `FmeMetricCheck`), rollback (`FmeFlagKill` stage on failure), ticket integration (Jira/ServiceNow), or none. For approvals: user groups, minimum count.

**L1 is the one scenario where the flag does not exist yet.** Do not demand an existing flag, its definitions, or its targeting state as a prerequisite. Instead gather: flag name (and confirm it is NOT already taken — see Phase 5), traffic type (must exist in the project/account scope), treatments, default/baseline treatment, per-env kill/restore plan, flagset name if attaching.

### Phase 5: Discover context

**List environments** to build promotion-order proposal (non-prod first, prod last via `isProduction`). **Confirm order.**

**For R1–R4 and L2–L4 (flag must already exist):** **Get flag** + **List definitions** to note per environment: `isKilled`, `defaultTreatment`, `defaultRule`, `trafficAllocation`, `rules`, targeting.

**For L1 (flag bootstrap):** do the opposite check — **Get flag** to confirm the name is NOT already in use (stop and ask if it is), and confirm the requested traffic type exists at the relevant scope. Do not call **List definitions** expecting prior state; there is none yet.

**Killed-flag resume (R1/R2/R3 and any previously-targeted flag):** write the approved initial allocation/rules/targets while killed; then require a **manual readback and `HarnessApproval` checkpoint** before `FmeFlagRestore`, followed by soak/later increases. The approver must inspect the complete definition through `/explain-flag` or Harness UI: still killed, approved `defaultRule`/`trafficAllocation`, all rules and treatment-level key/segment memberships, served default/configuration, and current experiment impacts. Reject mismatches or stale evidence. R3 must verify that no existing rule/target exposes non-beta users; 0% default plus appended beta keys does not prove isolation. If initially active, plan the immediate live impact explicitly and omit the unnecessary restore/resume checkpoint; never silently kill it.

**No native readback step exists in this catalog.** Use the agreed manual checkpoint, not a fabricated verifier or API-success claim. If no approver/readback is available, stop before automated restore and hand off. This checks stored configuration, not SDK propagation; `FmeMetricCheck` after a soak is a separate measurement. Changing `defaultTreatment` or its configuration can affect killed traffic immediately—disclose that impact before approval.

For L2: **List rollout statuses**. For approvals: **List user groups**. For tickets: **List connectors** (type Jira or ServiceNow; if missing, hand off to `/create-connector`). If unavailable, skip and ask user for details.

### Phase 6: Present plan and wait

Before any write, show: scenario(s) and rationale, environment promotion order, stage table (stage | environment | steps | gates | notes), pipeline variables (flag name as `<+input>`, treatments as variables — treatment `<+input>` directly in allocation is rejected), prerequisites (project/flag/approvers/connectors exist — for L1, project/traffic-type instead of flag), rollback path (`FmeFlagKill` when `pipelineStatus: Failure`), current vs planned state. Run [experiment check](../../references/fme/write-safety.md#experiment-check) with **List experiments** if targeting steps can invalidate experiments or for the L2 retirement-preparation scenario; link and confirm acknowledgement. For L2, also state explicitly that the generated pipeline stops short of archiving and that `/manage-flag-lifecycle` must re-verify readiness (staleness, dependents, active/paused experiments) at execution time before archiving. **Do not proceed until user confirms.**

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
- **L2**: "Prepare `old-checkout-flow` for retirement now that it's at 100% `off` everywhere" — generates status-update and flagset-detach stages only; archiving itself happens in `/manage-flag-lifecycle` after a fresh readiness check

## Performance Notes

- **One call to List definitions** returns all environments — prefer over N gets.
- **Design mode avoids writes** — fastest for brainstorming.
- **Large multi-env pipelines**: propose incremental delivery (staging first, prod follow-up).

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| **Environments disagree on targeting** | Don't generate prod steps contradicting staging. Offer config promotion or manual alignment. |
| **Flag killed in target** | Write approved initial targeting → manual full-definition readback/approval → restore → soak/later increases. Stop if verification or approval is unavailable; disclose any immediate change to the killed flag's served default/configuration. |
| **L2 pipeline expected to archive automatically** | By design it does not. 100% rollout at authoring time is not archive readiness — staleness, dependents, and active/paused experiments must be re-checked at execution time. The generated pipeline only updates rollout status and detaches flagsets; hand off to `/manage-flag-lifecycle` for the archive step with fresh evidence. |
| **L1 discovery returns "flag not found"** | Expected for bootstrap — this confirms the name is free to use, it is not a blocking error. |
| **User wants metric auto-rollback** | Explain no auto-kill on metric regression. Offer `FmeMetricCheck` that fails step + explicit `FmeFlagKill` rollback stage. |
| **`HarnessApproval` validation error** | Schema requires `includePipelineExecutionHistory` and `approvers` object with `disallowPipelineExecutor`, `minimumCount`, and either `userGroups` or `serviceAccounts`. |
| **Pipeline update overwrote stages** | Always **Get pipeline**, merge surgically, show diff. |
| **Environment name mismatch** | Names are case-sensitive. **List environments** and confirm. |
| **Treatment `<+input>` rejected** | Use pipeline variables: define under `pipeline:` spec, reference as `<+pipeline.variables.onTreatment>`. |
| **Connector missing** | **List connectors** (type Jira/ServiceNow). If missing, offer `/create-connector`. |
| **FME environment approval settings** | FME environment-level approval settings do not gate pipeline step execution — use a `HarnessApproval` step in the pipeline for gating. |
