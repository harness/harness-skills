---
name: gitops-status
description: Monitor GitOps application health, sync status, and manage ArgoCD deployments via Harness MCP. Use when user says "gitops status", "argocd status", "application sync", "gitops health", "is my app in sync", or asks about GitOps applications.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# GitOps Status

Monitor GitOps application health and manage sync operations via MCP.

## Instructions

### Step 1: Overview Dashboard

```
Call MCP tool: harness_get
Parameters:
  resource_type: "gitops_dashboard"
```

### Step 2: List Applications

```
Call MCP tool: harness_list
Parameters:
  resource_type: "gitops_application"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 3: Get Application Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "gitops_application"
  resource_id: "<app_name>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 4: Check Resource Tree

```
Call MCP tool: harness_get
Parameters:
  resource_type: "gitops_app_resource_tree"
  resource_id: "<app_name>"
```

### Step 5: Get Pod Logs (Debugging)

```
Call MCP tool: harness_get
Parameters:
  resource_type: "gitops_pod_log"
  resource_id: "<pod_name>"
```

### Step 6: Check Events

```
Call MCP tool: harness_list
Parameters:
  resource_type: "gitops_app_event"
```

### Step 7: Trigger Sync

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "gitops_application"
  action: "sync"
  resource_id: "<app_name>"
  org_id: "<organization>"
  project_id: "<project>"
```

## Additional Resource Types

```
Call MCP tool: harness_list
Parameters:
  resource_type: "gitops_agent"        # ArgoCD agents
  resource_type: "gitops_cluster"      # Connected clusters
  resource_type: "gitops_repository"   # Git repositories
  resource_type: "gitops_applicationset"  # ApplicationSets
  resource_type: "gitops_managed_resource"  # K8s resources
```

## GitOps Resource Types

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `gitops_agent` | list, get | ArgoCD instances |
| `gitops_application` | list, get, sync | Applications |
| `gitops_applicationset` | list, get | ApplicationSets |
| `gitops_cluster` | list, get | K8s clusters |
| `gitops_repository` | list, get | Git repositories |
| `gitops_app_event` | list | Application events |
| `gitops_pod_log` | get | Pod logs |
| `gitops_managed_resource` | list | K8s resources |
| `gitops_app_resource_tree` | get | Resource tree |
| `gitops_dashboard` | get | Overview dashboard |

## Application Health States

- **Healthy** - All resources running and passing health checks
- **Degraded** - Some resources failing health checks
- **Progressing** - Resources being created/updated
- **Suspended** - Application suspended
- **Missing** - Resources not found
- **Unknown** - Health status cannot be determined

## Sync States

- **Synced** - Live state matches desired state in Git
- **OutOfSync** - Live state differs from Git (needs sync)
- **Unknown** - Sync status cannot be determined

## Examples

- "Show me all GitOps applications" - List gitops_application
- "Is the api-gateway in sync?" - Get gitops_application, check sync status
- "Sync the payment-service" - Execute sync action
- "Get pod logs for failing service" - Get gitops_pod_log
- "Show the resource tree for my app" - Get gitops_app_resource_tree

## Performance Notes

- Check all applications in the requested scope before summarizing health status.
- For out-of-sync applications, examine the resource tree to identify the specific drift.
- Gather pod logs for failing resources before diagnosing issues.

## Troubleshooting

### Application OutOfSync
- Check git repo for recent changes
- Verify auto-sync is enabled if expected
- Review sync errors in events
- Trigger manual sync if needed

### Application Degraded
- Check pod logs for application errors
- Review resource tree for failing pods
- Check resource limits and quotas

### Agent Not Connected
- Verify ArgoCD agent is running
- Check network connectivity
- Review agent configuration
