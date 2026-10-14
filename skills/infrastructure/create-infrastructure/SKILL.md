---
name: create-infrastructure
description: Generate Harness Infrastructure Definition YAML for deployment targets and create via MCP. Use when user says "create infrastructure", "infrastructure definition", "k8s cluster config", "deployment target", or wants to configure where workloads run.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
  summary: Define infrastructure (K8s, ECS, Serverless)
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Infrastructure

Generate Harness Infrastructure Definition YAML and push via MCP.

## Instructions

1. **Identify infrastructure type** - KubernetesDirect, KubernetesGcp (GKE), KubernetesAzure (AKS), ECS, or ServerlessAwsLambda
2. **Ensure prerequisites exist** - The environment and cloud/cluster connector must be created first
3. **Generate YAML** using the templates below, referencing the correct connector and environment
4. **Create via MCP** using `harness_create` with resource_type `infrastructure`

## Infrastructure Types

### KubernetesDirect
```yaml
infrastructureDefinition:
  name: K8s Production
  identifier: k8s_prod
  orgIdentifier: default
  projectIdentifier: my_project
  environmentRef: prod
  deploymentType: Kubernetes
  type: KubernetesDirect
  spec:
    connectorRef: k8s_connector
    namespace: my-app-prod
    releaseName: release-<+INFRA_KEY_SHORT_ID>
  allowSimultaneousDeployments: false
```

### KubernetesGcp (GKE)
```yaml
infrastructureDefinition:
  name: GKE Cluster
  identifier: gke_prod
  environmentRef: prod
  deploymentType: Kubernetes
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
  deploymentType: Kubernetes
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
  deploymentType: ECS
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
  deploymentType: ServerlessAwsLambda
  type: ServerlessAwsLambda
  spec:
    connectorRef: aws_connector
    region: us-east-1
    stage: prod
```

### AzureWebApp
```yaml
infrastructureDefinition:
  name: Azure Web App
  identifier: azure_webapp_prod
  environmentRef: prod
  deploymentType: AzureWebApp
  type: AzureWebApp
  spec:
    connectorRef: azure_connector
    subscriptionId: <subscription_id>
    resourceGroup: my-rg
```

### Asg (Auto Scaling Group)
```yaml
infrastructureDefinition:
  name: ASG Production
  identifier: asg_prod
  environmentRef: prod
  deploymentType: Asg
  type: Asg
  spec:
    connectorRef: aws_connector
    region: us-east-1
```

### GoogleCloudFunctions
```yaml
infrastructureDefinition:
  name: Cloud Functions
  identifier: gcf_prod
  environmentRef: prod
  deploymentType: GoogleCloudFunctions
  type: GoogleCloudFunctions
  spec:
    connectorRef: gcp_connector
    region: us-central1
    project: my-gcp-project
```

### Pdc (Physical Data Center)
```yaml
infrastructureDefinition:
  name: On-Prem Servers
  identifier: pdc_prod
  environmentRef: prod
  deploymentType: Ssh
  type: Pdc
  spec:
    connectorRef: pdc_connector
    hosts:
      - host1.example.com
      - host2.example.com
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
- "Create Azure Web App infrastructure" - AzureWebApp type with subscription and resource group
- "Set up on-prem infrastructure" - Pdc type with host list for SSH deployments

## Performance Notes

- Verify the referenced connector and environment exist before creating the infrastructure definition.
- Ensure namespace and cluster names are accurate — typos will cause deployment failures.
- Use `<+INFRA_KEY_SHORT_ID>` in releaseName to guarantee uniqueness across deployments.

## Troubleshooting

- `CONNECTOR_NOT_FOUND` - Create the cloud/K8s connector first
- `ENVIRONMENT_NOT_FOUND` - Create the environment first
- `releaseName` must be unique per deployment; use `<+INFRA_KEY_SHORT_ID>`
- `deploymentType` must match the service definition's type (e.g., Kubernetes service needs KubernetesDirect infra)
- `allowSimultaneousDeployments: false` is the default; set to `true` only if concurrent deploys are safe
