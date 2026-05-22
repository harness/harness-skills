---
name: manage-feature-flags
description: >-
  Manage Harness Feature Flags (FME / Split.io) via MCP. List flags by workspace,
  get flag details, create flags, kill or restore flags per environment, archive
  or unarchive flags, and delete flags. Use when asked to create a feature flag,
  kill/restore a flag, list flags, check flag status, enable or disable a feature,
  or manage feature rollouts. Trigger phrases: feature flag, kill switch, restore
  flag, create flag, feature rollout, archive flag, FME flag.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2). Feature Flags are served by the FME (Split.io) backend — operations use the `fme_feature_flag` resource type and require a `workspace_id`.
---

# Manage Feature Flags

Create, list, kill/restore, and delete Harness FME (Split.io-backed) Feature Flags via MCP.

## Prerequisites

FME flags are workspace-scoped (not project-scoped). You must discover the `workspace_id` and `environment_id` before most operations.

### Step 0a: List workspaces

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_workspace"
```

### Step 0b: List environments (per workspace)

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_environment"
  workspace_id: "<workspace_id>"
```

## Instructions

### Step 1: List Existing Flags

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag"
  workspace_id: "<workspace_id>"
```

Filter by name, tags, or rollout status:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag"
  workspace_id: "<workspace_id>"
  name: "dark_mode"
  tags: "ui"
  rollout_status_id: "<uuid>"   # discover via fme_rollout_status
```

### Step 2: Get Flag Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_feature_flag"
  workspace_id: "<workspace_id>"
  feature_flag_name: "<flag_name>"
```

For per-environment targeting/state, use `fme_feature_flag_definition` and pass `environment_id`.

### Step 3: Create a Flag

```
Call MCP tool: harness_create
Parameters:
  resource_type: "fme_feature_flag"
  workspace_id: "<workspace_id>"
  traffic_type_id: "<traffic_type_id>"   # required by FME
  body:
    name: "dark_mode"
    description: "Enable dark mode UI theme"
    tags: ["ui", "rollout"]
```

### Step 4: Kill or Restore a Flag (per environment)

Kill (turn the flag OFF in one environment):

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "fme_feature_flag"
  action: "kill"
  workspace_id: "<workspace_id>"
  feature_flag_name: "<flag_name>"
  environment_id: "<environment_id>"
```

Restore (re-enable after a kill):

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "fme_feature_flag"
  action: "restore"
  workspace_id: "<workspace_id>"
  feature_flag_name: "<flag_name>"
  environment_id: "<environment_id>"
```

### Step 5: Archive / Unarchive a Flag

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "fme_feature_flag"
  action: "archive"      # or "unarchive"
  workspace_id: "<workspace_id>"
  feature_flag_name: "<flag_name>"
```

Archiving is subject to OPA policy checks (returns 409 on violation). Unarchive returns 409 if dependent objects exist.

### Step 6: Update Flag Metadata

```
Call MCP tool: harness_update
Parameters:
  resource_type: "fme_feature_flag"
  workspace_id: "<workspace_id>"
  feature_flag_name: "<flag_name>"
  body:
    description: "Updated description"
    tags: ["ui", "ga"]
```

### Step 7: Delete a Flag

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "fme_feature_flag"
  workspace_id: "<workspace_id>"
  feature_flag_name: "<flag_name>"
```

## FME Resource Types Reference

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `fme_workspace` | list | List FME workspaces |
| `fme_environment` | list | List FME environments (per workspace) |
| `fme_feature_flag` | list, get, create, update, delete, execute(kill/restore/archive/unarchive) | Flag metadata at workspace scope |
| `fme_feature_flag_definition` | list, get | Per-environment rollout targeting and state |
| `fme_rollout_status` | list | Discover valid `rollout_status_id` values |
| `fme_rule_based_segment` | list, get | Rule-based segments |
| `fme_rule_based_segment_definition` | list, get, execute(enable/disable/change_request) | Segment definition per environment |

## Examples

- "Create a feature flag for dark mode" — Create `fme_feature_flag` with `body: { name: "dark_mode", ... }`
- "Kill the experimental-search flag in production" — Execute `kill` with production `environment_id`
- "Restore the new-checkout flag in staging" — Execute `restore` with staging `environment_id`
- "List all feature flags in my workspace" — List `fme_feature_flag` for workspace
- "Archive the stale beta_banner flag" — Execute `archive`

## Performance Notes

- Always discover `workspace_id` and `environment_id` before kill/restore — wrong environment can affect production.
- List existing flags before creating to avoid duplicates.
- FME does not expose a single "toggle" action — use `kill` (off) and `restore` (on) per environment.

## Troubleshooting

### Flag won't kill/restore
- `environment_id` is required — kills are per-environment
- Confirm `feature_flag_name` is exact (case-sensitive)
- Verify the flag lives in the specified `workspace_id`

### Flag Not Found
- FME flags are workspace-scoped — confirm the correct `workspace_id`
- Use `harness_list` with `resource_type: "fme_feature_flag"` and no filters to see all flags in the workspace

### Archive fails with 409
- An OPA policy may block archival — review governance policies
- For unarchive, remove dependent segments/targeting before retrying
