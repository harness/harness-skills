---
name: manage-freeze-windows
description: >-
  Manage Harness deployment freeze windows via MCP. Create, list, get, update, and delete project-level
  freeze windows; toggle them Enabled/Disabled; and get or enable/disable the project-level global
  freeze. Use when asked about freeze windows, deployment freezes, change freezes, release blackouts,
  maintenance windows, holiday freezes, or to pause deployments. Trigger phrases: freeze window,
  deployment freeze, change freeze, release blackout, maintenance window, holiday freeze, pause
  deployments, block pipeline execution, global freeze.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP server (harness-mcp-v2)
---

# Manage Freeze Windows

Create and toggle Harness deployment freeze windows via MCP. A freeze window blocks pipeline executions within a time window so you can enforce change freezes for releases, holidays, or maintenance.

## MCP Tools Used

| Tool | Resource Type | Purpose |
|------|---------------|---------|
| `harness_list` | `freeze_window` | List project freeze windows, filter by status / time / keyword |
| `harness_get` | `freeze_window` | Get a single freeze window by identifier |
| `harness_create` | `freeze_window` | Create a freeze window from YAML |
| `harness_update` | `freeze_window` | Replace an existing freeze window's YAML definition |
| `harness_delete` | `freeze_window` | Delete a freeze window |
| `harness_execute` (action: `toggle_status`) | `freeze_window` | Enable / disable one or more freeze windows in bulk |
| `harness_get` | `global_freeze` | Get the current project-level global freeze state |
| `harness_execute` (action: `manage`) | `global_freeze` | Enable or disable the project global freeze from YAML |
| `harness_schema` | `freeze_window` | Exact JSON Schema for the `create` / `update` body |

Both resources are **project-scoped** — every call needs `org_id` and `project_id`.

## Freeze Window YAML

Create/update bodies take a **raw freeze YAML string** passed as `body: { yaml: "<yaml string>" }`. The MCP server forwards it to the Harness API with `Content-Type: application/yaml`.

```yaml
freeze:
  name: Q4 Release Freeze
  identifier: q4_release_freeze
  entityConfigs:
    - name: All Services
      entities:
        - type: Service
          filterType: All
        - type: Environment
          filterType: All
        - type: EnvType
          filterType: All
        - type: Org
          filterType: All
        - type: Project
          filterType: All
  status: Enabled                     # Enabled | Disabled
  description: "Change freeze for Q4 GA release"
  windows:
    - timeZone: America/Los_Angeles
      startTime: 2026-12-20 00:00 AM
      duration: 14d                   # e.g. 2h, 3d, 14d, 4w
      recurrence:
        type: Yearly                  # Daily | Weekly | Monthly | Yearly (optional)
  notificationRules: []
```

Use `harness_schema(resource_type="freeze_window")` if you want the authoritative field list. Key rules:
- `identifier` matches `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`.
- `entityConfigs` is required and must match at least one deployment scope.
- `windows[].duration` accepts `h`, `d`, `w` suffixes (no seconds).
- `windows[].startTime` format: `YYYY-MM-DD HH:mm AM|PM` in the given `timeZone`.

## Instructions

### Step 1: List existing freeze windows

```
Call MCP tool: harness_list
Parameters:
  resource_type: "freeze_window"
  org_id: "<organization>"
  project_id: "<project>"
  freeze_status: "Enabled"     # optional: Enabled | Disabled
  search_term: "release"       # optional: keyword filter
  start_time: 1735689600000    # optional: epoch ms lower bound
  end_time: 1738368000000      # optional: epoch ms upper bound
```

### Step 2: Get a freeze window by identifier

```
Call MCP tool: harness_get
Parameters:
  resource_type: "freeze_window"
  resource_id: "<freeze_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 3: Create a freeze window

```
Call MCP tool: harness_create
Parameters:
  resource_type: "freeze_window"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    yaml: |
      freeze:
        name: Holiday Freeze
        identifier: holiday_freeze
        entityConfigs:
          - name: All Services
            entities:
              - type: Service
                filterType: All
              - type: Environment
                filterType: All
              - type: EnvType
                filterType: All
        status: Enabled
        windows:
          - timeZone: America/Los_Angeles
            startTime: 2026-12-22 06:00 PM
            duration: 10d
```

### Step 4: Update a freeze window

`harness_update` performs a **full replace** of the YAML — include every field you want to keep.

```
Call MCP tool: harness_update
Parameters:
  resource_type: "freeze_window"
  resource_id: "<freeze_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    yaml: "<full updated freeze YAML>"
```

### Step 5: Toggle status for one or many freeze windows

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "freeze_window"
  action: "toggle_status"
  org_id: "<organization>"
  project_id: "<project>"
  status: "Enabled"                    # Enabled | Disabled
  body:
    freeze_ids: ["holiday_freeze", "q4_release_freeze"]
```

Pass an array of identifiers — toggle works in bulk. Use this instead of editing the YAML when you just need to flip enabled/disabled.

### Step 6: Delete a freeze window

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "freeze_window"
  resource_id: "<freeze_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 7: Read the project global freeze

```
Call MCP tool: harness_get
Parameters:
  resource_type: "global_freeze"
  org_id: "<organization>"
  project_id: "<project>"
```

Returns `{ status: "Enabled" | "Disabled", ... }`. The global freeze is a **singleton** — there is exactly one per project scope, no `resource_id` needed.

### Step 8: Enable or disable the global freeze

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "global_freeze"
  action: "manage"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    yaml: |
      freeze:
        name: Project Global Freeze
        identifier: _global_
        status: Enabled              # Enabled | Disabled
        entityConfigs:
          - name: All
            entities:
              - type: Service
                filterType: All
              - type: Environment
                filterType: All
              - type: EnvType
                filterType: All
        windows:
          - timeZone: UTC
            startTime: 2026-12-22 00:00 AM
            duration: 14d
```

The global freeze takes effect immediately when `status: Enabled` — pipelines at the project scope will start being blocked.

## Examples

### Create a two-week holiday freeze

```
/manage-freeze-windows
Create a holiday freeze window called "Winter 2026 Shutdown" in org default, project payments,
covering all services and environments, from 2026-12-22 6pm PT for 14 days.
```

### Check what's currently blocking deployments

```
/manage-freeze-windows
List every Enabled freeze window in project "payments" and also show me whether the project global
freeze is on.
```

### Bulk-disable all freezes for a hotfix

```
/manage-freeze-windows
Disable all Enabled freeze windows in project "payments" temporarily so I can ship a hotfix.
```

### Turn on the project global freeze

```
/manage-freeze-windows
Enable the global freeze for project "payments" right now with a 4-hour duration in UTC —
we're running incident response.
```

### Audit scheduled freezes for a release

```
/manage-freeze-windows
Show me every freeze window in project "release-ops" whose start_time is in the next 30 days.
```

## Performance Notes

- **Use `harness_schema(resource_type="freeze_window")`** to get the authoritative body schema before drafting new YAML — field names are case-sensitive and several fields (`entityConfigs`, `windows`, `notificationRules`) are required.
- **Prefer `toggle_status` over `update`** when you only want to flip enabled/disabled — it avoids re-sending the full YAML and works in bulk.
- **Freeze windows are project-scoped** — a window in project A does not affect project B. To freeze the whole org, create a freeze window in every project (or use `global_freeze` per project).
- **`global_freeze` is a singleton per project** — there is no list/create/delete. `harness_get` reads it, `harness_execute(action="manage")` flips it on or off via YAML.
- **Time zones matter** — `timeZone` is an IANA name (e.g. `America/Los_Angeles`, `Europe/Berlin`), not an offset. The server interprets `startTime` in that zone.
- **Overlapping windows compound** — Harness evaluates every Enabled freeze window; if any match, the deployment is blocked. Disable rather than delete if you may re-enable later.

## Troubleshooting

### `body must include yaml (freeze YAML string with 'freeze:' root)`

You passed the body as a plain YAML string or JSON object — the `bodyBuilder` expects the outer shape `body: { yaml: "<yaml string>" }`. Wrap your YAML string in a `yaml` key.

### `INVALID_REQUEST` on create

- Check that `entityConfigs` is present and non-empty. `entityConfigs[].entities` must include at least `Service` and `Environment` (or `EnvType`) filters.
- Verify `identifier` matches `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$` — hyphens and dots are not allowed in identifiers.
- `duration` values use suffixes (`2h`, `3d`, `14d`, `4w`) — raw numbers without a suffix are rejected.

### `DUPLICATE_IDENTIFIER`

A freeze window with that identifier already exists at the same project scope. Either `harness_update` the existing one or pick a new identifier.

### Toggle fails with "body must include freeze_ids"

`toggle_status` expects `body.freeze_ids` as an array of strings, even for a single window. Pass `body: { freeze_ids: ["my_freeze"] }`, not `body: "my_freeze"` or `resource_id: "my_freeze"`.

### Deployments still run during an Enabled freeze

- Confirm the freeze `status` is `Enabled` and not `Disabled` — `harness_get` will show the current status.
- Check the `windows[].startTime` and `duration` — if the current time is outside the window, the freeze is scheduled but not active.
- Verify `entityConfigs` actually cover the service/environment you're deploying to — a freeze with `Service: filterType: NotEquals / entityRefs: [payments]` will not block `payments`.
- Global project freeze and named freeze windows are independent — either one being `Disabled` is enough to let a deployment through if that's the only one matching.

### Can't delete a freeze window

Active (currently firing) freeze windows cannot be deleted in some account tiers — `Disabled` them first via `toggle_status` then `harness_delete`.
