---
name: create-secret
description: >-
  Generate Harness Secret definitions and manage secrets via MCP v2 tools. Supports SecretText,
  SecretFile, SSHKey, and WinRmCredentials types with configurable secret managers (Harness built-in,
  HashiCorp Vault, AWS Secrets Manager, Azure Key Vault, GCP Secret Manager). Use when asked to
  create a secret, store credentials, manage API keys, set up SSH keys, configure WinRM credentials,
  rotate secrets, or reference secrets in pipelines. Trigger phrases: create secret, secret text,
  secret file, SSH key, API key, password, credentials, secret manager, store secret.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Secret Skill

Generate Harness Secret definitions and manage secrets via MCP v2 tools.

## MCP v2 Tools Used

| Tool | Resource Type | Purpose |
|------|--------------|---------|
| `harness_list` | `secret` | List existing secrets |
| `harness_get` | `secret` | Get secret metadata (not the value) |
| `harness_create` | `secret` | Create a new secret |
| `harness_update` | `secret` | Update secret metadata or value |
| `harness_delete` | `secret` | Delete a secret |
| `harness_describe` | `secret` | Discover secret resource schema |

## Secret Types

### SecretText

Stores text-based secrets: passwords, API tokens, connection strings.

```yaml
secret:
  identifier: my_api_key
  name: My API Key
  description: API key for external service
  type: SecretText
  spec:
    secretManagerIdentifier: harnessSecretManager
    valueType: Inline
    value: <secret_value>
```

For other secret types (SecretFile, SSHKey with KeyReference/KeyPath/Password, WinRmCredentials with NTLM/Kerberos) and secret manager configuration, consult references/secret-types.md.

## Secret Scopes

| Scope | Visibility | MCP Parameters |
|-------|-----------|----------------|
| Project | Only within the project | `org_id` + `project_id` |
| Organization | All projects in the org | `org_id` only |
| Account | All orgs and projects | Neither org_id nor project_id |

## Instructions

### Step 1: Determine Requirements

- Secret type: SecretText, SecretFile, SSHKey, or WinRmCredentials
- Secret manager: Harness built-in or external
- Scope: project, org, or account
- Tags and description for organization

### Step 2: Check for Existing Secrets

```
harness_list(
  resource_type="secret",
  org_id="<org>",
  project_id="<project>",
  search_term="<keyword>"
)
```

### Step 3: Create the Secret

```
harness_create(
  resource_type="secret",
  org_id="<org>",
  project_id="<project>",
  body={
    "secret": {
      "identifier": "my_api_key",
      "name": "My API Key",
      "type": "SecretText",
      "spec": {
        "secret_manager_identifier": "harnessSecretManager",
        "value_type": "Inline",
        "value": "<value>"
      }
    }
  }
)
```

### Step 4: Verify Creation

```
harness_get(
  resource_type="secret",
  resource_id="my_api_key",
  org_id="<org>",
  project_id="<project>"
)
```

## Referencing Secrets in Pipelines

```yaml
# Project-level secret
<+secrets.getValue("my_api_key")>

# Org-level secret
<+secrets.getValue("org.my_api_key")>

# Account-level secret
<+secrets.getValue("account.my_api_key")>
```

In connector configuration:

```yaml
connector:
  spec:
    authentication:
      spec:
        tokenRef: github_pat   # secret identifier
```

In service variables:

```yaml
variables:
  - name: DB_PASSWORD
    type: Secret
    value: <+secrets.getValue("db_password")>
```

## Naming Conventions

| Secret Type | Pattern | Example |
|-------------|---------|---------|
| API Keys | `{service}_api_key` | `github_api_key` |
| Passwords | `{system}_password` | `prod_db_password` |
| Tokens | `{provider}_token` | `slack_token` |
| SSH Keys | `ssh_{purpose}` | `ssh_deploy_key` |
| Certificates | `{service}_cert` | `ssl_prod_cert` |

Identifier must match: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`

## Examples

### Create a GitHub PAT secret

```
/create-secret
Create a SecretText for a GitHub personal access token at the project level
using the Harness built-in secret manager
```

### Create SSH credentials

```
/create-secret
Create an SSH key secret for deploying to production servers as the "deploy" user
```

### Create a Vault-referenced secret

```
/create-secret
Create a secret that references the database password stored in HashiCorp Vault
at secret/data/production/database#password
```

### List secrets

```
/create-secret
Show me all secrets in the payments project
```

### Create WinRM credentials

```
/create-secret
Create WinRM NTLM credentials for the Windows deployment servers
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Duplicate identifier | Secret with same ID exists | Use unique identifier or update existing |
| Secret manager not found | Invalid `secretManagerIdentifier` | Verify the secret manager connector exists |
| Encryption failed | Secret manager connectivity issue | Check delegate connectivity to secret manager |
| Invalid secret type | Unsupported type string | Use `SecretText`, `SecretFile`, `SSHKey`, or `WinRmCredentials` |
| Invalid valueType | Case mismatch | Use `Inline` or `Reference` (case-sensitive) |

## Troubleshooting

### Secret Not Accessible in Pipeline

1. Check scope -- project secrets need no prefix, org secrets need `org.` prefix, account secrets need `account.` prefix
2. Verify the pipeline's project has access to the secret's scope
3. Confirm the user/service account running the pipeline has `core_secret_view` permission

### External Secret Manager Errors

1. Verify the secret manager connector is healthy (`harness_get` on the connector)
2. For Vault: check the path format includes `#key` suffix for specific keys
3. For AWS SM: ensure IAM permissions allow `secretsmanager:GetSecretValue`
4. Delegate must have network access to the external secret manager

### SSH Key Connection Failures

1. Verify the private key is in PEM format
2. Check that the target server accepts key-based authentication
3. If using KeyPath, confirm the key file exists on the delegate host
4. Test with `credentialType: Password` first to isolate key-specific issues

## Security Best Practices

- Use external secret managers (Vault, AWS SM) for production secrets
- Scope secrets as narrowly as possible -- prefer project over account
- Never output secret values in pipeline logs
- Rotate secrets regularly and update references
- Audit secret access via the `/audit-report` skill
