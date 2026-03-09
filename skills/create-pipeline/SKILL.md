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
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Pipeline

Generate Harness v0 Pipeline YAML and optionally push to Harness via MCP.

## Instructions

1. **Clarify requirements** - pipeline type (CI, CD, or both), language/framework, deployment target, cloud provider, special steps (testing, scanning, approvals)
2. **Generate valid YAML** following the structure below
3. **Optionally create via MCP** using `harness_create` with resource_type `pipeline`

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

For additional step types (BuildAndPushECR, BuildAndPushGCR, BuildAndPushACR, TerraformApply, HelmDeploy, ShellScript, Http, Background, Plugin, RestoreCacheGCS, SaveCacheGCS, S3Upload, GCSUpload, RunTests), consult `references/v0-pipeline-schema.md`.

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

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body: <the pipeline YAML>
```

To update an existing pipeline:

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: <the updated pipeline YAML>
```

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

## Troubleshooting

### YAML Validation Errors
- Identifier must match `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- Stage type is case-sensitive: `CI`, `Deployment`, `Approval`, `Custom`
- Every stage must have a `spec` field

### MCP Creation Errors
- `DUPLICATE_IDENTIFIER` - Pipeline already exists; use `harness_update` instead
- `CONNECTOR_NOT_FOUND` - Create the connector first or fix connectorRef
- `ACCESS_DENIED` - Check API key permissions

### Execution Failures
- Missing `<+input>` values - provide via input sets or runtime inputs
- Connector auth expired - test with `harness_execute` (resource_type: "connector", action: "test_connection")
- Delegate offline - check with `harness_status`
