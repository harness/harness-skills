# FME rollout pipeline YAML examples

Minimal snippets for composition. Replace placeholders; confirm `orgIdentifier`, `projectIdentifier`, environment names, and treatments with the user via MCP or explicit confirmation — **do not assume** `staging`/`production` or `on`/`off` without verification.

## FeatureFlag stage skeleton

```yaml
- stage:
    identifier: ff_rollout_staging
    name: Rollout Staging
    type: FeatureFlag
    spec:
      execution:
        steps:
          - step:
              identifier: restore_flag_staging
              name: Restore Flag
              type: FmeFlagRestore
              spec:
                flagName: new_checkout_flow
                environment: staging
          - step:
              identifier: allocate_25_staging
              name: Allocate 25 Percent
              type: FmeFlagDefaultAllocation
              spec:
                flagName: new_checkout_flow
                environment: staging
                allocation:
                  - treatment: "on"
                    amount: 25
                  - treatment: "off"
                    amount: 75
    failureStrategies:
      - onFailure:
          errors: [AllErrors]
          action:
            type: MarkAsFailure
```

## Clearing or setting targeting rules

`FmeFlagSetTargetingRules` **replaces** the full rule list — pass `targetingRules: []` to clear existing rules (e.g. before setting a default-rule allocation that should apply to everyone):

```yaml
- step:
    identifier: clear_staging_rules
    name: Clear Staging Targeting Rules
    type: FmeFlagSetTargetingRules
    spec:
      flagName: new_checkout_flow
      environment: staging
      targetingRules: []
```

To set a rule instead of clearing:

```yaml
- step:
    identifier: set_staging_rules
    name: Set Staging Targeting Rules
    type: FmeFlagSetTargetingRules
    spec:
      flagName: new_checkout_flow
      environment: staging
      targetingRules:
        - matcher: "<+user-supplied condition, e.g. country IN [US]>"
          allocation:
            - treatment: "on"
              amount: 100
            - treatment: "off"
              amount: 0
```

Confirm the exact matcher/rule shape against the live definition (`harness_get` / `harness_list` on `fme_feature_flag_definition`) before writing — do not guess field names for the matcher object.

## Approval gate between stages

```yaml
- stage:
    identifier: approve_prod_rollout
    name: Approve Production Rollout
    type: Approval
    spec:
      execution:
        steps:
          - step:
              identifier: prod_rollout_approval
              name: Production Rollout Approval
              type: HarnessApproval
              spec:
                approvalMessage: "Staging at 100%. Approve production rollout for new_checkout_flow."
                approvers:
                  userGroups: [prod_approvers]
                  minimumCount: 1
                  disallowPipelineExecutor: true
                includePipelineExecutionHistory: true
              timeout: 1d
    failureStrategies:
      - onFailure:
          errors: [AllErrors]
          action:
            type: Abort
```

## Multi-environment promotion with staging gate

```yaml
pipeline:
  identifier: new_checkout_flow_rollout
  name: New Checkout Flow Rollout
  projectIdentifier: my_project
  orgIdentifier: default
  stages:
    - stage:
        identifier: ff_dev
        name: Dev Full Launch
        type: FeatureFlag
        spec:
          execution:
            steps:
              - step:
                  type: FmeFlagRestore
                  identifier: restore_dev
                  name: Restore Dev
                  spec:
                    flagName: new_checkout_flow
                    environment: dev
              - step:
                  type: FmeFlagDefaultAllocation
                  identifier: launch_dev
                  name: Launch Dev
                  spec:
                    flagName: new_checkout_flow
                    environment: dev
                    allocation:
                      - treatment: "on"
                        amount: 100
                      - treatment: "off"
                        amount: 0
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: MarkAsFailure

    - stage:
        identifier: ff_staging
        name: Staging Full Launch
        type: FeatureFlag
        spec:
          execution:
            steps:
              - step:
                  type: FmeFlagRestore
                  identifier: restore_staging
                  name: Restore Staging
                  spec:
                    flagName: new_checkout_flow
                    environment: staging
              - step:
                  type: FmeFlagDefaultAllocation
                  identifier: launch_staging
                  name: Launch Staging
                  spec:
                    flagName: new_checkout_flow
                    environment: staging
                    allocation:
                      - treatment: "on"
                        amount: 100
                      - treatment: "off"
                        amount: 0
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: MarkAsFailure

    - stage:
        identifier: approve_prod
        name: Approve Production
        type: Approval
        spec:
          execution:
            steps:
              - step:
                  type: HarnessApproval
                  identifier: approve_prod_rollout
                  name: Approve Prod
                  spec:
                    approvalMessage: "Confirm staging verified at 100% for new_checkout_flow"
                    approvers:
                      userGroups: [prod_approvers]
                      minimumCount: 1
                      disallowPipelineExecutor: true
                    includePipelineExecutionHistory: true
                  timeout: 1d
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: Abort

    - stage:
        identifier: ff_prod
        name: Production Progressive Rollout
        type: FeatureFlag
        spec:
          execution:
            steps:
              - step:
                  type: FmeFlagRestore
                  identifier: restore_prod
                  name: Restore Production
                  spec:
                    flagName: new_checkout_flow
                    environment: production
              - step:
                  type: FmeFlagDefaultAllocation
                  identifier: allocate_10_prod
                  name: Allocate 10 Percent Prod
                  spec:
                    flagName: new_checkout_flow
                    environment: production
                    allocation:
                      - treatment: "on"
                        amount: 10
                      - treatment: "off"
                        amount: 90
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: StageRollback
```

## Progressive percentage in one environment (sequential stages)

Use separate stages when you need approval or soak time between percentages:

```yaml
# Stage 1: 5% → Stage 2: Approval → Stage 3: 25% → Stage 4: 100%
```

Each `FeatureFlag` stage contains `FmeFlagDefaultAllocation` only (restore once in the first stage). Insert `Approval` or `Wait` stages between them.

## Soak / metric gate (not auto-rollback)

```yaml
- stage:
    identifier: soak_staging_25
    name: Soak Staging 25 Percent
    type: Custom
    spec:
      execution:
        steps:
          - step:
              identifier: wait_1h
              name: Wait One Hour
              type: Wait
              spec:
                duration: 1h
          - step:
              identifier: metric_check_staging
              name: Metric Check Staging
              type: FmeMetricCheck
              spec:
                flagName: new_checkout_flow
                environment: staging
                lookbackWindow: 1h
                failureCriteria:
                  type: Jexl
                  spec:
                    condition: "<+user-supplied JEXL; true means fail>"
    failureStrategies:
      - onFailure:
          errors: [AllErrors]
          action:
            type: MarkAsFailure
```

Ask the user for the JEXL condition and metric `ref` names. A failed check does **not** kill the flag — add a following or failure-path `FmeFlagKill` stage if they want rollback.

## Downstream gating — keep production killed

Early pipeline run (prod held):

```yaml
- stage:
    identifier: ff_ensure_prod_off
    name: Ensure Production Off
    type: FeatureFlag
    spec:
      execution:
        steps:
          - step:
              type: FmeFlagKill
              identifier: kill_prod
              name: Kill Production
              spec:
                flagName: new_checkout_flow
                environment: production
```

Omit the production launch stage until the user is ready for a follow-up pipeline or later stages in the same pipeline after approval.

## Rollback stage

```yaml
- stage:
    identifier: ff_rollback_prod
    name: Rollback Production Flag
    type: FeatureFlag
    spec:
      execution:
        steps:
          - step:
              type: FmeFlagKill
              identifier: kill_prod_rollback
              name: Kill Flag Production
              spec:
                flagName: new_checkout_flow
                environment: production
    when:
      pipelineStatus: Failure
```

Adjust `when` to match your rollback trigger strategy.

## Pipeline inputs for environment and allocation

For reusable rollout pipelines:

```yaml
spec:
  flagName: <+input>
  environment: <+input>
  allocation: <+input>
```

Use when the same pipeline shape rolls out different flags or percentages per run.

## Creating via MCP

After user confirms the plan:

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<org>"
  project_id: "<project>"
  body:
    yamlPipeline: "<full pipeline YAML string, including 'pipeline:' root key>"
```

To append FME stages to an existing pipeline:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<org>"
  project_id: "<project>"
```

Merge stages, then:

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<org>"
  project_id: "<project>"
  body:
    yamlPipeline: "<full updated pipeline YAML string>"
```

Verify the project exists (`harness_list` with `resource_type: "project"` and `org_id` only) before creating.

