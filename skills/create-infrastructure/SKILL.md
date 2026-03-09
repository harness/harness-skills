---
name: create-infrastructure
description: Generate Harness Infrastructure Definition YAML for deployment targets and create via MCP. Use when user says "create infrastructure", "infrastructure definition", "k8s cluster config", "deployment target", or wants to configure where workloads run.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Infrastructure

Generate Harness Infrastructure Definition YAML and push via MCP.

## Infrastructure Types

### KubernetesDirect
```yaml
infrastructureDefinition:
  name: K8s Production
  identifier: k8s_prod
  orgIdentifier: default
  projectIdentifier: my_project
  environmentRef: prod
  type: KubernetesDirect
  spec:
    connectorRef: k8s_connector
    namespace: my-app-prod
    releaseName: release-<+INFRA_KEY_SHORT_ID>
```

### KubernetesGcp (GKE)
```yaml
infrastructureDefinition:
  name: GKE Cluster
  identifier: gke_prod
  environmentRef: prod
  type: KubernetesGcp
  spec:
    connectorRef: gcp_connector
    cluster: my-gke-cluster
    namespace: my-app
    releaseName: release-<+INFRA_KEY_SHORT_ID>
```

### KubernetesAzure (AKS)
```yaml
infrastructureDefinition:
  name: AKS Cluster
  identifier: aks_prod
  environmentRef: prod
  type: KubernetesAzure
  spec:
    connectorRef: azure_connector
    subscriptionId: <subscription_id>
    resourceGroup: my-rg
    cluster: my-aks-cluster
    namespace: my-app
    releaseName: release-<+INFRA_KEY_SHORT_ID>
```

### ECS
```yaml
infrastructureDefinition:
  name: ECS Fargate
  identifier: ecs_prod
  environmentRef: prod
  type: ECS
  spec:
    connectorRef: aws_connector
    region: us-east-1
    cluster: my-ecs-cluster
```

### ServerlessAwsLambda
```yaml
infrastructureDefinition:
  name: Lambda
  identifier: lambda_prod
  environmentRef: prod
  type: ServerlessAwsLambda
  spec:
    connectorRef: aws_connector
    region: us-east-1
    stage: prod
```

## Creating via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "infrastructure"
  org_id: "<organization>"
  project_id: "<project>"
  body: <infrastructure YAML>
```

## Examples

- "Create a K8s infrastructure for prod" - KubernetesDirect with prod namespace
- "Set up GKE infrastructure" - KubernetesGcp with GCP connector
- "Create ECS Fargate infrastructure" - ECS type with AWS connector

## Troubleshooting

- `CONNECTOR_NOT_FOUND` - Create the cloud/K8s connector first
- `ENVIRONMENT_NOT_FOUND` - Create the environment first
- `releaseName` must be unique per deployment; use `<+INFRA_KEY_SHORT_ID>`
