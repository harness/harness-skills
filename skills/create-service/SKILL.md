---
name: create-service
description: >-
  Generate Harness Service YAML for deployable workloads and create via MCP. Supports Kubernetes, Helm,
  ECS, Serverless, SSH, and WinRm deployment types with artifact sources from Docker Hub, ECR, GCR, ACR,
  Nexus, and S3. Use when asked to create a service, define a Kubernetes service, set up a Helm chart
  deployment, configure an ECS service, or define what gets deployed. Trigger phrases: create service,
  service definition, Kubernetes service, Helm service, ECS service, deployment service, artifact source.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Service

Generate Harness Service YAML and push to Harness via MCP.

## Instructions

1. **Detect service type from codebase** (if source code is available) - Scan the project for deployment manifests to auto-select the correct `serviceDefinition.type` and manifest configuration:
   - `k8s/`, `kubernetes/`, `manifests/` with YAML files → `Kubernetes` with `K8sManifest`
   - `kustomization.yaml` → `Kubernetes` with `Kustomize`
   - `Chart.yaml`, `charts/`, `helm/` → `NativeHelm` with `HelmChart`
   - `task-definition.json` → `ECS` with `EcsTaskDefinition`
   - `serverless.yml` / `template.yaml` (SAM) → `ServerlessAwsLambda`
   - `function.json` (Azure) → `AzureWebApp`
   - `.NET` + Windows → `WinRm`
   - Traditional app (JAR/WAR) without containers → `Ssh`
   - See `create-pipeline/references/codebase-analysis.md` Step 4 for the full decision tree
2. **Detect artifact source** - Match Dockerfile registry references to artifact source type:
   - Docker Hub → `DockerRegistry`
   - `*.dkr.ecr.*.amazonaws.com` → `Ecr`
   - `gcr.io` / `*-docker.pkg.dev` → `Gcr`
   - `*.azurecr.io` → `Acr`
3. **Confirm with user** - Present detected service type, manifest type, and artifact source for confirmation
4. **Generate YAML** following the structure below
5. **Create via MCP** using `harness_create` with resource_type `service`

## Service Structure

```yaml
service:
  name: My Service
  identifier: my_service
  orgIdentifier: default
  projectIdentifier: my_project
  serviceDefinition:
    type: Kubernetes        # Kubernetes, NativeHelm, ECS, ServerlessAwsLambda, Ssh, WinRm, AzureWebApp
    spec:
      artifacts:
        primary:
          primaryArtifactRef: docker_image
          sources:
            - identifier: docker_image
              type: DockerRegistry
              spec:
                connectorRef: dockerhub
                imagePath: myorg/myimage
                tag: <+input>
      manifests:
        - manifest:
            identifier: k8s_manifest
            type: K8sManifest
            spec:
              store:
                type: Github
                spec:
                  connectorRef: github_connector
                  repoName: my-manifests
                  branch: main
                  paths: [manifests/]
      variables:
        - name: replicas
          type: String
          value: "3"
```

## Deployment Types

### Kubernetes Service
```yaml
serviceDefinition:
  type: Kubernetes
  spec:
    artifacts:
      primary:
        primaryArtifactRef: main_image
        sources:
          - identifier: main_image
            type: DockerRegistry
            spec:
              connectorRef: dockerhub
              imagePath: myorg/api
              tag: <+input>
    manifests:
      - manifest:
          identifier: manifests
          type: K8sManifest
          spec:
            store:
              type: Github
              spec:
                connectorRef: github
                repoName: k8s-manifests
                branch: main
                paths: [deploy/]
```

### Helm Service
```yaml
serviceDefinition:
  type: NativeHelm
  spec:
    artifacts:
      primary:
        primaryArtifactRef: chart
        sources:
          - identifier: chart
            type: DockerRegistry
            spec:
              connectorRef: dockerhub
              imagePath: myorg/api
              tag: <+input>
    manifests:
      - manifest:
          identifier: helm_chart
          type: HelmChart
          spec:
            store:
              type: Http
              spec:
                connectorRef: helm_repo
            chartName: my-chart
            chartVersion: <+input>
            helmVersion: V3
```

### ECS Service
```yaml
serviceDefinition:
  type: ECS
  spec:
    artifacts:
      primary:
        primaryArtifactRef: ecr_image
        sources:
          - identifier: ecr_image
            type: Ecr
            spec:
              connectorRef: aws_connector
              region: us-east-1
              imagePath: my-image
              tag: <+input>
    manifests:
      - manifest:
          identifier: task_def
          type: EcsTaskDefinition
          spec:
            store:
              type: Github
              spec:
                connectorRef: github
                repoName: ecs-config
                branch: main
                paths: [task-definition.json]
```

## Artifact Source Types

- `DockerRegistry` - Docker Hub (connectorRef, imagePath, tag)
- `Ecr` - AWS ECR (connectorRef, region, imagePath, tag)
- `Gcr` - Google GCR (connectorRef, registryHostname, imagePath, tag)
- `Acr` - Azure ACR (connectorRef, subscriptionId, registry, repository, tag)
- `Nexus3Registry` - Nexus (connectorRef, repository, artifactPath, tag)
- `AmazonS3` - S3 (connectorRef, region, bucketName, filePath)

## Creating via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "service"
  org_id: "<organization>"
  project_id: "<project>"
  body: <service YAML>
```

List existing services:
```
Call MCP tool: harness_list
Parameters:
  resource_type: "service"
  org_id: "<organization>"
  project_id: "<project>"
```

## Examples

- "Create a K8s service with Docker Hub artifact" - Kubernetes type with DockerRegistry source
- "Create a Helm service" - NativeHelm type with HelmChart manifest
- "Create an ECS service with ECR" - ECS type with Ecr artifact source

## Performance Notes

- Verify that referenced connectors exist before creating the service definition.
- Ensure the deployment type matches the infrastructure type that will be used in the pipeline.
- For artifact sources, confirm the image path and registry are accessible.
- Quality of service configuration is more important than speed.

## Troubleshooting

- `CONNECTOR_NOT_FOUND` - Create connector first or fix connectorRef
- `DUPLICATE_IDENTIFIER` - Service exists; use `harness_update`
- Artifact tag `<+input>` means the tag is provided at runtime
