---
name: create-pipeline-v1
description: >-
  Generate Harness v1 simplified Pipeline YAML using the new concise syntax with lowercase types, ${{ }}
  expressions, and cleaner structure. Supports CI, deployment, and approval stages with native caching and
  matrix strategies. Use when asked for a v1 pipeline, simplified pipeline, new pipeline format, or when
  user specifically requests v1 syntax. Do NOT use for v0/standard pipelines (use create-pipeline).
  Trigger phrases: v1 pipeline, simplified pipeline, new pipeline format, create v1, modern pipeline syntax.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Pipeline v1

Generate Harness v1 simplified Pipeline YAML and optionally push to Harness via MCP.

## v1 Key Differences from v0

- Expression syntax: `${{ }}` instead of `<+ >`
- Lowercase type names: `ci`, `run`, `deployment`
- Simplified structure: less nesting, cleaner YAML
- Native caching and matrix support
- `run` field instead of `command` for Run steps

## Pipeline Structure

```yaml
version: 1
kind: pipeline
spec:
  stages:
    - name: build
      type: ci
      spec:
        steps:
          - name: test
            type: run
            spec:
              shell: bash
              run: npm test
```

## Stage Types

### CI Stage

```yaml
- name: build
  type: ci
  spec:
    clone: true
    platform:
      os: linux
      arch: amd64
    runtime:
      type: cloud
    steps:
      - name: install
        type: run
        spec:
          shell: bash
          run: npm ci
```

### Deployment Stage

```yaml
- name: deploy
  type: deployment
  spec:
    deployment_type: kubernetes
    service:
      ref: my_service
    environment:
      ref: staging
      infrastructure:
        ref: k8s_staging
    steps:
      - name: rollout
        type: k8s_rolling_deploy
        spec:
          skip_dry_run: false
```

### Approval Stage

```yaml
- name: approval
  type: approval
  spec:
    steps:
      - name: approve
        type: harness_approval
        spec:
          message: "Approve deployment?"
          approvers:
            user_groups: [prod_approvers]
            min_count: 1
          timeout: 1d
```

## Step Types

### Run
```yaml
- name: test
  type: run
  spec:
    shell: bash
    run: |
      npm ci
      npm test
    env:
      NODE_ENV: test
    reports:
      - type: junit
        paths: ["junit.xml"]
```

### Run with Container
```yaml
- name: test_in_container
  type: run
  spec:
    connector: dockerhub
    image: node:18
    shell: bash
    run: npm test
```

### Build and Push Docker
```yaml
- name: docker_push
  type: build_and_push_docker
  spec:
    connector: dockerhub
    repo: myorg/myimage
    tags:
      - latest
      - ${{ pipeline.sequenceId }}
```

## Variables and Expressions

```yaml
spec:
  inputs:
    env:
      type: string
      default: dev
    version:
      type: string
```

Expressions use `${{ }}`:
- `${{ pipeline.variables.env }}` - Pipeline variable
- `${{ stage.variables.x }}` - Stage variable
- `${{ secrets.my_secret }}` - Secret reference
- `${{ trigger.branch }}` - Trigger info
- `${{ pipeline.sequenceId }}` - Build number
- `${{ input }}` - Runtime input

## Matrix Strategy

```yaml
- name: test
  type: ci
  strategy:
    matrix:
      node_version: ["16", "18", "20"]
      os: [linux, macos]
    max_concurrency: 3
  spec:
    steps:
      - name: test
        type: run
        spec:
          image: node:${{ matrix.node_version }}
          run: npm test
```

## Caching

```yaml
- name: build
  type: ci
  spec:
    cache:
      paths:
        - node_modules
      key: cache-{{ checksum "package-lock.json" }}
    steps:
      - name: install
        type: run
        spec:
          run: npm ci
```

## Parallel Execution

```yaml
- name: tests
  type: ci
  spec:
    steps:
      - parallel:
          - name: unit_test
            type: run
            spec:
              run: npm run test:unit
          - name: lint
            type: run
            spec:
              run: npm run lint
```

## Complete CI Example

```yaml
version: 1
kind: pipeline
spec:
  inputs:
    branch:
      type: string
      default: main
  stages:
    - name: build_and_test
      type: ci
      spec:
        clone: true
        platform:
          os: linux
          arch: amd64
        runtime:
          type: cloud
        cache:
          paths: [node_modules]
          key: npm-{{ checksum "package-lock.json" }}
        steps:
          - name: install
            type: run
            spec:
              shell: bash
              run: npm ci
          - parallel:
              - name: lint
                type: run
                spec:
                  run: npm run lint
              - name: test
                type: run
                spec:
                  run: npm test
                  reports:
                    - type: junit
                      paths: ["junit.xml"]
          - name: docker_push
            type: build_and_push_docker
            spec:
              connector: dockerhub
              repo: myorg/my-app
              tags:
                - ${{ pipeline.sequenceId }}
                - latest
```

## Creating via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pipeline"
  org_id: "<organization>"
  project_id: "<project>"
  body: <the v1 pipeline YAML>
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
Create a simplified Kubernetes deployment pipeline with staging and production stages
```

### Create a v1 matrix build

```
/create-pipeline-v1
Create a v1 pipeline that tests across Node 16, 18, and 20 using matrix strategy
```

## Troubleshooting

### Common v1 Syntax Errors
- Using `<+...>` instead of `${{ ... }}` expressions
- Using uppercase type names (use lowercase: `ci`, `run`, `deployment`)
- Using `command` instead of `run` for Run steps
- Missing `version: 1` and `kind: pipeline` header

### MCP Errors
- `DUPLICATE_IDENTIFIER` - Pipeline exists; use `harness_update`
- `INVALID_REQUEST` - Check YAML structure matches v1 schema
