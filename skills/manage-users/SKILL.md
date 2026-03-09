---
name: manage-users
description: >-
  Manage Harness users, user groups, and service accounts via MCP. List and search users, create and
  manage user groups for team-based access, create service accounts for API automation, and view
  available permissions. Use when asked to list users, create a user group, manage service accounts,
  check who has access, or set up team permissions. Do NOT use for role assignments or resource groups
  (use manage-roles instead). Trigger phrases: list users, user group, service account, who has access,
  team permissions, add user to group, create service account.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage Users

Manage users, user groups, and service accounts via MCP.

## Instructions

### Step 1: List Users

```
Call MCP tool: harness_list
Parameters:
  resource_type: "user"
  search_term: "<name or email>"
```

Users are account-scoped. Use `search_term` to filter by name or email.

### Step 2: Get User Details

```
Call MCP tool: harness_get
Parameters:
  resource_type: "user"
  resource_id: "<user_id>"
```

### Step 3: Manage User Groups

List groups:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "user_group"
  org_id: "<organization>"
  project_id: "<project>"
  search_term: "<group name>"
```

Get group details:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "user_group"
  resource_id: "<group_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

Create a group:

```
Call MCP tool: harness_create
Parameters:
  resource_type: "user_group"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    identifier: "backend_team"
    name: "Backend Team"
    description: "Backend engineering team"
    users:
      - "<user_id_1>"
      - "<user_id_2>"
```

Delete a group:

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "user_group"
  resource_id: "<group_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 4: Manage Service Accounts

List service accounts:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "service_account"
  org_id: "<organization>"
  project_id: "<project>"
```

Create a service account:

```
Call MCP tool: harness_create
Parameters:
  resource_type: "service_account"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    identifier: "ci_bot"
    name: "CI Bot"
    description: "Service account for CI pipeline automation"
    email: "ci-bot@harness.io"
```

Delete a service account:

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "service_account"
  resource_id: "<service_account_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 5: List Available Permissions

```
Call MCP tool: harness_list
Parameters:
  resource_type: "permission"
```

This returns all platform permissions. Use this to understand what permissions can be assigned via roles.

## Resource Types

| Resource Type | Scope | Operations | Description |
|--------------|-------|-----------|-------------|
| `user` | Account | list, get | Platform users (read-only) |
| `user_group` | Project | list, get, create, delete | User groups for RBAC |
| `service_account` | Project | list, get, create, delete | API automation accounts |
| `permission` | Account | list | Available permissions (read-only) |

## Relationship to /manage-roles

This skill manages **principals** (users, groups, service accounts). Use `/manage-roles` to assign **roles** and **resource groups** to these principals:

1. `/manage-users` -- Create the user group or service account
2. `/manage-roles` -- Assign a role + resource group to that principal

## Examples

- "List all users in the account" -- List users with no filter
- "Find user john.doe" -- List users with search_term "john.doe"
- "Create a user group for the platform team" -- Create user_group with member user IDs
- "Create a service account for CI automation" -- Create service_account
- "What permissions are available?" -- List permissions
- "Delete the old test-bot service account" -- Delete service_account

## Performance Notes

- Verify user email addresses and group identifiers before making changes.
- List existing groups and service accounts before creating to avoid duplicates.
- For service accounts, confirm the token expiry and scope match the intended usage.

## Troubleshooting

### User Not Found
- Users are account-scoped -- no org/project needed
- Try searching by email address instead of display name
- User must be invited to the account before they appear

### Cannot Create User
- Users cannot be created via API -- they must be invited through the Harness UI or SCIM provisioning
- Use user groups and service accounts for programmatic access

### Service Account Has No Access
- Creating a service account alone does not grant permissions
- Use `/manage-roles` to assign a role to the service account
- Generate an API key for the service account via the Harness UI
