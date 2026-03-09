---
name: webhook-manager
description: >-
  Manage Harness GitX Webhooks via MCP for Git-to-Harness entity sync. Create, update, list, and delete
  webhooks that sync pipelines, templates, services, and other Harness entities from Git repositories.
  Supports account, org, and project scopes with multi-folder sync. Use when asked to create a GitX webhook,
  set up Git sync, configure repository webhooks, or manage Harness Git integration. Trigger phrases:
  create webhook, GitX webhook, Git sync, webhook manager, repository sync, manage webhooks.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Webhook Manager

Manage Harness GitX Webhooks via MCP for Git repository sync.

## Webhook Structure

```yaml
webhook:
  identifier: main_repo_webhook
  name: Main Repository Webhook
  connectorRef: github_connector
  repo: my-org/my-repo
  folderPaths:
    - .harness/
```

## Instructions

### Step 1: Identify Requirements

- What repository needs sync?
- Which folders contain Harness configs?
- What scope? (Account, Org, Project)
- Which Git connector to use?

### Step 2: Create Webhook via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "gitx_webhook"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    identifier: "project_webhook"
    name: "Project Config Webhook"
    connector_ref: "github_connector"
    repo: "my-org/my-service"
    folder_paths: [".harness/"]
```

### Step 3: Configure Git Provider

After creating the webhook in Harness, the user must add the returned webhook URL to their Git provider (GitHub/GitLab/Bitbucket) under repository webhook settings.

### Step 4: List Webhooks

```
Call MCP tool: harness_list
Parameters:
  resource_type: "gitx_webhook"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 5: Update or Delete

```
Call MCP tool: harness_update
Parameters:
  resource_type: "gitx_webhook"
  resource_id: "<webhook_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: <updated webhook config>
```

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "gitx_webhook"
  resource_id: "<webhook_identifier>"
```

## Webhook Scopes

| Scope | Use Case |
|-------|----------|
| Account | Shared templates, account-level configs |
| Organization | Cross-project resources, org templates |
| Project | Project-specific pipelines, services |

## Recommended Folder Structure

```
.harness/
├── pipelines/
├── templates/
├── services/
├── environments/
└── infrastructures/
```

## Examples

- "Set up Git sync for my service repo" - Create project-level webhook with `.harness/` folder
- "Sync shared templates from a central repo" - Create org-level webhook for templates folder
- "List all GitX webhooks" - List webhooks at the appropriate scope
- "Update webhook to sync more folders" - Update with additional folder paths

## Performance Notes

- List existing webhooks before creating to avoid duplicates.
- Verify the folder path and Git connector reference are correct before creating.
- Test webhook connectivity after creation to confirm events are being received.

## Troubleshooting

### Events Not Received
- Verify webhook URL is configured in the Git provider (GitHub/GitLab/Bitbucket)
- Check content type is `application/json` in Git provider settings
- Ensure push and PR events are selected

### Entities Not Syncing
- Folder paths must match exactly (case-sensitive)
- Files must be valid Harness YAML
- Connector must have read access to the repository

### Common Errors
- `CONNECTOR_NOT_FOUND` - Verify the Git connector exists and is accessible
- `REPOSITORY_NOT_FOUND` - Check repo name and connector permissions
- `DUPLICATE_IDENTIFIER` - Webhook with same identifier already exists
