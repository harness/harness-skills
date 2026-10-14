# Building Blocks: Optional Add-Ons for FME Pipelines

**IMPORTANT**: These are OPTIONAL. Not every scenario needs gates or metric checks. "No gates" is a valid answer. Only offer when they fit the user's scenario.

Field specs are in [step-catalog.md](step-catalog.md). This file covers composition patterns and when to offer each block.

---

## 1. Harness Approval

**When to offer:** Multi-stage rollouts with human verification checkpoints, production rollouts requiring sign-off, when user requests approval gates.

**Required fields:** `approvers` (object with `userGroups`, `minimumCount`, `disallowPipelineExecutor`), `includePipelineExecutionHistory` (boolean). See [step-catalog.md](step-catalog.md#harnessapproval).

**Prerequisites:** User groups must exist (**List user groups**).

---

## 2. Wait Step

**When to offer:** Gradual rollouts with time-based pauses, observability windows, when user specifies "wait X hours between stages".

**Required fields:** `duration` (e.g., "30m", "2h", "1d"). See [step-catalog.md](step-catalog.md#wait).

---

## 3. Jira Create

**When to offer:** Rollouts requiring change tracking, Jira workflows, when user mentions "create Jira ticket".

**Required fields:** `connectorRef`, `projectKey`, `issueType`. Optional: `fields`. See [step-catalog.md](step-catalog.md#jiracreate).

**Output expressions:** Issue key: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.issue.key>`

**Prerequisites:** Jira connector must exist (**List connectors** type Jira).

---

## 4. Jira Update

**When to offer:** After creating a Jira issue, status transitions, field updates, when user requests "update the Jira ticket".

**IMPORTANT:** No dedicated Jira comment step today. Offer status transition or field update instead.

**Required fields:** `connectorRef`, `issueKey`. Optional: `transitionTo`, `fields`. See [step-catalog.md](step-catalog.md#jiraupdate).

**Prerequisites:** Jira connector, issue key must be available.

---

## 5. Jira Approval

**When to offer:** External approval workflows via Jira, when user mentions "wait for Jira approval".

**Required fields:** `connectorRef`, `issueKey`, `approvalCriteria` (type: `Jexl` or `KeyValues`). See [step-catalog.md](step-catalog.md#jiraapproval).

---

## 6. ServiceNow Create

**When to offer:** ITIL/ITSM compliance, change management workflows, when user mentions "create ServiceNow ticket".

**Required fields:** `connectorRef`, `ticketType`. Optional: `fields`. See [step-catalog.md](step-catalog.md#servicenowcreate).

**Output expressions:** Ticket number: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.ticket.ticketNumber>`

**Prerequisites:** ServiceNow connector must exist (**List connectors** type ServiceNow).

---

## 7. ServiceNow Update

**When to offer:** After creating a ServiceNow ticket, status transitions, field updates, when user requests "update the ServiceNow ticket".

**Required fields:** `connectorRef`, `ticketType`, `ticketNumber`, `useServiceNowTemplate`. See [step-catalog.md](step-catalog.md#servicenowupdate).

---

## 8. ServiceNow Approval

**When to offer:** ServiceNow-based approval workflows, ITIL compliance, when user mentions "wait for ServiceNow approval".

**Required fields:** `connectorRef`, `ticketType`, `ticketNumber`, `approvalCriteria`. See [step-catalog.md](step-catalog.md#servicenowapproval).

---

## 9. FmeMetricCheck

**When to offer:** Rollouts with metric validation, data-driven gates, when user mentions "check metrics", "validate metrics", or "metric gates".

**Validates metrics against success criteria. Fails the step when `failureCriteria` evaluates to true. Does NOT auto-roll back the flag — use kill-on-failure stage for that.**

**Required fields:** `flagName`, `environment`, `lookbackWindow` (e.g., "7d", "24h"), `failureCriteria` (JEXL condition: true = FAIL). Optional: `metrics`. See [step-catalog.md](step-catalog.md#fmemetriccheck).

**Output expressions:** Metric values: `<+metrics.METRIC_NAME>` (in JEXL).

**Prerequisites:** Environment must exist (**List environments**), metrics must be defined.

---

## 10. Kill on Failure (Rollback Stage)

**When to offer:** High-risk production rollouts, when user requests "auto-rollback" or "kill on failure", strict safety requirements.

**Automatically kills the feature flag (everyone gets `defaultTreatment`) when the pipeline fails.**

**Pattern:**

```yaml
- stage:
    name: Rollback on Failure
    identifier: rollback
    type: Custom
    spec:
      execution:
        steps:
          - step:
              type: FmeFlagKill
              name: Kill Flag
              identifier: kill_flag
              spec:
                flagName: <+pipeline.variables.flagName>
                environment: <+pipeline.variables.environment>
              timeout: 5m
    when:
      pipelineStatus: Failure
```

**Required fields:** `flagName`, `environment`. See [step-catalog.md](step-catalog.md#fmeflagkill).

---

## 11. Shell Script

**When to offer:** Custom validation, integration with external systems, when user mentions "run a script", "custom check", or "call an API".

**Purpose:** Custom bash/PowerShell scripts for validation logic, external API calls, health checks, monitoring integration, custom metric collection.

**Required fields:** `shell` ("Bash" or "PowerShell"), `source` (type: `Inline` or `Harness`). See [step-catalog.md](step-catalog.md#shellscript).

**Output expressions:** Output variables: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.output.outputVariables.VARIABLE_NAME>`

**Prerequisites:** Delegate must be available, external dependencies (curl, jq, etc.) installed.

---

## 12. Pipeline Variables & Expressions

**When to offer:** User wants generic/reusable rollout pipeline, multiple flags with similar patterns, when user says "make it reusable" or "parameterize the pipeline".

**Purpose:** Create reusable pipelines where flag names, environments, and treatment names are parameterized as runtime inputs.

**Required setup:**
1. **Pipeline Variables**: Define at top level
2. **Treatment Variables**: Must be pipeline VARIABLES (not `<+input>` in treatment fields — schema rejects it)
3. **Reference Variables**: Use `<+pipeline.variables.VAR_NAME>` in step specs

**Why treatment names are pipeline variables:** Schema rejects `<+input>` directly in treatment fields. Treatment names must be pipeline VARIABLES with default values (e.g., `onTreatment: "on"`), then referenced as `<+pipeline.variables.onTreatment>`.

**Example pattern:**

```yaml
pipeline:
  name: Generic Flag Rollout
  identifier: generic_rollout
  projectIdentifier: my_project
  orgIdentifier: default
  variables:
    - name: flagName
      type: String
      description: "Feature flag name"
      value: <+input>
    - name: onTreatment
      type: String
      description: "Treatment to enable (default: on)"
      value: "on"
```

---

## 13. Failure Strategies

**Define how the pipeline behaves when steps fail:**
- **MarkAsFailure**: Stop execution and mark pipeline as failed (use for FME-mutating stages)
- **Ignore**: Continue despite failure (do NOT use for FME-mutating stages; hides failures)
- **Abort**: Stop on rejected approvals

**When to offer:** Always include for Custom stages, when user asks about "error handling" or "what happens if it fails".

**IMPORTANT:** Custom stages do NOT support `StageRollback` because they have no rollback section. Always use `MarkAsFailure` for FME-mutating stages (never `Ignore`).

**Example pattern:**

```yaml
- stage:
    name: Production Rollout
    identifier: prod_rollout
    type: Custom
    spec:
      execution:
        steps:
          - step:
              type: FmeFlagAddRemoveIndividualTargets
              name: Add Target
              identifier: add_target
              spec:
                flagName: <+pipeline.variables.flagName>
                environment: prod
                treatments:
                  - treatment: "on"
                    addKeys:
                      - user_123
              timeout: 5m
    failureStrategies:
      - onFailure:
          errors:
            - AllErrors
          action:
            type: MarkAsFailure
```

---

## Prerequisites Summary

Before generating a pipeline with building blocks, check:

1. **Jira Connector** (if using Jira steps): **List connectors** (type Jira).
2. **ServiceNow Connector** (if using ServiceNow steps): **List connectors** (type ServiceNow).
3. **User Groups** (if using HarnessApproval): **List user groups**.
4. **Environment** (always for FME steps): **List environments**.

If a prerequisite doesn't exist, ASK the user or offer to skip that building block.

---

## Usage Notes

1. **Building blocks are optional**: Only add when they fit the scenario.
2. **"No gates" is valid**: Don't force approvals/checks if user doesn't want them.
3. **Realistic values**: Use actual connector names, project keys, identifiers from list calls.
4. **Output expressions**: Double-check stage and step identifiers match the YAML.
5. **Custom stage limits**: No rollback section, so use MarkAsFailure instead of StageRollback.
