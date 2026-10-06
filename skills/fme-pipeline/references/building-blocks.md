# Building Blocks: Optional Add-Ons for FME Pipelines

**IMPORTANT**: These are OPTIONAL add-ons. Not every scenario needs gates or metric checks. "No gates" is a valid answer. Only offer building blocks when they fit the user's scenario.

**Validator Note**: Three examples (JiraApproval, ServiceNowApproval, ShellScript) use conditional schemas (discriminated unions) that the current validator cannot fully resolve. The YAML is correct per the Harness v0 schema but fails validation due to validator limitations with JSON Schema allOf + discriminator patterns. These examples will work correctly in Harness pipelines.

---

## 1. Harness Approval

### Purpose
Manual approval gate by designated Harness users or user groups before proceeding with flag operations.

### When to Offer
- Multi-stage rollouts with human verification checkpoints
- Production rollouts requiring sign-off
- Rollouts with compliance/audit requirements
- When user explicitly requests approval gates

### Required Fields (from schema)
- `approvers`: User groups or user IDs who can approve
- `includePipelineExecutionHistory`: Boolean to include execution context
- `approvalMessage` (optional): Custom message for approvers

### YAML Snippet

```yaml
- step:
    type: HarnessApproval
    name: Approve Production Rollout
    identifier: approve_prod
    spec:
      approvalMessage: "Review metrics and approve flag rollout to Production"
      includePipelineExecutionHistory: true
      approvers:
        userGroups:
          - release_managers
          - engineering_leads
        minimumCount: 1
        disallowPipelineExecutor: true
    timeout: 1d
```

### Output Expressions
None (approval steps don't produce outputs)

### Prerequisites
- User groups must exist: Check via `harness_list` with `resource_type: "user_group"`
- Ask user for user group identifiers if not provided

---

## 2. Wait Step

### Purpose
Introduce a fixed delay between flag operations to observe metrics, user behavior, or system stability.

### When to Offer
- Gradual rollouts with time-based pauses
- Observability windows between stages
- Rate-limited operations
- When user specifies "wait X hours between stages"

### Required Fields (from schema)
- `duration`: Duration string (e.g., "30m", "2h", "1d")

### YAML Snippet

```yaml
- step:
    type: Wait
    name: Wait for Metrics
    identifier: wait_for_metrics
    spec:
      duration: 1h
    timeout: 2h
```

### Output Expressions
None

### Prerequisites
None

---

## 3. Jira Create

### Purpose
Create a Jira issue to track the flag rollout, document the change, or trigger downstream workflows.

### When to Offer
- Rollouts requiring change tracking
- Integration with Jira-based workflows
- Documentation and audit trail requirements
- When user mentions "create Jira ticket"

### Required Fields (from schema)
- `connectorRef`: Jira connector identifier
- `projectKey`: Jira project key (e.g., "REL")
- `issueType`: Jira issue type (e.g., "Task", "Story")
- `fields` (optional): Custom fields (summary, description, etc.)

### YAML Snippet

```yaml
- step:
    type: JiraCreate
    name: Create Rollout Ticket
    identifier: create_jira
    spec:
      connectorRef: jira_connector
      projectKey: REL
      issueType: Task
      fields:
        - name: Summary
          value: "Feature flag rollout: <+pipeline.variables.flagName>"
        - name: Description
          value: "Automated rollout pipeline for flag <+pipeline.variables.flagName> in <+pipeline.variables.environment>"
    timeout: 5m
```

### Output Expressions
- Issue key: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.issue.key>`
- Issue URL: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.issue.url>`

Use the actual step identifier in place of `STEP_ID`.

### Prerequisites
- Jira connector must exist: Check via `harness_list` with `resource_type: "connector"` and filter by type `Jira`
- Ask user for connector reference and project key if not provided

---

## 4. Jira Update

### Purpose
Update an existing Jira issue with rollout progress or change status.

**IMPORTANT**: There's no dedicated Jira comment step today, so this skill doesn't generate comments. Offer a status transition or field update instead.

### When to Offer
- After creating a Jira issue earlier in the pipeline
- Status transitions (e.g., "In Progress" → "Done")
- Field updates for standard fields like Summary/Description or user-named fields
- When user requests "update the Jira ticket"

### Required Fields (from schema)
- `connectorRef`: Jira connector identifier
- `issueKey`: Jira issue key (from JiraCreate output or user input)
- `transitionTo` (optional): Status transition
- `fields` (optional): Fields to update

### YAML Snippet

```yaml
- step:
    type: JiraUpdate
    name: Update Rollout Status
    identifier: update_jira
    spec:
      connectorRef: jira_connector
      issueKey: <+pipeline.stages.rollout.spec.execution.steps.create_jira.issue.key>
      transitionTo:
        transitionName: Done
        status: Done
    timeout: 5m
```

### Output Expressions
None (update steps don't produce outputs)

### Prerequisites
- Jira connector must exist
- Issue key must be available (from JiraCreate step or user input)

---

## 5. Jira Approval

### Purpose
Wait for a Jira issue to reach a specific status before proceeding (e.g., wait for ticket approval).

### When to Offer
- External approval workflows via Jira
- When user mentions "wait for Jira approval"
- Integration with existing Jira-based approval processes

### Required Fields (from schema)
- `connectorRef`: Jira connector identifier
- `issueKey`: Jira issue key to monitor
- `approvalCriteria`: Condition to approve (status match)
- `rejectionCriteria` (optional): Condition to reject

### YAML Snippet

```yaml
- step:
    type: JiraApproval
    name: Wait for Jira Approval
    identifier: jira_approval
    spec:
      connectorRef: jira_connector
      issueKey: <+pipeline.stages.rollout.spec.execution.steps.create_jira.issue.key>
      approvalCriteria:
        type: Jexl
        spec:
          expression: <+issue.fields.Status> == "Approved"
      rejectionCriteria:
        type: Jexl
        spec:
          expression: <+issue.fields.Status> == "Rejected"
    timeout: 1d
```

### Output Expressions
None

### Prerequisites
- Jira connector must exist
- Issue key must be available

---

## 6. ServiceNow Create

### Purpose
Create a ServiceNow change request or incident ticket for the flag rollout.

### When to Offer
- ITIL/ITSM compliance requirements
- Change management workflows
- ServiceNow-based approval processes
- When user mentions "create ServiceNow ticket"

### Required Fields (from schema)
- `connectorRef`: ServiceNow connector identifier
- `ticketType`: Ticket type (e.g., "change_request", "incident")
- `fields` (optional): Custom fields
- `useServiceNowTemplate` (optional): Use ServiceNow template

### YAML Snippet

```yaml
- step:
    type: ServiceNowCreate
    name: Create Change Request
    identifier: create_snow
    spec:
      connectorRef: servicenow_connector
      ticketType: change_request
      fields:
        - name: short_description
          value: "Feature flag rollout: <+pipeline.variables.flagName>"
        - name: description
          value: "Automated rollout for flag <+pipeline.variables.flagName>"
        - name: priority
          value: "3"
    timeout: 5m
```

### Output Expressions
- Ticket number: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.ticket.ticketNumber>`
- Ticket URL: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.ticket.url>`

### Prerequisites
- ServiceNow connector must exist: Check via `harness_list` with `resource_type: "connector"` and filter by type `ServiceNow`
- Ask user for connector reference and ticket type if not provided

---

## 7. ServiceNow Update

### Purpose
Update an existing ServiceNow ticket with rollout progress or change status.

### When to Offer
- After creating a ServiceNow ticket earlier in the pipeline
- Status transitions or field updates
- When user requests "update the ServiceNow ticket"

### Required Fields (from schema)
- `connectorRef`: ServiceNow connector identifier
- `ticketType`: Ticket type
- `ticketNumber`: Ticket number (from ServiceNowCreate output or user input)
- `useServiceNowTemplate`: Boolean

### YAML Snippet

```yaml
- step:
    type: ServiceNowUpdate
    name: Update Change Request
    identifier: update_snow
    spec:
      connectorRef: servicenow_connector
      ticketType: change_request
      ticketNumber: <+pipeline.stages.rollout.spec.execution.steps.create_snow.ticket.ticketNumber>
      useServiceNowTemplate: false
      fields:
        - name: state
          value: "Closed"
        - name: close_notes
          value: "Rollout completed successfully"
    timeout: 5m
```

### Output Expressions
None

### Prerequisites
- ServiceNow connector must exist
- Ticket number must be available

---

## 8. ServiceNow Approval

### Purpose
Wait for a ServiceNow ticket to reach a specific state before proceeding (e.g., wait for change approval).

### When to Offer
- ServiceNow-based approval workflows
- ITIL compliance with approval gates
- When user mentions "wait for ServiceNow approval"

### Required Fields (from schema)
- `connectorRef`: ServiceNow connector identifier
- `ticketType`: Ticket type
- `ticketNumber`: Ticket number to monitor
- `approvalCriteria`: Condition to approve

### YAML Snippet

```yaml
- step:
    type: ServiceNowApproval
    name: Wait for Change Approval
    identifier: snow_approval
    spec:
      connectorRef: servicenow_connector
      ticketType: change_request
      ticketNumber: <+pipeline.stages.rollout.spec.execution.steps.create_snow.ticket.ticketNumber>
      approvalCriteria:
        type: Jexl
        spec:
          expression: <+ticket.state> == "Approved"
      rejectionCriteria:
        type: Jexl
        spec:
          expression: <+ticket.state> == "Rejected"
    timeout: 1d
```

### Output Expressions
None

### Prerequisites
- ServiceNow connector must exist
- Ticket number must be available

---

## 9. FmeMetricCheck

### Purpose
Validate feature flag metrics against success criteria. Fails the step (and optionally the pipeline) when `failureCriteria` evaluates to true. Does NOT auto-roll back the flag — use kill-on-failure stage for that.

### When to Offer
- Rollouts with metric validation
- Data-driven decision gates
- SLO/SLI enforcement
- When user mentions "check metrics", "validate metrics", or "metric gates"

### Required Fields (from schema)
- `flagName`: Feature flag name (string or JEXL expression)
- `environment`: FME environment ID (string or JEXL expression)
- `lookbackWindow`: Time window (e.g., "7d", "24h")
- `failureCriteria`: JEXL condition (true = FAIL, false = PASS)
- `metrics` (optional): Array of metric refs to evaluate

### YAML Snippet

```yaml
- step:
    type: FmeMetricCheck
    name: Validate Error Rate
    identifier: check_metrics
    spec:
      flagName: <+pipeline.variables.flagName>
      environment: <+pipeline.variables.environment>
      lookbackWindow: 1h
      metrics:
        - ref: error_rate_mean
        - ref: latency_p95
      failureCriteria:
        type: Jexl
        spec:
          condition: <+metrics.error_rate_mean> > 0.05 || <+metrics.latency_p95> > 500
    timeout: 10m
```

### Output Expressions
- Metric values: `<+metrics.METRIC_NAME>` (available in JEXL conditions)

### Prerequisites
- FME environment must exist: Check via `harness_list` with `resource_type: "fme_environment"`
- Metrics must be defined in FME
- Ask user for metric names and thresholds if not provided

---

## 10. Kill on Failure (Rollback Stage)

### Purpose
Automatically kill the feature flag (set to "off" for all targets) when the pipeline fails, providing an emergency rollback mechanism.

### When to Offer
- High-risk production rollouts
- When user requests "auto-rollback" or "kill on failure"
- Rollouts with strict safety requirements

### Required Fields (from schema)
- `flagName`: Feature flag name
- `environment`: FME environment ID

### YAML Snippet

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

### Output Expressions
None

### Prerequisites
- FME environment must exist
- Flag must exist in the environment

---

## 11. Shell Script

### Purpose
Run custom bash or PowerShell scripts for:
- Custom validation logic
- External API calls
- L3/L4 health checks
- Integration with monitoring systems
- Custom metric collection

### When to Offer
- Custom validation requirements
- Integration with external systems not covered by built-in steps
- When user mentions "run a script", "custom check", or "call an API"

### Required Fields (from schema)
- `shell`: Shell type ("Bash" or "PowerShell")
- `source`: Script source (inline or file)
- `onDelegate`: Boolean (true to run on delegate)

### YAML Snippet

```yaml
- step:
    type: ShellScript
    name: Check External API
    identifier: check_api
    spec:
      shell: Bash
      onDelegate: true
      source:
        type: Inline
        spec:
          script: "curl -s https://api.example.com/health | jq -r '.error_rate'"
      environmentVariables:
        - name: FLAG_NAME
          type: String
          value: <+pipeline.variables.flagName>
      outputVariables:
        - name: error_rate
          type: String
          value: error_rate
    timeout: 10m
```

### Output Expressions
- Output variables: `<+pipeline.stages.STAGE_ID.spec.execution.steps.STEP_ID.output.outputVariables.VARIABLE_NAME>`

### Prerequisites
- Delegate must be available and healthy
- External dependencies (curl, jq, etc.) must be installed on delegate

---

## 12. Pipeline Variables & Expressions

### Purpose
Create reusable pipelines where flag names, environments, and treatment names are parameterized as runtime inputs.

### When to Offer
- User wants a generic/reusable rollout pipeline
- Multiple flags with similar rollout patterns
- When user says "make it reusable" or "parameterize the pipeline"

### Required Setup
1. **Pipeline Variables**: Define at the top level
2. **Treatment Variables**: Must be pipeline VARIABLES (not `<+input>` in treatment fields, as schema rejects it)
3. **Reference Variables**: Use `<+pipeline.variables.VAR_NAME>` in step specs

### YAML Snippet

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
    - name: environment
      type: String
      description: "FME environment ID"
      value: <+input>
    - name: onTreatment
      type: String
      description: "Treatment to enable (default: on)"
      value: "on"
    - name: targetKey
      type: String
      description: "Target identifier to add"
      value: <+input>
  stages:
    - stage:
        name: Enable Flag
        identifier: enable
        type: Custom
        spec:
          execution:
            steps:
              - step:
                  type: FmeFlagAddRemoveIndividualTargets
                  name: Add Individual Target
                  identifier: add_target
                  spec:
                    flagName: <+pipeline.variables.flagName>
                    environment: <+pipeline.variables.environment>
                    treatments:
                      - treatment: <+pipeline.variables.onTreatment>
                        addKeys:
                          - <+pipeline.variables.targetKey>
```

### Why Treatment Names are Pipeline Variables
The schema rejects `<+input>` directly in treatment fields. Treatment names must be pipeline VARIABLES with default values (e.g., `onTreatment: "on"`), then referenced as `<+pipeline.variables.onTreatment>`.

### Prerequisites
None (variables are part of the pipeline definition)

---

## 13. Failure Strategies

### Purpose
Define how the pipeline behaves when steps fail:
- **MarkAsFailure**: Stop execution and mark pipeline as failed (use for FME-mutating stages; hides no failures)
- **Ignore**: Continue execution despite failure (do NOT use for FME-mutating stages; hides failures)
- **Abort**: Stop on rejected approvals

### When to Offer
- Always include for Custom stages (FeatureFlag stages have built-in handling)
- When user asks about "error handling" or "what happens if it fails"

### Custom Stage Failure Strategy

**IMPORTANT**: Custom stages do NOT support `StageRollback` because they have no rollback section. Always use `MarkAsFailure` for FME-mutating stages (never `Ignore`).

### YAML Snippet

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

### Prerequisites
None

---

## Prerequisites Summary

Before generating a pipeline with building blocks, the skill MUST check:

1. **Jira Connector** (if using Jira steps):
   ```
   harness_list(resource_type="connector")
   ```
   Then pick ones whose type is Jira.

2. **ServiceNow Connector** (if using ServiceNow steps):
   ```
   harness_list(resource_type="connector")
   ```
   Then pick ones whose type is ServiceNow.

3. **User Groups** (if using HarnessApproval):
   ```
   harness_list(resource_type="user_group")
   ```

4. **FME Environment** (always check for FME steps):
   ```
   harness_list(resource_type="fme_environment")
   ```

If a prerequisite doesn't exist, ASK the user for the identifier or offer to skip that building block.

---

## Usage Notes

1. **Building blocks are optional**: Only add them when they fit the scenario.
2. **"No gates" is valid**: Don't force approvals or checks if user doesn't want them.
3. **Realistic values**: Use actual connector names, project keys, and identifiers from MCP list calls.
4. **Output expressions**: Double-check stage and step identifiers match the YAML.
5. **Custom stage limits**: No rollback section, so use MarkAsFailure instead of StageRollback.
