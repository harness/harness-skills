---
name: chaos-experiment
description: Create and manage chaos experiments using Harness Chaos Engineering via MCP. Run resilience tests like pod deletion, CPU stress, and network faults. Use when user says "chaos experiment", "chaos engineering", "resilience test", "chaos test", or wants to test system reliability.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Chaos Experiment

Create and manage chaos experiments using Harness Chaos Engineering via MCP.

## Instructions

### Step 1: Check Infrastructure

```
Call MCP tool: harness_list
Parameters:
  resource_type: "chaos_infrastructure"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Browse Templates

```
Call MCP tool: harness_list
Parameters:
  resource_type: "chaos_experiment_template"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 3: List Existing Experiments

```
Call MCP tool: harness_list
Parameters:
  resource_type: "chaos_experiment"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 4: Create Experiment

```
Call MCP tool: harness_create
Parameters:
  resource_type: "chaos_experiment"
  org_id: "<organization>"
  project_id: "<project>"
  body: <experiment definition>
```

### Step 5: Run Experiment

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "chaos_experiment"
  action: "run"
  resource_id: "<experiment_id>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 6: Monitor Results

```
Call MCP tool: harness_list
Parameters:
  resource_type: "chaos_experiment_run"
  org_id: "<organization>"
  project_id: "<project>"
```

Get specific run details:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "chaos_experiment_run"
  resource_id: "<run_id>"
```

### Step 7: Check Probes

```
Call MCP tool: harness_list
Parameters:
  resource_type: "chaos_probe"
  org_id: "<organization>"
  project_id: "<project>"
```

## Common Experiment Types

- **Pod Delete** - Kill pods to test recovery
- **Pod CPU Hog** - Stress CPU to test throttling
- **Pod Memory Hog** - Consume memory to test OOM handling
- **Pod Network Loss** - Simulate network failures
- **Pod Network Latency** - Add artificial latency
- **Node Drain** - Drain K8s nodes
- **EC2 Stop** - Stop AWS EC2 instances
- **ECS Task Stop** - Stop ECS tasks

## Chaos Resource Types

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `chaos_experiment` | list, get, create, update, delete, run | Experiments |
| `chaos_experiment_run` | list, get | Run history/results |
| `chaos_experiment_template` | list, get | Pre-built templates |
| `chaos_infrastructure` | list, get | Target infrastructure |
| `chaos_probe` | list, get | Health probes |

## Examples

- "Show me all chaos experiments" - List chaos_experiment
- "Create a pod-delete experiment for checkout-service" - Create chaos_experiment
- "Run the weekly resilience test" - Execute run action
- "What were the results of the last chaos run?" - Get chaos_experiment_run

## Troubleshooting

### Experiment Won't Run
- Verify chaos infrastructure is connected and active
- Check target application/namespace exists
- Ensure RBAC permissions for chaos operations

### Probes Failing
- Check probe endpoints are accessible
- Verify probe timeout settings
- Review probe type matches expected behavior
