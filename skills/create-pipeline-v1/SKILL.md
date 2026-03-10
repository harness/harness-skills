---
name: create-pipeline-v1
description: >-
  Generate Harness v1 simplified Pipeline YAML using the new concise syntax with flat structure, ${{ }}
  expressions, script field, and action steps. Supports CI stages (run, run-test, background), CD stages
  (service/environment with action steps for K8s, Helm, ECS), approval (stage-level and inline), parallel
  execution, matrix/for/while strategies, caching, volumes, and templates. Use when asked for a v1 pipeline,
  simplified pipeline, new pipeline format, or when user specifically requests v1 syntax. Do NOT use for
  v0/standard pipelines (use create-pipeline). Trigger phrases: v1 pipeline, simplified pipeline, new
  pipeline format, create v1, modern pipeline syntax.
metadata:
  author: Harness
  version: 3.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Pipeline v1

Generate Harness v1 simplified Pipeline YAML and optionally push to Harness via MCP.

**Alpha: This skill is currently in internal testing only.**

## Instructions

1. **Confirm v1 format** - User must specifically want v1 syntax. Default to v0 (`/create-pipeline`) if unclear.
2. **Clarify requirements** - Pipeline type (CI, CD, or both), language/framework, deployment target
3. **Consult the spec reference** - Use `references/v1-spec-schema.md` for the complete v1 schema, step types, action catalog, and examples
4. **Select native actions** - Always prefer native action and template steps over `run:` steps. Consult `references/native-actions.md` for the full mapping. Key rules:
   - Docker build/push → use `template: uses: buildAndPushToDocker` / `buildAndPushToECR` / `buildAndPushToGAR` (never `run: docker build && docker push`)
   - K8s deploy → use `action: uses: kubernetes-rolling-deploy` or `template: uses: k8sRollingDeployStep` (never `run: kubectl apply`)
   - Helm deploy → use `action: uses: helm-deploy` or `template: uses: helmDeployBasicStep` (never `run: helm upgrade --install`)
   - ECS deploy → use `template: uses: ecsBluegreenDeployStep` (never `run: aws ecs update-service`)
   - Terraform → use `template: uses: terraformStep` (never `run: terraform apply`)
   - Security scanning → use native STO templates (`gitleaksStep`, `banditStep`, `sbomOrchestrationStep`)
   - Uploads → use `template: uses: uploadArtifactsToS3` / `uploadArtifactsToGCS` (never `run: aws s3 cp`)
   - Approvals → use `approval: uses: harness` or `approval: uses: jira` (never polling scripts)
   - Ticketing → use `action: uses: jira-create` / `snow-create` (never `run: curl`)
   - HTTP requests → use `action: uses: http` or `template: uses: httpStep` (never `run: curl`)
   - Use `run:` steps only for custom build/test/lint commands with no native equivalent
5. **Generate v1 YAML** using flat structure, `${{ }}` expressions, `script` field for run steps, and `action`/`template` steps for deployments
6. **Optionally create via MCP** using `harness_create` with resource_type `pipeline`

## v1 Key Differences from v0

| v0 Syntax | v1 Syntax |
|-----------|-----------|
| `<+variable>` expressions | `${{ variable }}` expressions |
| `type: CI` / `type: Deployment` stage types | Flat stages -- no `type` field |
| `command:` field in Run steps | `script:` field in `run:` steps |
| Native steps (`K8sRollingDeploy`, `HelmDeploy`) | Action steps (`action: uses: kubernetes-rolling-deploy`) |
| `failureStrategies:` | `on-failure:` |
| `HarnessApproval` step type | `approval: uses: harness` (stage-level or inline) |
| Deep nesting (`spec: execution: steps:`) | Flat structure (`steps:`) |
| `strategy: matrix:` under stage `spec` | `strategy: matrix:` directly on stage or step |

## Pipeline Structure

```yaml
pipeline:
  name: My Pipeline
  repo:                          # optional: repository config
    connector: account.github
    name: myorg/my-repo
  clone:                         # optional: clone config
    depth: 1
  on:                            # optional: event triggers
  - push:
      branches: [main]
  env:                           # optional: global env vars
    NODE_ENV: production
  inputs:                        # optional: pipeline inputs
    branch:
      type: string
      default: main
  stages:
  - name: build
    steps:
    - run:
        script: go build
```

No `version:`, `kind:`, or `spec:` wrapper -- `pipeline:` is the root key.

## Stages

Stages have no `type` field. Their purpose is determined by their keys.

### CI Stage

```yaml
- name: build
  runtime: cloud
  platform:
    os: linux
    arch: arm
  cache:
    path: node_modules
    key: npm.${{ branch }}
  steps:
  - run:
      script: npm ci
```

### Deployment Stage

```yaml
- name: deploy
  service: my-service
  environment: staging
  steps:
  - action:
      uses: kubernetes-rolling-deploy
      with:
        dry-run: false
```

### Approval (stage-level)

```yaml
- approval:
    uses: harness
    with:
      timeout: 30m
      message: "Approve deployment?"
      groups: [admins, ops]
      min-approvers: 1
```

## Step Types

### Run Step

Uses `script:` field (not `command:` or `run:`).

```yaml
# long syntax
- run:
    script: npm test

# short syntax
- run: npm test

# with container
- run:
    container: node:18
    script: npm test

# with shell and env
- run:
    shell: bash
    script: |
      npm ci
      npm test
    env:
      NODE_ENV: test

# with output variables
- id: build
  run:
    script: echo "TAG=v1" >> $HARNESS_OUTPUT
    output: [TAG]
```

### Run Test Step

```yaml
- run-test:
    container: maven
    script: mvn test
    report:
      type: junit
      path: target/surefire-reports/*.xml
    splitting:
      concurrency: 4
```

### Action Step

Actions replace v0 native steps. See `references/v1-spec-schema.md` for the full action catalog.

```yaml
# Kubernetes deploy
- action:
    uses: kubernetes-rolling-deploy
    with:
      dry-run: false

# Helm deploy
- action:
    uses: helm-deploy
    with:
      timeout: 10m

# Terraform plan
- action:
    uses: terraform-plan
    with:
      command: apply
      aws-provider: account.aws_connector

# HTTP request
- action:
    uses: http
    with:
      method: GET
      endpoint: https://acme.com
```

### Background Step

```yaml
- background:
    container: redis
- run:
    script: npm test
```

### Template Step

```yaml
- template:
    uses: account.docker@1.0.0
    with:
      push: true
      tags: latest
```

### Approval Step (inline)

```yaml
- approval:
    uses: jira
    with:
      connector: account.jira
      project: PROJ
```

## Parallel and Group

```yaml
# parallel steps
- parallel:
    steps:
    - run:
        script: npm run lint
    - run:
        script: npm test

# parallel stages
- parallel:
    stages:
    - steps:
      - run: go test
    - steps:
      - run: npm test

# step group
- group:
    steps:
    - run:
        script: go build
    - run:
        script: go test
```

## Strategy

```yaml
# matrix (stage-level)
- strategy:
    matrix:
      node: [16, 18, 20]
      os: [linux, macos]
    max-parallel: 3
  steps:
  - run:
      container: node:${{ matrix.node }}
      script: npm test

# matrix (step-level)
- strategy:
    matrix:
      go: [1.19, 1.20, 1.21]
  run:
    container: golang:${{ matrix.go }}
    script: go test
```

## Failure Strategy

```yaml
# step-level
- run:
    script: go test
  on-failure:
    errors: all
    action: ignore       # abort, ignore, retry, fail, success

# retry with attempts
- run:
    script: go test
  on-failure:
    errors: [unknown]
    action:
      retry:
        attempts: 5
        interval: 10s
        failure-action: fail

# stage-level
- steps:
  - run:
      script: go test
  on-failure:
    errors: all
    action: abort
```

## Conditional Execution

```yaml
# stage conditional
- if: ${{ branch == "main" }}
  steps:
  - run:
      script: deploy.sh

# step conditional
- if: ${{ branch == "main" }}
  run:
    script: deploy.sh
```

## Complete CI Example

```yaml
pipeline:
  repo:
    connector: account.github
    name: myorg/my-app
  clone:
    depth: 1
  on:
  - push:
      branches: [main]
  - pull_request:
      branches: [main]
  stages:
  - name: build-and-test
    runtime: cloud
    platform:
      os: linux
      arch: arm
    cache:
      path: node_modules
      key: npm.${{ branch }}
    steps:
    - run:
        script: npm ci
    - parallel:
        steps:
        - run:
            script: npm run lint
        - run-test:
            script: npm test
            report:
              type: junit
              path: junit.xml
    - action:
        uses: docker-build-push
        with:
          connector: dockerhub
          repo: myorg/my-app
          tags: [${{ pipeline.sequenceId }}, latest]
```

## Complete CD Example

```yaml
pipeline:
  inputs:
    skip_dry_run:
      type: boolean
      default: false
  stages:
  - name: deploy-staging
    service: petstore
    environment: staging
    steps:
    - action:
        uses: manifest-download
    - action:
        uses: manifest-bake
    - action:
        uses: kubernetes-rolling-deploy
        with:
          dry-run: ${{ inputs.skip_dry_run }}
  - approval:
      uses: harness
      with:
        timeout: 1d
        message: "Approve production deployment?"
        groups: [prod-approvers]
        min-approvers: 1
  - name: deploy-prod
    service: petstore
    environment: prod
    steps:
    - action:
        uses: manifest-download
    - action:
        uses: manifest-bake
    - action:
        uses: kubernetes-rolling-deploy
        with:
          dry-run: false
```

## Creating via MCP

1. **Verify the project exists** — List projects with `harness_list` (resource_type: `project`, org_id) to confirm. If the project does not exist, create it first with `harness_create` (resource_type: `project`, body: `{ identifier, name }`) or ask the user.
2. **Create the pipeline** — Use `harness_create` with the v1 pipeline YAML serialized as a **`yamlPipeline`** string in the body. Do not pass a nested JSON `pipeline` object; it causes serialization errors.

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<full v1 pipeline YAML string, including 'pipeline:' root key>" }
```

## Examples

### Create a v1 CI pipeline

```
/create-pipeline-v1
Create a v1 CI pipeline for a Node.js app with caching, parallel lint and test, and Docker push
```

### Create a v1 deployment pipeline

```
/create-pipeline-v1
Create a v1 Kubernetes deployment pipeline with staging approval and production stages
```

### Create a v1 matrix build

```
/create-pipeline-v1
Create a v1 pipeline that tests across Go 1.19, 1.20, and 1.21 using matrix strategy
```

## Performance Notes

- Always check `references/native-actions.md` before using a `run:` step. Native actions provide better error handling, rollback support, and UI integration.
- Always consult `references/v1-spec-schema.md` for the complete v1 spec before generating YAML.
- Use `script:` field in run steps, never `command:` or `run:` as the field name.
- Use `action: uses:` or `template: uses:` for deployments, never v0 native step types like `K8sRollingDeploy`.
- Do not mix v0 and v1 syntax. No `<+...>` expressions, no `type:` on stages, no `spec:` wrapper.
- Validate all expressions use `${{ }}` syntax before presenting.

## Troubleshooting

### Common v1 Syntax Errors

- Using `<+...>` instead of `${{ ... }}` expressions
- Adding `type:` field on stages (v1 stages have no type)
- Using `command:` or `run:` as the field name instead of `script:`
- Wrapping pipeline in `version:`, `kind:`, `spec:` (v1 uses bare `pipeline:`)
- Using v0 step types (`K8sRollingDeploy`) instead of actions (`action: uses: kubernetes-rolling-deploy`)
- Using `failureStrategies:` instead of `on-failure:`

### MCP Errors

- **Project not found** — Verify the project exists with `harness_list` (resource_type: `project`, org_id). Create it first or confirm org_id/project_id are correct.
- **Missing required fields for pipeline: pipeline** — Pass the body as `{ yamlPipeline: "<full v1 pipeline YAML string>" }` instead of a nested JSON `pipeline` object.
- `DUPLICATE_IDENTIFIER` — Pipeline exists; use `harness_update`
- `INVALID_REQUEST` — Check YAML structure matches v1 schema
