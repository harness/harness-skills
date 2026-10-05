# FME Pipeline Scenarios

Common FME rollout use cases. Scenarios can be combined (e.g., R3 inside each environment of R2). Full patterns in [blueprints.md](blueprints.md), step details in [step-catalog.md](step-catalog.md).

## Quick Reference

| Scenario | Use when | Primary steps |
|----------|----------|---------------|
| **R1** Progressive ramp | Increase traffic in one environment | `FmeFlagRestore` → `FmeFlagDefaultAllocation` (5→25→50→100) |
| **R2** Multi-environment promotion | Ramp across dev/qa/staging/prod with different schedules per env | ONE STAGE PER ENVIRONMENT, each with restore + allocation + optional gates |
| **R3** Beta cohort first | Test users first, then ramp to everyone | `FmeFlagAddRemoveIndividualTargets` or `FmeFlagSetTargetingRules` → then default allocation |
| **R4** Config promotion | Copy validated staging config to prod | `FmeFlagDefinitionInstructions` or `FmeFlagPatchDefinition` after reading source env |
| **L1** Flag bootstrap | Create flag + treatments + initial targeting | `FmeFlagCreate` → `FmeFlagSetTreatments` per env → kill/restore/targets per env → flagsets |
| **L2** Flag retirement | Archive a fully-launched flag | Verify 100% → `FmeFlagUpdate` (rolloutStatus) → remove from flagsets → `FmeFlagArchive` |
| **L3** Segment sync from external system | Import user keys from external system to segment | `ShellScript` fetches keys → `FmeSegmentAddRemoveTargets` with expression |
| **L4** Test-user targeting for E2E tests | Add test keys, run tests, clean up on success or failure | `FmeFlagAddRemoveIndividualTargets` add → `ShellScript` run tests → remove keys with cleanup step |

## R1: Progressive Ramp Within One Environment

**Use when:** Ramping a flag within a single environment (e.g., staging 5% → 25% → 50% → 100%).

**Pattern:**
1. `FmeFlagRestore` (if flag is killed)
2. `FmeFlagDefaultAllocation` with first percentage (e.g., 5% on, 95% off)
3. Optional gate: `HarnessApproval`, `Wait`, or `FmeMetricCheck`
4. `FmeFlagDefaultAllocation` with next percentage (e.g., 25% on, 75% off)
5. Repeat until 100%

**Stage structure:** One `Custom` stage per percentage, OR one stage with sequential steps if no gates between percentages.

**Building blocks:** Gates between percentages, kill on failure, metric checks.

**Inputs to gather:** Flag name, environment, treatment names, ramp schedule (e.g., 5, 25, 50, 100), gate type between steps (approval, wait duration, metric check, or none).

## R2: Multi-Environment Promotion

**THE HEADLINE SCENARIO.** A reusable pipeline where the flag name is a pipeline input (`<+input>`) and the pipeline ramps the flag across multiple environments in order. Each environment can have its own: ramp schedule (non-prod: straight to 100%; prod: slower such as 1→5→25→50→100), gate before the environment (approval, wait, or none), gate between ramp steps within the environment (approval, wait, metric check, or none).

**Pattern:** ONE STAGE PER ENVIRONMENT (not a matrix), because schedules and gates differ per environment. Per environment: optional gate BEFORE the env (e.g., `HarnessApproval` before prod), `FmeFlagRestore`, `FmeFlagDefaultAllocation` steps per the env's ramp schedule, optional gates BETWEEN ramp steps (e.g., `Wait` 1h after 25%).

**Multiple prod regions:** can be sequential stages, or a `parallel:` stage group if simultaneous rollout is desired.

**Pipeline variables:** `flagName` as `<+input>` (so the same pipeline can roll out multiple flags). Treatment names as pipeline VARIABLES (e.g., `onTreatment` default `on`, `offTreatment` default `off`), referenced as `<+pipeline.variables.onTreatment>` (the schema rejects `<+input>` directly in treatment fields). Environment names can be literal per stage or variables.

**Ticket integration (optional):** `JiraCreate` or `ServiceNowCreate` at the start, `JiraUpdate` / `ServiceNowUpdate` at milestones, close the ticket at the end.

**Gather per-env plan table:**

| Environment | Ramp schedule | Gate before env | Gate between steps |
|-------------|---------------|-----------------|-------------------|
| dev | 100 | none | none |
| qa | 100 | none | none |
| staging | 100 | none | Wait 1h |
| prod-us | 1, 5, 25, 50, 100 | Harness approval | Wait 2h |
| prod-eu | 1, 5, 25, 50, 100 | Harness approval | Wait 2h |

**Inputs to gather:** Flag name (or `<+input>` for reusable pipeline), ordered list of environments, per environment: ramp schedule, gate before env, gate between steps, ticket system (Jira, ServiceNow, or none), approvers (user groups for approval gates).

## R3: Beta Cohort First, Then Everyone

**Use when:** Targeting a subset of users (beta cohort) before ramping the default allocation.

**Pattern:**
1. `FmeFlagRestore`
2. `FmeFlagAddRemoveIndividualTargets` to add beta user keys, OR `FmeFlagSetTargetingRules` to set a segment rule
3. Optional soak/gate (`Wait`, `FmeMetricCheck`, `HarnessApproval`)
4. `FmeFlagDefaultAllocation` to ramp the default allocation (5 → 25 → 50 → 100)
5. At GA (100%): `FmeFlagSetIndividualTargets` with empty list to clear individual targets, OR `FmeFlagSetTargetingRules` with empty list to clear rules

**Evaluation order:** Individual targets and rules take precedence over the default allocation, so beta users see the test treatment even when the default allocation is 0%.

**Inputs to gather:** Flag name, environment, treatments, beta cohort (individual user keys, OR segment name, OR targeting rule condition), ramp schedule after beta (if any), when to clear beta targeting (immediately, or leave it during ramp, or clear at GA).

## R4: Config Promotion Between Environments

**Use when:** Staging targeting is validated and prod should match it exactly.

**Pattern:**
1. Read staging definition: **List definitions** for the flag and pick staging env
2. Translate staging config to prod using ONE of:
   - `FmeFlagDefinitionInstructions` with multiple instruction types (restore, allocation, rules, etc.) in one atomic step
   - `FmeFlagPatchDefinition` with JSON Patch operations
   - Replay individual steps: `FmeFlagDefaultAllocation`, `FmeFlagSetTargetingRules`, etc. with prod `environment`
3. Optional verification step: `FmeMetricCheck` or `Wait` after applying

**When to use each approach:**
- **`FmeFlagDefinitionInstructions`**: Multiple fields changing together (restore + allocation + rules), or env promotion where several fields must sync
- **`FmeFlagPatchDefinition`**: Surgical edits, complex nested changes (operations is a **string**, not YAML list)
- **Replay steps**: Simple allocation or rules change, when the source config is a single field

**Inputs to gather:** Flag name, source environment (e.g., staging), target environment (e.g., prod), which fields to copy: allocation, rules, individual targets, dynamic config, all of the above.

## L1: Flag Bootstrap

**Use when:** Creating a new flag from scratch with treatments, initial targeting, and environment-specific defaults.

**Pattern:**
1. `FmeFlagCreate` with flag name and treatments (creates definitions with trafficAllocation 100% and defaultRule 100% on `defaultTreatment`)
2. Per environment: `FmeFlagSetTreatments` if treatments differ per env (requires `environment` + `baselineTreatment`, items `{treatment,description}`)
3. Per environment: `FmeFlagKill` in prod to serve `defaultTreatment` to everyone, `FmeFlagRestore` in dev to resume targeting
4. Optional: `FmeFlagAddRemoveIndividualTargets` to add QA test users in non-prod environments
5. Optional: `FmeFlagsetCreate` + `FmeFlagAddRemoveFlagsets` to attach the flag to a release flagset

**Inputs to gather:** Flag name, treatment names (at least 2), default treatment, baseline treatment (for metrics), per environment: kill or restore, default allocation, individual targets, flagset name (if attaching to a flagset).

## L2: Flag Retirement

**Use when:** A flag is at 100% in all critical environments and ready to be archived.

**Pattern:**
1. **Verify 100%** before generating the pipeline: **List definitions** for the flag. Per environment: confirm `isKilled` is false, `defaultRule` allocation is 100% on the winning treatment, `trafficAllocation` is 100, `rules` is empty, individual targets empty. If any environment is not at 100%, STOP and tell the user which environments need to reach 100% first.
2. `FmeFlagUpdate` with `rolloutStatus` to mark the flag as "Completed" or "Deprecated" (discover valid values via **List rollout statuses**)
3. `FmeFlagAddRemoveFlagsets` with `removeFlagsets` to detach from any flagsets
4. `FmeFlagArchive` to archive the flag (archiving makes SDKs return `control` in every environment; remove the flag from code first with `/cleanup-feature-flags`)

**DO NOT generate this pipeline if any environment is not at 100%.** The user must first roll out to 100% everywhere (use R1 or R2), then run the retirement pipeline.

**Inputs to gather:** Flag name, confirm all critical environments are at 100% (verify first), rollout status value, flagsets to remove from (if any).

## L3: Segment Sync from External System

**Use when:** Segment membership comes from an external system (database, API, etc.) and must be synced to an FME segment.

**Pattern:**
1. `ShellScript` step that: fetches the user keys from the external system, exports an output variable with the keys as a list (e.g., `export keys='["user1","user2","user3"]'`)
2. `FmeSegmentAddRemoveTargets` step with: `segmentName` (segment name, user provides), `environment` (FME environment name), `addKeys` (expression referencing the ShellScript output: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.output.outputVariables.keys>`), OR `removeKeys` (expression for keys to remove)

**IMPORTANT:** The expression must resolve to a list at runtime. The schema expects a list, not a string. This should be verified on the first run. If the external system returns a different format (newline-separated, CSV, etc.), the ShellScript must transform it to a JSON array.

**Inputs to gather:** Segment name (user provides), environment name, external system details (how to fetch the keys: database query, API endpoint, etc.), script to fetch keys (ask user, or draft a script and confirm), add or remove keys (or both).

## L4: Test-User Targeting for End-to-End Tests

**Use when:** E2E tests need specific user keys to be targeted, then cleaned up after the test (success or failure).

**Pattern:**
1. `FmeFlagAddRemoveIndividualTargets` with `addKeys` to add test user keys to the test treatment
2. `ShellScript` step that runs or triggers the E2E tests
3. `FmeFlagAddRemoveIndividualTargets` with `removeKeys` to remove the test user keys. The cleanup step must run even on failure: use step-level `when: stageStatus: All` OR a failure strategy that ensures the cleanup step runs.

**Inputs to gather:** Flag name, environment, treatment, test user keys to add, how to run the tests (command, script, or existing pipeline to trigger), cleanup strategy: step-level `when` or failure strategy.

## Combining Scenarios

**Example: R3 inside each environment of R2**
- Dev: beta cohort → 100% (no approval)
- QA: beta cohort → 100% (no approval)
- Staging: beta cohort → 100% (approval before staging)
- Prod: beta cohort → 1% → 5% → 25% → 50% → 100% (approval before prod, wait 2h between steps)

**Example: L3 + R1**
- Sync segment from external system
- Progressive ramp targeting that segment
- Then ramp default allocation to everyone

**Example: L1 + R2 + L2**
- L1: Bootstrap the flag
- R2: Multi-environment promotion to 100%
- L2: Retire and archive the flag

## Not Covered (Out of Scope)

These scenarios are explicitly out of scope for this skill. Refer users to the listed alternatives:

- **Triggers (scheduled, webhook, cron)**: This skill only creates pipelines. After the pipeline exists, use `/create-trigger` to automate it.
- **Scheduled launches**: Not covered. Manual pipeline execution only.
- **Coupling to deploy or CI stages**: No CD or CI stages in this skill. Use `/create-pipeline` to add CI/CD stages, then chain with FME stages.
- **Governance and OPA `Policy` steps**: Not covered as standalone scenarios.
- **Kill-switch runbook pipelines**: Not covered. Kill-switch rollback is covered within scenarios (rollback stage), but dedicated runbook pipelines are out of scope.
- **Experiment launch and analysis**: Not covered. Use `/manage-experiments`, `/review-experiment-results`, `/choose-metric`, `/create-metric`, `/instrument-metric`.
- **`FmeFlagSetImpressionTracking` and `FmeChangeProposalSubmit` steps**: Never generate these steps. They are out of scope.
- **Running pipelines**: This skill only creates/updates pipelines. After the pipeline exists, point users to `/run-pipeline`.
- **Direct flag changes**: This skill only creates pipelines with FME steps. For direct flag kill/restore/allocation, point users to `/update-flag-targeting`.
