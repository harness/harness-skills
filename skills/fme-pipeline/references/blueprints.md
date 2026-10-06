# FME Pipeline Blueprints

This file contains complete pipeline YAML blueprints for each scenario from `scenarios.md`. Each blueprint is production-ready with realistic placeholders that can be customized.

## Table of Contents

- [R1: Progressive Ramp Within One Environment](#r1-progressive-ramp-within-one-environment)
- [R2: Multi-Environment Promotion (THE HEADLINE)](#r2-multi-environment-promotion-the-headline)
- [R3: Beta Cohort First, Then Everyone](#r3-beta-cohort-first-then-everyone)
- [R4: Config Promotion Between Environments](#r4-config-promotion-between-environments)
- [L1: Flag Bootstrap](#l1-flag-bootstrap)
- [L2: Flag Retirement](#l2-flag-retirement)
- [L3: Segment Sync from External System](#l3-segment-sync-from-external-system)
- [L4: Test-User Targeting for End-to-End Tests](#l4-test-user-targeting-for-end-to-end-tests)

---

## R1: Progressive Ramp Within One Environment

**Use case:** Roll out a flag progressively within a single environment with approval gates between each percentage increase.

**Customize:**
- Flag name and environment in all steps
- Treatment names in allocation steps
- Approval user groups

**Stages:**

- `ramp_25_percent`: `FmeFlagRestore`, `FmeFlagDefaultAllocation`, `HarnessApproval`
- `ramp_50_percent`: `FmeFlagDefaultAllocation`, `HarnessApproval`
- `ramp_100_percent`: `FmeFlagDefaultAllocation`
- `rollback_on_failure` (when: Failure): `FmeFlagKill`

**Full pipeline:** [r1-progressive-ramp.yaml](blueprints/r1-progressive-ramp.yaml)

---

## R2: Multi-Environment Promotion (THE HEADLINE)

**Use case:** Reusable pipeline for promoting any flag across dev → qa → staging → prod (us + eu regions) with environment-specific ramp schedules, approval gates, and Jira ticket tracking. Solo teams can set `disallowPipelineExecutor: false` for approvals.

**Customize:**
- Flag name as pipeline input variable
- Treatment names as pipeline variables
- Jira connector and project details
- Approver user groups
- Environments and ramp schedules per environment
- Production regions (parallel or sequential)

**Stages:**

- `create_jira_ticket`: `JiraCreate`, `JiraUpdate`
- `dev_environment`: `FmeFlagRestore`, `FmeFlagDefaultAllocation`
- `qa_environment`: `FmeFlagRestore`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`
- `staging_environment`: `FmeFlagRestore`, `FmeFlagDefaultAllocation`, `Wait`
- parallel:
  - `prod_us`: `HarnessApproval`, `FmeFlagRestore`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`
  - `prod_eu`: `HarnessApproval`, `FmeFlagRestore`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`, `Wait`, `FmeFlagDefaultAllocation`
- `close_jira_ticket`: `JiraUpdate`
- `rollback_on_failure` (when: Failure): `FmeFlagKill`, `FmeFlagKill`, `JiraUpdate`

**Full pipeline:** [r2-multi-env-promotion.yaml](blueprints/r2-multi-env-promotion.yaml)

**Note:** Production regions are shown as parallel stages for simultaneous rollout. They can be changed to sequential stages if preferred.

---

## R3: Beta Cohort First, Then Everyone

**Use case:** Target beta users first, then progressively ramp to everyone.

**Customize:**
- Flag name and environment in all steps
- Beta user keys in individual targets step
- Treatment names in allocation steps
- Soak durations between ramp steps

**Stages:**

- `beta_targeting`: `FmeFlagRestore`, `FmeFlagAddRemoveIndividualTargets`, `FmeFlagDefaultAllocation`, `Wait`
- `ramp_10_percent`: `FmeFlagDefaultAllocation`, `Wait`
- `ramp_50_percent`: `FmeFlagDefaultAllocation`, `Wait`
- `ramp_100_percent`: `FmeFlagDefaultAllocation`, `FmeFlagAddRemoveIndividualTargets`

**Full pipeline:** [r3-beta-cohort.yaml](blueprints/r3-beta-cohort.yaml)

---

## R4: Config Promotion Between Environments

**Use case:** Copy validated staging configuration to production atomically (read staging definition via MCP first, then apply to prod). Optionally preceded by approval.

**Customize:**
- Flag name and environments
- Source environment definition (read via MCP `harness_get` or `harness_list` on `fme_feature_flag_definition`)
- Instructions list content based on source definition
- Optional approval before promotion

**Note:** Use `FmeFlagDefinitionInstructions` to apply multiple field changes atomically. For simple allocation-only promotion, `FmeFlagPatchDefinition` is an alternative.

**Stages:**

- `approve_promotion`: `HarnessApproval`
- `promote_definition`: `FmeFlagDefinitionInstructions`, `Wait`

**Full pipeline:** [r4-config-promotion.yaml](blueprints/r4-config-promotion.yaml)

---

## L1: Flag Bootstrap

**Use case:** Create a new flag with treatments, configure per-env settings (kill prod, restore dev), add QA test users, and optionally attach to a flagset.

**Customize:**
- Flag name, traffic type, and treatments
- Default and baseline treatments
- Per-environment kill/restore configuration
- QA test user keys
- Flagset name (optional step, mark if not needed)

**Stages:**

- `create_flag`: `FmeFlagCreate`
- `configure_per_env`: `FmeFlagKill`, `FmeFlagRestore`, `FmeFlagRestore`
- `add_qa_targets`: `FmeFlagAddRemoveIndividualTargets`
- `attach_flagset`: `FmeFlagsetCreate`, `FmeFlagAddRemoveFlagsets`

**Full pipeline:** [l1-flag-bootstrap.yaml](blueprints/l1-flag-bootstrap.yaml)

---

## L2: Flag Retirement

**Use case:** Archive a flag that's at 100% in all environments (verify via MCP before running).

**Customize:**
- Flag name in all steps
- Rollout status value (discover valid values via MCP `fme_rollout_status`)
- Flagsets to remove

**IMPORTANT:** Only run this pipeline after verifying the flag is at 100% in all environments via MCP. Do not generate this pipeline if any environment is not at 100%.

**Stages:**

- `mark_completed`: `FmeFlagUpdate`
- `remove_from_flagsets`: `FmeFlagAddRemoveFlagsets`
- `archive_flag`: `FmeFlagArchive`

**Full pipeline:** [l2-flag-retirement.yaml](blueprints/l2-flag-retirement.yaml)

---

## L3: Segment Sync from External System

**Use case:** Fetch user keys from an external system (database, API, etc.) and sync them to an FME segment.

**Customize:**
- Shell script logic to fetch keys from your external system
- Segment name and environment
- Expression for referencing ShellScript output

**Note:** The ShellScript must export keys as a JSON array (e.g., `export KEYS='["user1","user2"]'`). Verify on first run that the expression resolves to a list.

**Stages:**

- `sync_segment`: `ShellScript`, `FmeSegmentAddRemoveTargets`

**Full pipeline:** [l3-segment-sync.yaml](blueprints/l3-segment-sync.yaml)

---

## L4: Test-User Targeting for End-to-End Tests

**Use case:** Add test user keys to a flag, run E2E tests, then clean up the keys (even on test failure). All in ONE stage so cleanup runs even if tests fail.

**Customize:**
- Flag name, environment, and treatment
- Test user keys to add and remove
- Test command in ShellScript step

**Note:** Cleanup step runs via `when.stageStatus: All` so it executes even if tests fail.

**Stages:**

- `test_with_targeting`: `FmeFlagAddRemoveIndividualTargets`, `ShellScript`, `FmeFlagAddRemoveIndividualTargets`

**Full pipeline:** [l4-test-targeting.yaml](blueprints/l4-test-targeting.yaml)

---

## Notes on Customization

### Identifiers and Names
- **Identifiers**: Must match `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- **Names**: Must match `^[a-zA-Z_0-9-.][-0-9a-zA-Z_\s.]{0,127}$`

### Treatments
- Treatment names must be quoted strings (e.g., `"on"`, `"off"`)
- When using pipeline variables for treatment names, reference them as `<+pipeline.variables.onTreatment>`
- Never use `<+input>` directly in treatment fields (schema rejects it)

### Allocations
- Amounts must sum to 100 across all treatments
- Each amount is an integer between 0 and 100

### Stage Conditionals
- `when.pipelineStatus` accepts: `Success`, `Failure`, `All` (not `Failed`)
- Use `when.stageStatus: All` at the step level to run cleanup steps regardless of previous step outcomes

### Approvals
- `approvers.userGroups`: Use format `account.<group_name>` or `org.<group_name>` or `project.<group_name>`
- `minimumCount`: Number of required approvals
- `disallowPipelineExecutor`: Set to `true` to prevent the user who triggered the pipeline from approving

### Wait Durations
- Format: `<number><unit>` where unit is `s` (seconds), `m` (minutes), `h` (hours), `d` (days), `w` (weeks)
- Examples: `30m`, `2h`, `1d`

### Jira Integration
- `connectorRef`: Reference to your Jira connector
- `issueKey`: Use output from JiraCreate step: `<+pipeline.stages.<stage_id>.spec.execution.steps.<step_id>.issue.key>`
- `fields`: Array of name/value pairs for standard fields like Summary/Description or user-named fields

### Pipeline Variables
- Use `<+input>` to prompt for the value at runtime
- Reference variables as `<+pipeline.variables.<variable_name>>`
- Declare variables in the `pipeline.variables` array

### Expressions
- Stage outputs: `<+pipeline.stages.<stage_id>.spec.execution.steps.<step_id>.output.<field>>`
- Pipeline variables: `<+pipeline.variables.<variable_name>>`
- Input prompts: `<+input>`
