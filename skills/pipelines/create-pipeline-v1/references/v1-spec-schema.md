# Harness v1 Pipeline Spec Reference

Complete reference for the v1 simplified pipeline YAML syntax. Source: https://github.com/thisrohangupta/spec

## Pipeline Structure

```yaml
pipeline:
  name: My Pipeline          # optional display name
  inputs: {}                 # pipeline-level inputs
  env: {}                    # global environment variables
  repo: {}                   # repository configuration
  clone: {}                  # clone configuration
  on: []                     # event triggers
  barriers: []               # barrier definitions
  stages: []                 # pipeline stages
```

No `version:`, `kind:`, or `spec:` wrapper -- the v1 format uses `pipeline:` as the root key directly.

## Repository and Clone

### Repository

```yaml
pipeline:
  repo:
    connector: account.github
    name: harness/hello-world
```

### Clone Configurations

```yaml
# disabled (short)
clone: false

# disabled (long)
clone:
  disabled: true

# with depth and ref (short)
clone:
  depth: 50
  ref: main

# with fully-qualified ref
clone:
  depth: 50
  ref: refs/heads/main

# with typed ref (long)
clone:
  depth: 50
  ref:
    name: main
    type: branch

# with options
clone:
  insecure: true
  trace: true
```

Clone can be set at pipeline level or per-stage:

```yaml
pipeline:
  clone: false          # disable globally
  stages:
  - clone: false        # disable per stage
    steps: [...]
```

## Event Triggers (`on`)

```yaml
# single event
on: push

# multiple events
on:
- push
- pull_request

# with branch filters
on:
- push:
    branches: [main]
- pull_request:
    branches: [main]
```

## Inputs

```yaml
pipeline:
  inputs:
    branch:
      type: string
      default: main
    version:
      type: string
      required: true
    deploy_env:
      type: string
      enum: [dev, staging, prod]
    api_key:
      type: secret
      default: account.my_secret
```

Input types: `string`, `secret`, `boolean`

Reference inputs with `${{ inputs.branch }}`.

## Stages

Stages are flat -- no `type` field. The stage's purpose is determined by its keys.

### CI Stage (steps only)

```yaml
pipeline:
  stages:
  - name: build
    steps:
    - run:
        script: go build
```

### CI Stage with Runtime

```yaml
pipeline:
  stages:
  - name: build
    runtime: cloud                    # short syntax
    platform:
      os: linux
      arch: arm
    steps:
    - run:
        script: go build
```

Runtime types:
- `cloud` (short) or `cloud: { image: ubuntu-latest, size: large }` (long)
- `kubernetes: { namespace: default }`
- `shell` (short) or `shell: true` (long)

### Deployment Stage (service + environment)

```yaml
pipeline:
  stages:
  - name: deploy
    service: petstore
    environment: prod
    steps:
    - action:
        uses: kubernetes-rolling-deploy
        with:
          dry-run: false
```

### Multi-Service / Multi-Environment

```yaml
pipeline:
  stages:
  - name: deploy-all
    service:
      items: [svc-a, svc-b, svc-c]
      sequential: true
    environment:
      items: [dev, staging, prod]
      sequential: true
      deploy-to:
        dev:
          infrastructure: k8s-dev
        staging:
          infrastructure: k8s-staging
        prod:
          infrastructure: k8s-prod
    steps:
    - action:
        uses: kubernetes-rolling-deploy
```

### Pipeline-Level Service/Environment

```yaml
pipeline:
  service: petstore
  environment: prod
  stages:
  - steps:
    - action:
        uses: kubernetes-rolling-deploy
```

### Stage with Delegate

```yaml
pipeline:
  stages:
  - name: deploy
    delegate: my-delegate-group
    steps: [...]
```

### Stage with Conditional

```yaml
pipeline:
  stages:
  - name: deploy
    if: ${{ branch == "main" }}
    steps: [...]
```

## Step Types

### Run Step

The `run` step uses a `script` field (not `run` or `command`).

```yaml
# long syntax
- run:
    script: go build

# short syntax
- run: go build

# with container
- run:
    container: golang
    script: go build

# with container options
- run:
    container:
      image: node:18
      user: 1000
      group: 1000
      privileged: false
      memory: 512m
      cpu: 1000
      pull: always        # always, never, if-not-exists
    script: npm test

# with shell
- run:
    shell: bash            # bash, powershell, python, sh
    script: |
      npm ci
      npm test

# multi-line as array
- run:
    script:
    - npm install
    - npm test

# with environment variables
- run:
    script: npm test
    env:
      NODE_ENV: test
      API_KEY: ${{ inputs.api_key }}

# with delegate
- run:
    script: deploy.sh
    delegate: my-delegate

# with output variables
- run:
    script: |
      echo "VERSION=1.0.0" >> $HARNESS_OUTPUT
    output:
      - VERSION
      - name: SECRET_VAR
        mask: true

# referencing step outputs
- id: build
  run:
    script: echo "TAG=v1" >> $HARNESS_OUTPUT
    output: [TAG]
- run:
    script: echo ${{ steps.build.output.TAG }}
```

### Run Test Step

Test intelligence with splitting and reports:

```yaml
# basic
- run-test:
    container: maven
    script: mvn test

# with report
- run-test:
    script: mvn test
    report:
      type: junit
      path: /path/to/junit.xml

# with test globbing
- run-test:
    script: mvn test
    match:
    - tests/**/*.java

# with parallel splitting
- run-test:
    script: mvn test
    splitting:
      concurrency: 4

# disabled intelligence
- run-test:
    script: mvn test
    intelligence:
      disabled: true
```

### Background Step

```yaml
# short syntax (container name as image)
- background:
    container: redis

# long syntax with ports
- background:
    container:
      image: redis
      ports:
        - 80:80

# background script
- background:
    script: npm run start
```

### Action Step

Actions replace v0 native steps. They reference reusable templates.

```yaml
# Harness action (replaces v0 native steps)
- action:
    uses: kubernetes-rolling-deploy
    with:
      dry-run: false

# Kubernetes blue-green
- action:
    uses: kubernetes-blue-green-deploy
    with:
      dry-run: false
      pruning: false

# Helm deploy
- action:
    uses: helm-deploy
    with:
      timeout: 10m
      steady-state-check: true

# Terraform plan
- action:
    uses: terraform-plan
    with:
      command: apply
      aws-provider: account.aws_connector
      export-plan: true

# HTTP request
- action:
    uses: http
    with:
      method: GET
      endpoint: https://acme.com

# Wait
- action:
    uses: wait
    with:
      duration: 10m

# Jira create
- action:
    uses: jira-create
    with:
      connector: harness-jira
      project: cds
      type: enhancement
      fields:
      - name: labels
        value: adoption_blocker

# ServiceNow create
- action:
    uses: snow-create
    with:
      connector: harness-snow
      ticket-type: asset type
      description: enhancement

# Kubernetes scale
- action:
    uses: kubernetes-scale
    with:
      workload: default/Deployment/harness-example
      replica: 2

# OPA policy
- action:
    uses: policy
    with:
      type: custom
      timeout: 10m
      name: namespace-validator
      payload: |
        {"name": "<+infra.name>"}

# Git clone
- action:
    uses: git-clone
    with:
      branch: main
      repo-name: Product-Management
      connector: cd-demo

# GitHub Action (third-party)
- action:
    uses: docker-build-push-action
    with:
      push: true
      tags: latest
```

Available Harness actions:
- `kubernetes-rolling-deploy`, `kubernetes-blue-green-deploy`, `kubernetes-blue-green-swap`, `kubernetes-blue-green-scale-down`, `kubernetes-canary-deploy`, `kubernetes-canary-delete`, `kubernetes-delete`, `kubernetes-scale`
- `manifest-download`, `manifest-bake`
- `helm-deploy`, `helm-rollback`
- `terraform-plan`, `terraform-provisioner`
- `dynamic-environment`
- `http`, `wait`
- `jira-create`, `jira-update`
- `snow-create`, `snow-update`
- `policy`
- `git-clone`

### Template Step

```yaml
# reference a template
- template:
    uses: account.docker
    with:
      push: true
      tags: latest
      repo: harness/hello-world

# with version pinning
- template:
    uses: account.docker@1.0.0
    with:
      push: true
```

### Approval Step (inline)

```yaml
- approval:
    uses: jira
    with:
      connector: account.jira
      project: PROJ
```

### Barrier Step

```yaml
# define barriers at pipeline level
pipeline:
  barriers:
    - some-barrier
  stages:
  - steps:
    - run:
        script: go build
    - barrier:
        name: some-barrier
    - run:
        script: go test
```

### Queue Step

```yaml
- timeout: 30m
  queue:
    key: some-queue
    scope: pipeline
```

## Stage-Level Approval

Approval is a stage-level key (not a step type):

```yaml
pipeline:
  stages:
  - steps:
    - action:
        uses: kubernetes-rolling-deploy
    - approval:
        uses: harness
        with:
          timeout: 30m
          message: "Approve deployment?"
          groups: [admins, ops]
          min-approvers: 1
          auto-reject: true
          self-approval: false
          print-execution-history: true
```

## Parallel and Group

### Parallel Steps

```yaml
- parallel:
    steps:
    - run:
        script: go build
    - run:
        script: go test

# with conditional
- if: ${{ branch == "main" }}
  parallel:
    steps:
    - run:
        script: go build
    - run:
        script: go test
```

### Step Group

```yaml
- group:
    steps:
    - run:
        script: go build
    - run:
        script: go test

# with conditional
- if: ${{ branch == "main" }}
  group:
    steps:
    - run:
        script: go build
    - run:
        script: go test
```

### Parallel Stages

```yaml
pipeline:
  stages:
  - parallel:
      stages:
      - steps:
        - run: go build
      - steps:
        - run: npm run

# with conditional
  - if: ${{ branch == "main" }}
    parallel:
      stages:
      - steps:
        - run: go build
      - steps:
        - run: npm test
```

### Stage Group

```yaml
pipeline:
  stages:
  - group:
      stages:
      - steps:
        - run: go build
        - run: go test
      - steps:
        - run: npm run
        - run: npm test
```

## Strategy (Matrix, For, While)

### Matrix (stage-level)

```yaml
pipeline:
  stages:
  - strategy:
      matrix:
        go: [1.19, 1.20, 1.21]
        platform: [linux, windows]
      exclude:
        - go: 1.19
          platform: windows
      max-parallel: 2
    steps:
    - run:
        container: golang:${{ matrix.go }}
        script: go test
```

### Matrix (step-level)

```yaml
- strategy:
    matrix:
      node: [19, 20, 21]
  run:
    container: node:${{ matrix.node }}
    script: npm test
```

### For Loop

```yaml
pipeline:
  stages:
  - strategy:
      for:
        iterations: 10
    steps:
    - run:
        script: echo iteration ${{ iteration.index }}
```

### While Loop

```yaml
pipeline:
  stages:
  - strategy:
      while:
        iterations: 100
        condition: ${{ steps.health.output.STATUS != "healthy" }}
    steps:
    - id: health
      run:
        script: curl -s http://app/health
```

## Failure Strategy (`on-failure`)

Can be set at stage or step level.

### Basic Actions

```yaml
# step-level
- run:
    script: go test
  on-failure:
    errors: all              # all, unknown, connectivity, timeout, etc.
    action: abort            # abort, ignore, retry, fail, success

# stage-level
pipeline:
  stages:
  - steps:
    - run:
        script: go test
    on-failure:
      errors: all
      action: abort
```

### Retry

```yaml
- run:
    script: go test
  on-failure:
    errors: [unknown]
    action:
      retry:
        attempts: 5
        interval: 10s               # single interval
        failure-action: fail

# staggered intervals
  on-failure:
    errors: [unknown]
    action:
      retry:
        attempts: 5
        interval: [10s, 30s, 1m, 5m, 10m]
        failure-action: fail

# simplified retry
  on-failure:
    errors: all
    action: retry
```

### Manual Intervention

```yaml
- run:
    script: go test
  on-failure:
    errors: [all]
    action:
      manual-intervention:
        timeout: 30m
        timeout-action: fail

# with complex timeout action (retry on timeout)
  on-failure:
    errors: [all]
    action:
      manual-intervention:
        timeout: 30m
        timeout-action:
          retry:
            attempts: 10
            interval: 30s
            failure-action: success
```

### Retry with Manual Intervention Fallback

```yaml
  on-failure:
    errors: [unknown]
    action:
      retry:
        attempts: 5
        interval: 10s
        failure-action:
          manual-intervention:
            timeout: 60m
            timeout-action: fail
```

## Caching

```yaml
pipeline:
  stages:
  - steps:
    - run:
        script: npm ci && npm test
    cache:
      path: node_modules              # single path
      key: build.${{ branch }}

# multiple paths
    cache:
      path:
      - /path/to/a/folder
      - /path/to/b/folder

# disabled
    cache:
      disabled: true
```

## Volumes

```yaml
pipeline:
  stages:
  - steps:
    - run:
        script: go build
        container:
          volumes:
            - source: docker
              target: /var/run/docker.sock
    volumes:
    - name: docker
      uses: bind
      with:
        path: /var/run/docker.sock

# temp volume
    volumes:
    - name: home
      uses: temp
```

## Step Properties

Common properties available on all steps:

```yaml
- id: my_step               # unique identifier for referencing outputs
  name: My Step              # display name
  if: ${{ branch == "main" }}  # conditional execution
  timeout: 10m               # step timeout
  delegate: my-delegate      # delegate selector
  strategy:                  # matrix/for/while at step level
    matrix:
      node: [19, 20, 21]
  on-failure:                # failure strategy
    errors: all
    action: ignore
  run:
    script: echo hello
```

## Global Environment Variables

```yaml
pipeline:
  env:
    GOOS: linux
    GOARCH: amd64
  stages:
  - steps:
    - run:
        script: go build
```

## Template Definitions

### Step Template

```yaml
template:
  inputs:
    version:
      type: string
      default: latest
  step:
    run:
      container: node:${{ inputs.version }}
      script:
      - npm install
      - npm test
```

### Multi-Step Template (via group)

```yaml
template:
  inputs:
    version:
      type: string
      default: latest
  step:
    group:
      steps:
      - run:
          container: node:${{ inputs.version }}
          script: npm install
      - run:
          container: node:${{ inputs.version }}
          script: npm test
```

### Stage Template

```yaml
template:
  inputs:
    goos:
      type: string
      default: linux
    version:
      type: string
      default: '1.20'
  stage:
    steps:
    - run:
        container: golang:${{ inputs.version }}
        script: go build
```

## Expressions

```yaml
${{ inputs.branch }}              # input reference
${{ pipeline.sequenceId }}        # build number
${{ branch }}                     # current branch
${{ matrix.go }}                  # matrix value
${{ steps.STEP_ID.output.VAR }}  # step output
${{ iteration.index }}            # loop index
${{ env.HARNESS_ACCOUNT_ID }}    # environment variable
```

## Complete CD Example (Kubernetes Rolling)

```yaml
pipeline:
  inputs:
    skip_dry_run:
      type: boolean
      default: false
  stages:
  - name: deploy
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
          dry-run: true
    - approval:
        uses: harness
        with:
          timeout: 30m
          message: "Approve production deployment?"
          groups: [admins, ops]
          min-approvers: 1
    - action:
        uses: kubernetes-rolling-deploy
        with:
          dry-run: ${{ inputs.skip_dry_run }}
          dry-run-before-deploy: false
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
  env:
    NODE_ENV: production
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
