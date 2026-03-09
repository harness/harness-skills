---
name: manage-roles
description: >-
  Manage Harness RBAC roles, role assignments, permissions, and resource groups via MCP v2 tools.
  List, create, update, and delete custom roles. View role assignments and permissions for users,
  groups, and service accounts. Use when asked to manage access control, assign roles, check
  permissions, create custom roles, review RBAC configuration, onboard users, or audit access.
  Trigger phrases: manage roles, RBAC, role assignment, user permissions, access control, custom role,
  resource group, who has access, grant access, revoke access.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage Roles Skill

Manage Harness RBAC (Role-Based Access Control) via MCP v2 tools.

## MCP v2 Tools Used

| Tool | Resource Type | Operations |
|------|--------------|------------|
| `harness_list` | `role` | List all roles |
| `harness_get` | `role` | Get role details |
| `harness_create` | `role` | Create custom role |
| `harness_update` | `role` | Update custom role |
| `harness_delete` | `role` | Delete custom role |
| `harness_list` | `role_assignment` | List role assignments |
| `harness_get` | `role_assignment` | Get assignment details |
| `harness_list` | `permission` | List available permissions |
| `harness_get` | `permission` | Get permission details |
| `harness_list` | `resource_group` | List resource groups |
| `harness_get` | `resource_group` | Get resource group details |
| `harness_describe` | `role` | Discover role schema |
| `harness_search` | -- | Search across role-related resources |

For built-in roles (account/org/project/module), resource groups, common permissions, and role assignment structure, consult references/builtin-roles.md.

## Instructions

### Step 1: Understand Requirements

Determine:
- **Who** needs access (user email, group ID, or service account ID)
- **What** level of access (admin, developer, viewer, executor, custom)
- **Where** (account, org, project scope)
- **Which resources** (all or specific resource group)

### Step 2: List Existing Roles

```
harness_list(
  resource_type="role",
  org_id="<org>",           # optional
  project_id="<project>",   # optional
  search_term="<keyword>"   # optional
)
```

### Step 3: Check Current Assignments

```
harness_list(
  resource_type="role_assignment",
  org_id="<org>",
  project_id="<project>"
)
```

### Step 4: List Available Permissions (for custom roles)

```
harness_list(resource_type="permission")
```

### Step 5: Create Custom Role (if needed)

```
harness_create(
  resource_type="role",
  org_id="<org>",
  project_id="<project>",
  body={
    "identifier": "custom_deployer",
    "name": "Custom Deployer",
    "description": "Can execute pipelines and view services",
    "permissions": [
      "core_pipeline_execute",
      "core_pipeline_view",
      "core_service_view",
      "core_environment_view"
    ]
  }
)
```

Identifier must match pattern: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`

### Step 6: View Resource Groups

```
harness_list(resource_type="resource_group", org_id="<org>", project_id="<project>")
```

## Examples

### List all roles in a project

```
/manage-roles
Show me all roles available in the payments project
```

### Check who has admin access

```
/manage-roles
List all role assignments with admin privileges in the default org
```

### Create a custom read-only deployer role

```
/manage-roles
Create a custom role called "release-manager" that can execute pipelines,
view services and environments, but cannot edit anything
```

### Audit access for a user

```
/manage-roles
What roles does jane.smith@company.com have across all projects?
```

### Review resource groups

```
/manage-roles
Show me all resource groups and what they include
```

## Best Practices

- **Prefer groups over individual users** -- assign roles to USER_GROUP for easier management
- **Follow least privilege** -- start with viewer roles and add permissions as needed
- **Scope narrowly** -- use project-level roles over account-level when possible
- **Use built-in roles first** -- create custom roles only when built-in roles do not fit
- **Naming convention:** `{role}_{principal}` for identifiers (e.g., `deployer_ops_team`)

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Role not found | Invalid role identifier | Built-in roles start with `_` -- verify exact identifier |
| Resource group not found | Invalid resource group | Check `harness_list(resource_type="resource_group")` |
| Principal not found | User/group/SA does not exist | Verify the principal exists before assigning |
| Duplicate identifier | Role with same ID exists | Use a unique identifier or update the existing role |
| Permission denied | Caller lacks RBAC management permissions | Need `core_role_view` / `core_role_edit` permissions |

## Troubleshooting

### User Cannot Access Resources

1. List role assignments for the user to confirm a role is assigned
2. Check the role has the required permissions (`harness_get` on the role)
3. Verify the resource group scope includes the target resources
4. Check that the assignment is not `disabled: true`

### Custom Role Not Working

1. Verify all required permissions are included (e.g., `_view` permission is needed alongside `_edit`)
2. Check the role is assigned at the correct scope (account/org/project)
3. Confirm the resource group matches the resources the user needs

### Permission Denied When Managing Roles

1. The caller needs `core_role_edit` to create/update roles
2. The caller needs `core_roleassignment_edit` to manage assignments
3. Account-level operations require account admin or equivalent
