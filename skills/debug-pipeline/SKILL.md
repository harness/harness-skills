---
name: debug-pipeline
description: >-
  Diagnose Harness pipeline execution failures and suggest fixes via MCP tools. Analyzes execution logs,
  identifies root causes across build failures, infrastructure errors, configuration issues, deployment
  problems, and timeouts. Use when asked to debug a pipeline, investigate a failure, find out why a build
  failed, analyze pipeline errors, or check execution logs. Trigger phrases: debug pipeline, pipeline
  failed, why did my build fail, analyze failure, pipeline error, execution logs, fix pipeline.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Debug Pipeline

Diagnose pipeline execution failures and suggest fixes via MCP.

## Instructions

### Step 1: Quick Diagnosis (Preferred)

Use the dedicated diagnosis tool first:

```
Call MCP tool: harness_diagnose
Parameters:
  pipeline_id: "<pipeline_identifier>"   # or execution_id or url
  include_logs: true
  project_id: "<project>"
```

This retrieves execution details, logs, stage/step breakdowns, and failure details in one call.

### Step 2: Project Health Overview

Check overall project health for context:

```
Call MCP tool: harness_status
Parameters:
  org_id: "<organization>"
  project_id: "<project>"
```

Shows recent failed executions, running executions, and deployment activity.

### Step 3: Find Failed Executions (if needed)

```
Call MCP tool: harness_list
Parameters:
  resource_type: "execution"
  org_id: "<organization>"
  project_id: "<project>"
  search_term: "<pipeline name>"
```

### Step 4: Get Execution Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "execution"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 5: Get Execution Logs

```
Call MCP tool: harness_get
Parameters:
  resource_type: "execution_log"
  resource_id: "<execution_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 6: Get Pipeline Definition

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

## Analysis Framework

Categorize errors and provide targeted fixes:

### Build Failures
- Missing dependencies - Check package.json/requirements.txt
- Compilation errors - Review recent code changes
- Docker build failures - Check Dockerfile and base image

### Infrastructure Errors
- "No delegate available" - Check delegate status, verify tags match
- Connector failures - Rotate credentials, test connection
- Resource limits - Check cloud quotas and limits

### Configuration Errors
- "Secret not found" - Verify secret exists at correct scope (account/org/project)
- "Could not resolve expression" - Check expression syntax
- "Connector not found" - Verify connectorRef identifier

### Deployment Errors
- ImagePullBackOff - Check registry credentials and image tag
- CrashLoopBackOff - Check container logs, resource limits
- Readiness probe failed - Review probe configuration

### Timeout Errors
- Step/stage exceeded timeout - Increase timeout or optimize
- Delegate task queued too long - Scale up delegates

### Artifact Errors
- "Artifact not found" - Verify artifact path, check upstream build

## Response Format

```
## Pipeline Failure Analysis

**Pipeline:** <name>
**Execution:** <id>
**Failed At:** <timestamp>

### Failure Summary
**Stage:** <failed_stage>
**Step:** <failed_step>
**Error:** <error message>

### Root Cause
<explanation>

### Fix
**Immediate:** <specific steps>
**Prevention:** <how to avoid in future>
```

## Examples

- "Why did my build pipeline fail?" - Use `harness_diagnose` with pipeline_id
- "Debug execution abc123" - Use `harness_diagnose` with execution_id
- "Show me recent failures" - Use `harness_status` then drill into failures
- "Analyze the pipeline at https://app.harness.io/..." - Pass URL directly to `harness_diagnose`

## Performance Notes

- Take your time analyzing logs thoroughly. Read complete error messages and stack traces before diagnosing.
- Check all failed steps, not just the first one. Multiple failures may share a root cause or reveal a dependency chain.
- Quality of diagnosis is more important than speed. A wrong diagnosis wastes more time than a thorough one.

## Troubleshooting

### Logs Not Available
- Logs expire based on retention settings
- Very recent executions may have delayed logs
- Aborted executions may not have complete logs

### Cannot Find Execution
- Verify org/project scope
- Remove filters to see all executions
- Check RBAC permissions

### MCP Connection Issues
- Verify MCP server is running and connected
- Check API key validity
- Ensure required toolsets (pipelines, logs) are enabled
