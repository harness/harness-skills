---
name: manage-delegates
description: >-
  Monitor and manage Harness Delegates via MCP. List delegates and check health status, manage delegate
  registration tokens (create, revoke, delete), and find which delegates are associated with a token.
  Use when asked about delegate status, delegate health, delegate connectivity, delegate tokens, or
  troubleshooting delegate issues. Trigger phrases: delegate status, delegate health, list delegates,
  delegate token, delegate connectivity, delegate troubleshooting, delegate down.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  summary: Monitor delegate health and manage registration tokens
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage Delegates

Monitor delegate health and manage registration tokens via MCP.

## Instructions

### Step 1: List Delegates

List all delegates in the account to check health and connectivity:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "delegate"
```

This returns all delegates with their status, version, connectivity, and last heartbeat. Delegates are account-scoped -- no org/project needed.

### Step 2: List Delegate Tokens

```
Call MCP tool: harness_list
Parameters:
  resource_type: "delegate_token"
  org_id: "<organization>"
  project_id: "<project>"
```

Filter by name or status:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "delegate_token"
  name: "prod-token"
  status: "ACTIVE"
```

### Step 3: Get Token Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "delegate_token"
  resource_id: "<token_name>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 4: Create a Token

```
Call MCP tool: harness_create
Parameters:
  resource_type: "delegate_token"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    name: "prod-delegate-token"
```

### Step 5: Find Delegates for a Token

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "delegate_token"
  action: "get_delegates"
  resource_id: "<token_name>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 6: Revoke a Token

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "delegate_token"
  action: "revoke"
  resource_id: "<token_name>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 7: Delete a Token

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "delegate_token"
  resource_id: "<token_name>"
  org_id: "<organization>"
  project_id: "<project>"
```

## Resource Types

| Resource Type | Scope | Operations | Description |
|--------------|-------|-----------|-------------|
| `delegate` | Account | list | List delegates with health status |
| `delegate_token` | Project | list, get, create, delete + revoke, get_delegates actions | Manage registration tokens |

## Examples

- "Are all delegates healthy?" -- List delegates, check status and last heartbeat
- "Create a new delegate token for the staging project" -- Create token with project scope
- "Which delegates are using the prod-token?" -- Execute get_delegates action on the token
- "Revoke the old registration token" -- Execute revoke action
- "Show me all active delegate tokens" -- List tokens filtered by status ACTIVE

## Performance Notes

- When diagnosing delegate issues, check both the delegate list (for health/heartbeat) and the token status (for auth). A delegate showing as disconnected may have a revoked token.
- Always verify delegate connectivity before troubleshooting pipeline failures -- many execution errors stem from unavailable delegates.

## Troubleshooting

### Delegate Shows Disconnected
1. Check the delegate's last heartbeat timestamp -- if stale, the delegate process may be down
2. Verify the delegate token is ACTIVE (not REVOKED)
3. Check network connectivity between the delegate host and Harness SaaS

### Pipeline Fails with "No Delegates Available"
1. List delegates to confirm at least one is connected and healthy
2. Check if the pipeline uses a delegate selector that doesn't match any active delegate
3. Verify the delegate has the required tools installed (kubectl, helm, docker, etc.)

### Token Issues
- Tokens are project-scoped -- a token created in project A cannot register delegates for project B
- Revoking a token disconnects all delegates registered with it
- Deleted tokens cannot be recovered -- create a new one and re-register delegates
