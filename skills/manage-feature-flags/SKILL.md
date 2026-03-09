---
name: manage-feature-flags
description: >-
  Manage Harness Feature Flags via MCP. Create boolean or multivariate flags, list flags by project
  or workspace, get flag details with environment state, toggle flags on/off per environment, and
  delete flags. Use when asked to create a feature flag, toggle a flag, list flags, check flag status,
  enable or disable a feature, or manage feature rollouts. Trigger phrases: feature flag, toggle flag,
  create flag, enable feature, disable feature, flag status, feature rollout, kill switch.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage Feature Flags

Create, list, toggle, and delete Harness Feature Flags via MCP.

## Instructions

### Step 1: List Existing Flags

```
Call MCP tool: harness_list
Parameters:
  resource_type: "feature_flag"
  org_id: "<organization>"
  project_id: "<project>"
```

Filter by name or environment:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "feature_flag"
  org_id: "<organization>"
  project_id: "<project>"
  name: "dark_mode"
  environment: "production"
```

### Step 2: Get Flag Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "feature_flag"
  resource_id: "<flag_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  environment: "<environment>"
```

### Step 3: Create a Flag

```
Call MCP tool: harness_create
Parameters:
  resource_type: "feature_flag"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    identifier: "dark_mode"
    name: "Dark Mode"
    kind: "boolean"
    permanent: false
    description: "Enable dark mode UI theme"
```

Flag kinds:
- `boolean` -- simple on/off toggle
- `multivariate` -- multiple variations (e.g., string, number, JSON)

### Step 4: Toggle a Flag

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "feature_flag"
  action: "toggle"
  resource_id: "<flag_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  enable: true
  environment: "production"
```

Set `enable: true` to turn on, `enable: false` to turn off. The `environment` parameter is required.

### Step 5: Delete a Flag

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "feature_flag"
  resource_id: "<flag_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

## FME Resources

For Split.io-backed Feature Management & Experimentation (FME), use these additional resource types:

| Resource Type | Operations | Description |
|--------------|-----------|-------------|
| `fme_workspace` | list | List FME workspaces |
| `fme_environment` | list | List FME environments |
| `fme_feature_flag` | list, get | List/get flags by workspace (no environment required) |

## Examples

- "Create a feature flag for dark mode" -- Create boolean flag with identifier `dark_mode`
- "Turn on the new-checkout flag in staging" -- Toggle with `enable: true`, `environment: "staging"`
- "Kill the experimental-search feature in production" -- Toggle with `enable: false`, `environment: "production"`
- "List all feature flags in the payments project" -- List with project scope
- "Is the beta-dashboard flag enabled?" -- Get flag details with environment

## Performance Notes

- Verify the flag identifier and environment before toggling. Toggling the wrong flag can cause production issues.
- List existing flags before creating to avoid duplicates.
- Confirm the flag type (boolean vs. multivariate) matches the intended use case.

## Troubleshooting

### Flag Not Toggling
- The `environment` parameter is required for toggle -- specify which environment to target
- Verify the flag identifier is correct (case-sensitive)
- Check that the flag exists in the target project

### Flag Not Found
- Identifiers are project-scoped -- confirm the correct org_id and project_id
- Use `harness_list` without filters to see all flags, then narrow down

### Boolean vs Multivariate
- Use `boolean` for simple on/off flags
- Use `multivariate` when you need multiple string/number/JSON variations
