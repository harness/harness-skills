---
name: create-pipeline
description: >-
  Generate Harness v0 Pipeline YAML for CI/CD workflows and create them via MCP. Supports CI stages
  (build, test, Docker push), CD stages (Kubernetes, Helm, ECS, serverless), approval gates, parallel
  execution, matrix strategies, and failure rollback. Use when asked to create a pipeline, build pipeline,
  deployment pipeline, CI/CD workflow, or set up Harness pipelines. Do NOT use for v1 simplified pipelines
  (use create-pipeline-v1). Trigger phrases: create pipeline, build pipeline, deployment pipeline, CI/CD,
  Harness pipeline, Kubernetes deploy pipeline.
metadata:
  author: Harness
  version: 2.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Pipeline

Generate Harness v0 Pipeline YAML and optionally push to Harness via MCP.

## Instructions

1. **Analyze codebase** (if source code is available) - Scan the project to auto-detect language, build tools, test frameworks, containerization, deployment manifests, and target infrastructure. Use the detection tables and decision tree in `references/codebase-analysis.md` to determine:
   - Language and runtime version (package.json → Node.js, go.mod → Go, pom.xml → Java, etc.)
   - Build commands and base images
   - Test framework and report format (Jest → JUnit, pytest → JUnit XML, etc.)
   - Linter and formatter (ESLint, Prettier, Ruff, etc.)
   - Dockerfile presence and registry type (Docker Hub, ECR, GCR, ACR)
   - Deployment manifests → Harness service/deployment type (k8s manifests → Kubernetes, Chart.yaml → NativeHelm, task-definition.json → ECS, serverless.yml → ServerlessAwsLambda)
   - Existing CI/CD configs for migration (GitHub Actions, Jenkins, GitLab CI, etc.)
2. **Clarify requirements** - Confirm detected settings with the user. Ask about anything that couldn't be auto-detected: deployment target, cloud provider, approval gates, notification channels.
3. **Select native steps** - Always prefer Harness native steps over `Run` or `ShellScript` steps. Consult `references/native-steps.md` for the full mapping. Key rules:
   - Docker build/push → use `BuildAndPushDockerRegistry` / `BuildAndPushECR` / `BuildAndPushGCR` / `BuildAndPushACR` (never `Run: docker build && docker push`)
   - K8s deploy → use `K8sRollingDeploy` / `K8sBlueGreenDeploy` / `K8sCanaryDeploy` (never `Run: kubectl apply`)
   - Helm deploy → use `HelmDeploy` (never `Run: helm upgrade --install`)
   - ECS deploy → use `EcsRollingDeploy` (never `Run: aws ecs update-service`)
   - Terraform → use `TerraformPlan` / `TerraformApply` (never `Run: terraform apply`)
   - Security scanning → use native STO steps (`AquaTrivy`, `Snyk`, `Sonarqube`, `Semgrep`, etc.)
   - Uploads → use `S3Upload` / `GCSUpload` (never `Run: aws s3 cp`)
   - Approvals → use `HarnessApproval` / `JiraApproval` (never polling scripts)
   - Ticketing → use `JiraCreate` / `ServiceNowCreate` (never `Run: curl`)
   - Use `Run` steps only for custom build/test/lint commands with no native equivalent
4. **Generate valid YAML** following the structure below, using the detected build/test/deploy commands
5. **Optionally create via MCP** using `harness_create` with resource_type `pipeline`

## Pipeline Structure

```yaml
pipeline:
  identifier: my_pipeline       # ^[a-zA-Z_][0-9a-zA-Z_]{0,127}$
  name: My Pipeline
  orgIdentifier: default
  projectIdentifier: my_project
  tags: {}
  properties:
    ci:
      codebase:                  # Required for CI stages
        connectorRef: github_connector
        repoName: my-repo
        build:
          type: branch
          spec:
            branch: <+trigger.branch>
  stages:
    - stage: ...
```

## Stage Types

### CI Stage (type: CI)

```yaml
- stage:
    identifier: build
    name: Build
    type: CI
    spec:
      cloneCodebase: true
      platform:
        os: Linux
        arch: Amd64
      runtime:
        type: Cloud    # Cloud, Kubernetes, VM, Docker
        spec: {}
      execution:
        steps:
          - step: ...
```

### CD Stage (type: Deployment)

```yaml
- stage:
    identifier: deploy
    name: Deploy
    type: Deployment
    spec:
      deploymentType: Kubernetes  # Kubernetes, NativeHelm, ECS, ServerlessAwsLambda, Ssh, WinRm, AzureWebApp
      service:
        serviceRef: my_service
      environment:
        environmentRef: dev
        infrastructureDefinitions:
          - identifier: k8s_dev
      execution:
        steps:
          - step: ...
        rollbackSteps:
          - step: ...
    failureStrategies:
      - onFailure:
          errors: [AllErrors]
          action:
            type: StageRollback
```

### Approval Stage (type: Approval)

```yaml
- stage:
    identifier: approval
    name: Approval
    type: Approval
    spec:
      execution:
        steps:
          - step:
              identifier: approve
              name: Approve
              type: HarnessApproval
              spec:
                approvalMessage: "Please review and approve"
                approvers:
                  userGroups: [prod_approvers]
                  minimumCount: 1
              timeout: 1d
```

## Common Step Types

### Run Step
```yaml
- step:
    identifier: run_tests
    name: Run Tests
    type: Run
    spec:
      shell: Bash          # Sh, Bash, Powershell, Pwsh, Python
      command: |
        npm ci
        npm test
      envVariables:
        NODE_ENV: test
      reports:
        type: JUnit
        spec:
          paths: ["junit.xml"]
```

### Build and Push Docker
```yaml
- step:
    identifier: docker_push
    name: Build and Push
    type: BuildAndPushDockerRegistry
    spec:
      connectorRef: dockerhub
      repo: myorg/myimage
      tags: [latest, <+pipeline.sequenceId>]
      dockerfile: Dockerfile
```

### K8s Rolling Deploy
```yaml
- step:
    identifier: rollout
    name: Rollout
    type: K8sRollingDeploy
    spec:
      skipDryRun: false
    timeout: 10m
```

### K8s Rolling Rollback
```yaml
- step:
    identifier: rollback
    name: Rollback
    type: K8sRollingRollback
    spec: {}
    timeout: 10m
```

For the complete catalog of 300+ native step types (cloud deployments, security scanners, IaC, ticketing, approvals, GitOps, and more), consult `references/native-steps.md`. Always check this reference before using a `Run` step.

## Variables and Expressions

```yaml
pipeline:
  variables:
    - name: env
      type: String
      default: dev
    - name: api_key
      type: Secret
      value: <+secrets.getValue("api_key")>
```

Common expressions:
- `<+pipeline.variables.env>` - Pipeline variable
- `<+stage.variables.VAR>` - Stage variable
- `<+steps.step_id.output.outputVariables.VAR>` - Step output
- `<+trigger.branch>`, `<+trigger.commitSha>` - Trigger info
- `<+secrets.getValue("name")>` - Secret reference
- `<+pipeline.sequenceId>` - Build number

## Parallel Execution

```yaml
# Parallel steps
- parallel:
    - step: ...
    - step: ...

# Parallel stages
stages:
  - parallel:
      - stage: ...
      - stage: ...
```

## Failure Strategies

```yaml
failureStrategies:
  - onFailure:
      errors: [AllErrors]     # AllErrors, Timeout, Authentication, Connectivity
      action:
        type: StageRollback   # Ignore, Retry, MarkAsSuccess, Abort, StageRollback, PipelineRollback
```

## Conditional Execution

```yaml
- stage:
    when:
      pipelineStatus: Success
      condition: <+pipeline.variables.deploy> == "true"
```

## Matrix Strategy

```yaml
- stage:
    strategy:
      matrix:
        node_version: ["16", "18", "20"]
        os: [linux, macos]
      maxConcurrency: 3
```

## Creating via MCP

After generating the YAML, create it in Harness:

1. **Ensure the project exists** — If the project does not exist, create it first with `harness_create` (resource_type: `project`, body: `{ identifier, name }`) or ask the user to create it. List projects with `harness_list` (resource_type: `project`, org_id) to verify.
2. **Create the pipeline** — Use `harness_create` with the pipeline YAML in the body as a **yamlPipeline** string. Passing a large nested JSON `pipeline` object can cause serialization errors and may not satisfy the API; the reliable format is:

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<full pipeline YAML string, including 'pipeline:' root>" }
```

To update an existing pipeline:

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<full updated pipeline YAML string>" }
```

**MCP server note:** If the Harness MCP server (harness-mcp-v2) documents in `harness_describe`(resource_type: "pipeline") or in the pipeline schema that create accepts `body.yamlPipeline` (YAML string), agents can discover this format without relying on the skill.

To verify it was created:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

## Complete CI Example

```yaml
pipeline:
  identifier: nodejs_ci
  name: Node.js CI
  projectIdentifier: my_project
  orgIdentifier: default
  properties:
    ci:
      codebase:
        connectorRef: github_connector
        repoName: my-app
        build:
          type: branch
          spec:
            branch: <+trigger.branch>
  stages:
    - stage:
        identifier: build_and_test
        name: Build and Test
        type: CI
        spec:
          cloneCodebase: true
          platform:
            os: Linux
            arch: Amd64
          runtime:
            type: Cloud
            spec: {}
          execution:
            steps:
              - step:
                  identifier: install
                  name: Install
                  type: Run
                  spec:
                    shell: Bash
                    command: npm ci
              - parallel:
                  - step:
                      identifier: lint
                      name: Lint
                      type: Run
                      spec:
                        shell: Bash
                        command: npm run lint
                  - step:
                      identifier: test
                      name: Test
                      type: Run
                      spec:
                        shell: Bash
                        command: npm test
              - step:
                  identifier: docker_push
                  name: Build and Push
                  type: BuildAndPushDockerRegistry
                  spec:
                    connectorRef: dockerhub
                    repo: myorg/my-app
                    tags: [<+pipeline.sequenceId>, latest]
```

## Complete CD Example

```yaml
pipeline:
  identifier: k8s_deploy
  name: K8s Deploy
  projectIdentifier: my_project
  orgIdentifier: default
  stages:
    - stage:
        identifier: deploy_staging
        name: Deploy Staging
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            serviceRef: my_service
          environment:
            environmentRef: staging
            infrastructureDefinitions:
              - identifier: k8s_staging
          execution:
            steps:
              - step:
                  identifier: rollout
                  name: Rollout
                  type: K8sRollingDeploy
                  spec:
                    skipDryRun: false
                  timeout: 10m
            rollbackSteps:
              - step:
                  identifier: rollback
                  name: Rollback
                  type: K8sRollingRollback
                  spec: {}
                  timeout: 10m
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: StageRollback
    - stage:
        identifier: approval
        name: Production Approval
        type: Approval
        spec:
          execution:
            steps:
              - step:
                  identifier: approve
                  name: Approve Prod
                  type: HarnessApproval
                  spec:
                    approvalMessage: "Approve production deployment?"
                    approvers:
                      userGroups: [prod_approvers]
                      minimumCount: 1
                  timeout: 1d
    - stage:
        identifier: deploy_prod
        name: Deploy Production
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            serviceRef: my_service
          environment:
            environmentRef: prod
            infrastructureDefinitions:
              - identifier: k8s_prod
          execution:
            steps:
              - step:
                  identifier: rollout
                  name: Rollout
                  type: K8sRollingDeploy
                  spec:
                    skipDryRun: false
                  timeout: 10m
            rollbackSteps:
              - step:
                  identifier: rollback
                  name: Rollback
                  type: K8sRollingRollback
                  spec: {}
                  timeout: 10m
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: StageRollback
```

## Examples

### Create a CI pipeline

```
/create-pipeline
Create a CI pipeline for a Node.js app that builds, runs tests, and pushes to Docker Hub
```

### Create a CD pipeline with approvals

```
/create-pipeline
Create a Kubernetes deployment pipeline with staging, manual approval, and production stages
```

### Create a combined CI/CD pipeline

```
/create-pipeline
Build a pipeline that runs tests, pushes a Docker image, and deploys to ECS with rollback
```

### Create a matrix build pipeline

```
/create-pipeline
Create a CI pipeline that tests across Node 16, 18, and 20 on both Linux and macOS
```

### Create a pipeline with parallel stages

```
/create-pipeline
Create a pipeline with parallel test stages for unit tests, integration tests, and linting
```

## Performance Notes

- Always check `references/native-steps.md` before using a Run step. Native steps provide better error handling and UI integration.
- Validate that all referenced connectors, services, and environments exist before creating the pipeline.
- For CD pipelines, confirm the deployment type matches the service definition type.
- Quality of generated YAML is more important than speed. Verify structure before submitting.

## Troubleshooting

### YAML Validation Errors
- Identifier must match `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- Stage type is case-sensitive: `CI`, `Deployment`, `Approval`, `Custom`
- Every stage must have a `spec` field

### MCP Creation Errors
- **Project not found** — Create the project first with `harness_create` (resource_type: `project`, body: `{ identifier, name }`) or confirm project_id/org_id. List projects with `harness_list` (resource_type: `project`, org_id).
- **Missing required fields for pipeline: pipeline** — Pass the body as `{ yamlPipeline: "<full pipeline YAML string>" }` (not a nested JSON `pipeline` object). Avoid large nested JSON to prevent serialization issues.
- `DUPLICATE_IDENTIFIER` - Pipeline already exists; use `harness_update` instead
- `CONNECTOR_NOT_FOUND` - Create the connector first or fix connectorRef
- `ACCESS_DENIED` - Check API key permissions

### Execution Failures
- Missing `<+input>` values - provide via input sets or runtime inputs
- Connector auth expired - test with `harness_execute` (resource_type: "connector", action: "test_connection")
- Delegate offline - check with `harness_status`
