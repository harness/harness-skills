---
name: create-connector
description: Generate Harness Connector YAML for integrations and create/test via MCP. Use when user says "create connector", "git connector", "aws connector", "docker connector", "cloud connector", or wants to connect Harness to external services.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
  summary: Create connectors (GitHub, AWS, GCP, Azure, Docker, K8s)
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Connector

Generate Harness Connector YAML and create/test via MCP.

## Instructions

1. **Identify connector type** - Determine what service to connect (Git provider, cloud provider, container registry, Kubernetes cluster)
2. **Generate YAML** using the templates below, filling in credentials and endpoint details
3. **Create via MCP** using `harness_create` with resource_type `connector`
4. **Test connection** using `harness_execute` with action `test_connection` to verify

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
      type: ManualConfig          # ManualConfig, InheritFromDelegate, Irsa, OidcAuthentication
      spec:
        accessKeyRef: aws_access_key
        secretKeyRef: aws_secret_key
    delegateSelectors: []         # Optional: target specific delegates
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
      type: ManualConfig          # ManualConfig, InheritFromDelegate, OidcAuthentication
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

## Helm Repository Connector

### HTTP Helm Repo
```yaml
connector:
  name: Helm Repo
  identifier: helm_repo
  type: HttpHelmRepo
  spec:
    helmRepoUrl: https://charts.example.com
    auth:
      type: UsernamePassword      # UsernamePassword or Anonymous
      spec:
        username: myuser
        passwordRef: helm_password
    delegateSelectors: []
```

### OCI Helm Repo
```yaml
connector:
  name: OCI Helm
  identifier: oci_helm
  type: OciHelmRepo
  spec:
    helmRepoUrl: oci://registry.example.com/charts
    auth:
      type: UsernamePassword
      spec:
        username: myuser
        passwordRef: oci_password
```

## Artifact Repository Connectors

### Nexus
```yaml
connector:
  name: Nexus
  identifier: nexus_connector
  type: Nexus
  spec:
    nexusServerUrl: https://nexus.example.com
    version: "3.x"               # "2.x" or "3.x"
    auth:
      type: UsernamePassword
      spec:
        username: admin
        passwordRef: nexus_password
```

### Artifactory
```yaml
connector:
  name: Artifactory
  identifier: artifactory_connector
  type: Artifactory
  spec:
    artifactoryServerUrl: https://artifactory.example.com
    auth:
      type: UsernamePassword
      spec:
        username: admin
        passwordRef: artifactory_password
```

## Ticketing Connectors

### Jira
```yaml
connector:
  name: Jira
  identifier: jira_connector
  type: Jira
  spec:
    jiraUrl: https://mycompany.atlassian.net
    auth:
      type: UsernamePassword
      spec:
        username: user@company.com
        passwordRef: jira_api_token
```

### ServiceNow
```yaml
connector:
  name: ServiceNow
  identifier: servicenow_connector
  type: ServiceNow
  spec:
    serviceNowUrl: https://mycompany.service-now.com
    auth:
      type: UsernamePassword
      spec:
        username: admin
        usernameRef: snow_username
        passwordRef: snow_password
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
- "Create a Helm repo connector" - HttpHelmRepo type for chart repositories
- "Set up Jira connector" - Jira type for approval and ticketing integration
- "Create Nexus connector" - Nexus type for artifact repository

## Performance Notes

- Always test the connection after creation using `harness_execute` with action `test_connection`.
- Verify that referenced secrets exist before creating the connector.
- For cloud connectors, confirm IAM permissions match the intended usage (read-only vs. read-write).

## Troubleshooting

### Connection Test Fails
- Verify credentials/tokens are valid and not expired
- Check network connectivity (delegate may need access)
- Ensure proper IAM permissions for cloud connectors

### Secret References
- Secrets must exist before creating the connector
- Use format: `account.secret_name` for account-level secrets
- Use just `secret_name` for project-level secrets

### Delegate Selectors
- Use `delegateSelectors` to target connectors at specific delegates
- Required when the service is only reachable from specific network locations
- Match delegate tags exactly (case-sensitive)
