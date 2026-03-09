---
name: create-connector
description: Generate Harness Connector YAML for integrations and create/test via MCP. Use when user says "create connector", "git connector", "aws connector", "docker connector", "cloud connector", or wants to connect Harness to external services.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Connector

Generate Harness Connector YAML and create/test via MCP.

## Git Connectors

### GitHub
```yaml
connector:
  name: GitHub
  identifier: github_connector
  type: Github
  spec:
    url: https://github.com/myorg
    type: Account                    # Account or Repo
    authentication:
      type: Http
      spec:
        type: UsernameToken
        spec:
          username: myuser
          tokenRef: github_pat       # Secret reference
    apiAccess:
      type: Token
      spec:
        tokenRef: github_pat
    executeOnDelegate: false
```

### GitLab
```yaml
connector:
  name: GitLab
  identifier: gitlab_connector
  type: Gitlab
  spec:
    url: https://gitlab.com/myorg
    type: Account
    authentication:
      type: Http
      spec:
        type: UsernameToken
        spec:
          username: myuser
          tokenRef: gitlab_token
```

### Bitbucket
```yaml
connector:
  name: Bitbucket
  identifier: bitbucket_connector
  type: Bitbucket
  spec:
    url: https://bitbucket.org/myorg
    type: Account
    authentication:
      type: Http
      spec:
        type: UsernameToken
        spec:
          username: myuser
          tokenRef: bitbucket_app_password
```

## Cloud Connectors

### AWS
```yaml
connector:
  name: AWS
  identifier: aws_connector
  type: Aws
  spec:
    credential:
      type: ManualConfig          # ManualConfig, InheritFromDelegate, Irsa
      spec:
        accessKeyRef: aws_access_key
        secretKeyRef: aws_secret_key
    executeOnDelegate: false
```

### GCP
```yaml
connector:
  name: GCP
  identifier: gcp_connector
  type: Gcp
  spec:
    credential:
      type: ManualConfig          # ManualConfig, InheritFromDelegate
      spec:
        secretKeyRef: gcp_service_account_key
    executeOnDelegate: false
```

### Azure
```yaml
connector:
  name: Azure
  identifier: azure_connector
  type: Azure
  spec:
    credential:
      type: ManualConfig
      spec:
        auth:
          type: Secret
          spec:
            secretRef: azure_client_secret
        applicationId: <app_id>
        tenantId: <tenant_id>
    azureEnvironmentType: AZURE     # AZURE, AZURE_US_GOVERNMENT
    executeOnDelegate: false
```

## Registry Connectors

### Docker Hub
```yaml
connector:
  name: Docker Hub
  identifier: dockerhub
  type: DockerRegistry
  spec:
    dockerRegistryUrl: https://index.docker.io/v2/
    providerType: DockerHub
    auth:
      type: UsernamePassword
      spec:
        username: myuser
        passwordRef: dockerhub_password
```

### AWS ECR
```yaml
connector:
  name: ECR
  identifier: ecr_connector
  type: Aws
  spec:
    credential:
      type: ManualConfig
      spec:
        accessKeyRef: aws_access_key
        secretKeyRef: aws_secret_key
```

## Kubernetes Connector

```yaml
connector:
  name: K8s Cluster
  identifier: k8s_connector
  type: K8sCluster
  spec:
    credential:
      type: ManualConfig          # ManualConfig, InheritFromDelegate
      spec:
        masterUrl: https://k8s-api.example.com
        auth:
          type: ServiceAccount
          spec:
            serviceAccountTokenRef: k8s_sa_token
            caCertRef: k8s_ca_cert
```

## Creating and Testing via MCP

Create connector:
```
Call MCP tool: harness_create
Parameters:
  resource_type: "connector"
  org_id: "<organization>"
  project_id: "<project>"
  body: <connector YAML>
```

Test connection:
```
Call MCP tool: harness_execute
Parameters:
  resource_type: "connector"
  action: "test_connection"
  resource_id: "<connector_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

Browse available connector types:
```
Call MCP tool: harness_list
Parameters:
  resource_type: "connector_catalogue"
```

## Examples

- "Create a GitHub connector with PAT" - Github type with token auth
- "Set up AWS connector" - Aws type with access key credentials
- "Create Docker Hub connector" - DockerRegistry type
- "Connect to my K8s cluster" - K8sCluster with service account

## Troubleshooting

### Connection Test Fails
- Verify credentials/tokens are valid and not expired
- Check network connectivity (delegate may need access)
- Ensure proper IAM permissions for cloud connectors

### Secret References
- Secrets must exist before creating the connector
- Use format: `account.secret_name` for account-level secrets
- Use just `secret_name` for project-level secrets
