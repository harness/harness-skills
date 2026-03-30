---
name: run-pipeline
description: >-
  Execute and monitor Harness pipeline runs via MCP tools. Find pipelines, provide runtime inputs, trigger
  executions, monitor progress, handle approvals, retry failures, and abort running or stuck executions.
  Use when asked to run a pipeline, execute a deployment, trigger a build, start a pipeline, deploy a
  service, check execution status, approve a pipeline, or abort/stop/interrupt executions. Trigger phrases:
  run pipeline, execute pipeline, deploy, start build, trigger pipeline, check execution, approve
  deployment, retry failed pipeline, abort execution, stop pipeline, interrupt execution, kill stuck
  pipeline.
metadata:
  author: Harness
  version: 2.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Run Pipeline

Execute and monitor Harness pipeline runs via MCP.

## Instructions

### Step 1: Find the Pipeline

```
Call MCP tool: harness_search
Parameters:
  query: "<user's pipeline name or keyword>"
  resource_types: ["pipeline"]
  compact: true
```

Or list all pipelines in a project:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  search_term: "<optional filter>"
```

### Step 2: Get Pipeline Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

Extract from response:
- Required runtime inputs (`<+input>` fields)
- Pipeline variables with types and defaults
- Stage structure and deployment targets

### Step 3: Check Available Input Sets

```
Call MCP tool: harness_list
Parameters:
  resource_type: "input_set"
  org_id: "<organization>"
  project_id: "<project>"
```

Input sets provide pre-configured values that can be used or overridden.

### Step 4: Execute the Pipeline

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "pipeline"
  action: "run"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 5: Monitor Execution

```
Call MCP tool: harness_get
Parameters:
  resource_type: "execution"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

Execution statuses: Running, Success, Failed, Aborted, Waiting (approval/input), Expired

### Step 6: Handle Approvals

If execution is waiting for approval:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "approval_instance"
  org_id: "<organization>"
  project_id: "<project>"
```

Then approve or reject:

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "approval_instance"
  action: "approve"  # or "reject"
  resource_id: "<approval_id>"
```

## Safety: Production Deployments

CRITICAL: Before executing pipelines targeting production:

1. Confirm intent with the user explicitly
2. Show what will be deployed (version, service, environment)
3. Check if pipeline has approval gates
4. Verify the version was tested in lower environments

## Response Format

### Before Execution
```
Pipeline: <name>
Project: <project>
Required Inputs: <list variables needing values>
Available Input Sets: <list>
Ready to execute? Confirm to proceed.
```

### After Trigger
```
Pipeline: <name>
Execution ID: <id>
Status: Running
View in Harness: <openInHarness link>
```

### Execution Complete
```
Pipeline: <name>
Status: Success/Failed
Duration: <time>
Stages: <stage results table>
```

## Retrying Failed Executions

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "execution"
  action: "retry"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

## Interrupting Running Executions

To abort an entire pipeline execution:

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "execution"
  action: "interrupt"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
  interrupt_type: "AbortAll"
```

The `interrupt_type` parameter is required. Valid values:

| interrupt_type | Effect |
|----------------|--------|
| `AbortAll` | Abort the entire pipeline execution |
| `UserMarkedFailure` | Mark the execution as failed by user |

To abort multiple stuck executions, call `harness_execute` with `interrupt_type: "AbortAll"` for each execution ID.

## Examples

- "Run the ci-pipeline" - Search for pipeline, execute with defaults
- "Deploy version 2.0.0 to staging" - Find deploy pipeline, provide version input, execute
- "What's the status of execution xyz123?" - Get execution details
- "Retry the last failed deployment" - List recent failed executions, retry
- "Abort all stuck executions" - List running/waiting executions, interrupt each with `interrupt_type: "AbortAll"`
- "Stop execution abc123" - Interrupt the specific execution with `interrupt_type: "AbortAll"`

## Performance Notes

- Always confirm the pipeline identifier and required inputs before triggering execution. A failed execution due to missing inputs wastes time.
- When monitoring executions, wait for terminal status (Success, Failed, Aborted) before reporting results. Do not assume intermediate states are final.
- If an execution fails, gather full error context from logs before suggesting fixes. Do not guess at root causes.

## Troubleshooting

### Pipeline Won't Start
- Check delegate availability with `harness_status`
- Validate all required inputs have values
- Test connector credentials with `harness_execute` (resource_type: "connector", action: "test_connection")

### Missing Inputs
- Use `harness_get` on the pipeline to see all `<+input>` fields
- Check input sets for pre-configured values

### Execution Stuck
- Check for pending approvals with `harness_list` (resource_type: "approval_instance")
- Check delegate status with `harness_status`
- Abort stuck executions with `harness_execute` (resource_type: "execution", action: "interrupt", interrupt_type: "AbortAll")
