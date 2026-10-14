# Built-in Roles and Permissions Reference

## Account-Level Roles

| Identifier | Description |
|------------|-------------|
| `_account_admin` | Full account access |
| `_account_viewer` | Read-only account access |
| `_organization_admin` | Manage all organizations |
| `_organization_viewer` | View all organizations |

## Organization-Level Roles

| Identifier | Description |
|------------|-------------|
| `_organization_admin` | Full org access |
| `_organization_viewer` | Read-only org access |
| `_project_admin` | Manage all projects in org |
| `_project_viewer` | View all projects in org |

## Project-Level Roles

| Identifier | Description |
|------------|-------------|
| `_project_admin` | Full project access |
| `_project_viewer` | Read-only project access |
| `_pipeline_executor` | Execute pipelines |
| `_pipeline_editor` | Create and edit pipelines |

## Module-Specific Roles

| Identifier | Module |
|------------|--------|
| `_ci_admin` / `_ci_developer` | CI |
| `_cd_admin` / `_cd_developer` | CD |
| `_ff_admin` | Feature Flags |
| `_ccm_admin` | Cloud Cost Management |
| `_sto_admin` | Security Testing |

## Built-in Resource Groups

| Identifier | Scope |
|------------|-------|
| `_all_resources_including_child_scopes` | All resources at current and child scopes |
| `_all_account_level_resources` | All account-level resources |
| `_all_organization_level_resources` | All org-level resources |
| `_all_project_level_resources` | All project-level resources |

## Common Permissions

| Permission | Description |
|------------|-------------|
| `core_pipeline_view` | View pipelines |
| `core_pipeline_edit` | Edit pipelines |
| `core_pipeline_delete` | Delete pipelines |
| `core_pipeline_execute` | Execute pipelines |
| `core_service_view` | View services |
| `core_service_edit` | Edit services |
| `core_environment_view` | View environments |
| `core_environment_edit` | Edit environments |
| `core_secret_view` | View secrets |
| `core_secret_edit` | Edit secrets |
| `core_connector_view` | View connectors |
| `core_connector_edit` | Edit connectors |

## Role Assignment Structure

```json
{
  "identifier": "<unique_id>",
  "resource_group_identifier": "<resource_group>",
  "role_identifier": "<role_id>",
  "principal": {
    "identifier": "<user_email_or_group_id>",
    "type": "USER | USER_GROUP | SERVICE_ACCOUNT"
  },
  "disabled": false
}
```

**Principal types:**
- `USER` -- individual user (use email as identifier)
- `USER_GROUP` -- user group (use group identifier)
- `SERVICE_ACCOUNT` -- service account (use SA identifier)
