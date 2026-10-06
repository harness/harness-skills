# FME Pipeline Blueprints

Complete pipeline YAML blueprints for each scenario from [scenarios.md](scenarios.md). Each blueprint is production-ready with realistic placeholders.

## Index

| Blueprint | Use case | Key inputs | YAML |
|-----------|----------|------------|------|
| **R1: Progressive Ramp** | Roll out a flag progressively within a single environment with approval gates between each % increase | Flag name, environment, treatment names, ramp schedule (e.g., 25→50→100), approval user groups | [r1-progressive-ramp.yaml](blueprints/r1-progressive-ramp.yaml) |
| **R2: Multi-Environment Promotion** | Reusable pipeline for promoting any flag across dev → qa → staging → prod (us + eu regions) with environment-specific ramp schedules, approval gates, and Jira ticket tracking | Flag name as pipeline input, treatment names as variables, Jira connector, approver user groups, environments, ramp schedules per env, production regions (parallel or sequential) | [r2-multi-env-promotion.yaml](blueprints/r2-multi-env-promotion.yaml) |
| **R3: Beta Cohort First** | Target beta users first, then progressively ramp to everyone | Flag name, environment, beta user keys, treatment names, ramp schedule after beta, soak durations | [r3-beta-cohort.yaml](blueprints/r3-beta-cohort.yaml) |
| **R4: Config Promotion** | Copy validated staging configuration to production atomically (read staging definition first, then apply to prod); optionally preceded by approval | Flag name, source environment (staging), target environment (prod), source definition content (via List definitions), optional approval | [r4-config-promotion.yaml](blueprints/r4-config-promotion.yaml) |
| **L1: Flag Bootstrap** | Create a new flag with treatments, configure per-env settings (kill prod, restore dev), add QA test users, optionally attach to a flagset | Flag name, traffic type, treatment names, default/baseline treatments, per-env kill/restore/allocation/targets, QA test user keys, flagset name (optional) | [l1-flag-bootstrap.yaml](blueprints/l1-flag-bootstrap.yaml) |
| **L2: Flag Retirement (preparatory only)** | Prepare a flag that's at 100% in all environments for retirement — status update + flagset detach; does NOT archive (verify via List definitions before running; archive separately via `/manage-flag-lifecycle` after code removal, with a fresh readiness check) | Flag name (verify 100% first), rollout status value (via List rollout statuses), flagsets to remove | [l2-flag-retirement.yaml](blueprints/l2-flag-retirement.yaml) |
| **L3: Segment Sync** | Fetch user keys from an external system (database, API, etc.) and sync them to an FME segment | Segment name, environment, external system details (how to fetch keys), script to fetch keys (exports keys as JSON array), add or remove keys | [l3-segment-sync.yaml](blueprints/l3-segment-sync.yaml) |
| **L4: Test-User Targeting** | Add test user keys to a flag, run E2E tests, then clean up the keys (even on test failure); all in ONE stage so cleanup runs even if tests fail | Flag name, environment, treatment, test user keys to add/remove, test command in ShellScript step | [l4-test-targeting.yaml](blueprints/l4-test-targeting.yaml) |

## Customization Notes

### Identifiers and Names
- **Identifiers**: Must match `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- **Names**: Must match `^[a-zA-Z_0-9-.][-0-9a-zA-Z_\s.]{0,127}$`

### Treatments
- Treatment names must be quoted strings (e.g., `"on"`, `"off"`)
- When using pipeline variables, reference as `<+pipeline.variables.onTreatment>`
- Never use `<+input>` directly in treatment fields (schema rejects it)

### Allocations
- Amounts must sum to 100 across all treatments
- Each amount is an integer between 0 and 100

### Stage Conditionals
- `when.pipelineStatus` accepts: `Success`, `Failure`, `All` (not `Failed`)
- Use `when.stageStatus: All` at step level to run cleanup steps regardless of previous step outcomes

### Approvals
- `approvers.userGroups`: Use format `account.<group_name>` or `org.<group_name>` or `project.<group_name>`
- `minimumCount`: Number of required approvals
- `disallowPipelineExecutor`: Set to `true` to prevent pipeline executor from approving

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
