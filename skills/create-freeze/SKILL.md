---
name: create-freeze
description: >-
  Generate Harness Deployment Freeze YAML and create them via MCP. Configure time-based freeze windows
  that block deployments during maintenance, holidays, or compliance periods. Supports service, environment,
  and pipeline scoping with recurring schedules (daily, weekly, monthly, yearly). Use when asked to create
  a freeze, block deployments, set up a maintenance window, or configure a change freeze. Trigger phrases:
  create freeze, deployment freeze, freeze window, maintenance window, change freeze, blackout window.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Freeze

Generate Harness Deployment Freeze YAML and push via MCP.

## Freeze Structure

```yaml
freeze:
  identifier: holiday_freeze
  name: Holiday Freeze
  status: Enabled
  orgIdentifier: default
  projectIdentifier: my_project
  entityConfigs:
    - name: All Production
      entities:
        - type: Service
          filterType: All
        - type: EnvType
          filterType: Equals
          entityRefs:
            - Production
  windows:
    - timeZone: America/New_York
      startTime: 2024-12-23 00:00 AM
      endTime: 2024-12-26 11:59 PM
```

## Instructions

### Step 1: Identify Requirements

- What period needs to be frozen?
- Which services/environments are affected?
- Is it recurring (daily, weekly, monthly)?
- What scope? (Account, Org, Project)

### Step 2: Generate Freeze YAML

Use the structure above. Key fields:

- `status`: `Enabled` or `Disabled`
- `entityConfigs`: What to freeze (services, environments, pipelines)
- `windows`: When to freeze (time range + optional recurrence)

### Step 3: Create via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "freeze"
  org_id: "<organization>"
  project_id: "<project>"
  body: <freeze YAML>
```

To update or disable:

```
Call MCP tool: harness_update
Parameters:
  resource_type: "freeze"
  resource_id: "<freeze_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: <updated freeze YAML>
```

## Entity Types

| Type | Description | Filter Options |
|------|-------------|----------------|
| `Service` | Services | All, Equals, NotEquals |
| `Env` | Specific environments | All, Equals, NotEquals |
| `EnvType` | Environment types (Production, PreProduction) | All, Equals |
| `Pipeline` | Pipelines | All, Equals, NotEquals |

## Window Configuration

Duration format: `30m`, `2h`, `1d`, `1w`

Recurrence types: `Daily`, `Weekly`, `Monthly`, `Yearly`

```yaml
windows:
  - timeZone: UTC
    startTime: 2024-01-06 00:00 AM
    endTime: 2024-01-07 11:59 PM
    recurrence:
      type: Weekly
      spec:
        until: 2024-12-31 11:59 PM
```

## Examples

- "Create a holiday freeze for production" - Freeze with EnvType=Production, fixed date range
- "Block weekend deployments" - Recurring weekly freeze on Saturday-Sunday
- "Freeze the payment service for 4 hours" - Service-specific freeze with duration
- "Set up a monthly maintenance window" - Recurring monthly freeze

## Performance Notes

- Verify freeze window times are in the correct timezone before creating.
- Confirm scope filters match the intended pipelines, services, or environments.
- Check for existing overlapping freeze windows to avoid conflicts.

## Troubleshooting

### Freeze Not Blocking Deployments
- Verify `status: Enabled`
- Check timezone and start/end times
- Confirm entity filters match the target services/environments

### Freeze Blocking Too Broadly
- `filterType: All` affects everything -- use `Equals` with specific `entityRefs` to narrow scope
- Account-level freezes cascade to all orgs and projects

### Validation Errors
- Datetime format must be `YYYY-MM-DD HH:MM AM/PM`
- Use IANA timezones (e.g., `America/New_York`, not `EST`)
- Identifiers must match `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
