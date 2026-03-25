# Pipeline Policies

## Package: `pipeline`
## Root path: `input.pipeline`
## Valid actions: `onrun`, `onsave`, `onstepstart`

## Structural Nesting (CRITICAL for correct Rego)

The pipeline payload has **recursive nesting**. Steps are NOT always at `stages[i].stage.spec.execution.steps[j].step`. They can be nested inside step groups, parallel blocks, or insert nodes — at any depth.

### Stage-level nesting

Each element in `input.pipeline.stages[]` is ONE of:

```
stages[i].stage          — a sequential stage
stages[i].parallel[]     — an array of stages that run concurrently
                            stages[i].parallel[j].stage
```

### Step-level nesting (ExecutionWrapperConfig)

Each element in `stage.spec.execution.steps[]` is exactly ONE of:

```
steps[j].step            — a single step (leaf node)
steps[j].stepGroup       — a step group containing nested steps
steps[j].parallel[]      — an array of steps/stepGroups/inserts that run concurrently
steps[j].insert          — inserted steps (InsertStepsNode)
```

**Step groups** contain their own `steps[]` array with the same structure — so nesting is **recursive**:

```
stage.spec.execution.steps[j].stepGroup.steps[k].step              — step inside group
stage.spec.execution.steps[j].stepGroup.steps[k].stepGroup         — nested group
stage.spec.execution.steps[j].stepGroup.steps[k].parallel[l].step  — parallel inside group
```

**Parallel blocks** are arrays of ExecutionWrapperConfig:

```
stage.spec.execution.steps[j].parallel[k].step                    — step in parallel
stage.spec.execution.steps[j].parallel[k].stepGroup.steps[l].step — step group in parallel
```

**Insert nodes** also contain a `steps[]` array:

```
stage.spec.execution.steps[j].insert.identifier
stage.spec.execution.steps[j].insert.name
stage.spec.execution.steps[j].insert.steps[k].step
```

### Rollback steps

Rollback steps use the **same** recursive structure as execution steps:

```
stage.spec.execution.rollbackSteps[j].step
stage.spec.execution.rollbackSteps[j].stepGroup
stage.spec.execution.rollbackSteps[j].parallel[]
```

### IMPORTANT: Writing policies that find ALL steps

Because of this recursive nesting, a policy that only checks `steps[j].step` will **miss** steps inside step groups, parallel blocks, and inserts. Use one of these approaches:

**Approach 1: Use OPA's `walk()` to find all steps regardless of nesting depth:**
```rego
deny[msg] {
  [path, value] = walk(input.pipeline)
  path[count(path) - 1] == "step"
  value.type == "HarnessApproval"
  value.spec.approvers.disallowPipelineExecutor != true
  msg := sprintf("approval step '%s' must set disallowPipelineExecutor", [value.name])
}
```

**Approach 2: Write separate rules for each nesting level (explicit but verbose):**
```rego
# Direct step
deny[msg] { step := input.pipeline.stages[_].stage.spec.execution.steps[_].step; check(step); msg := format(step) }
# Step in step group
deny[msg] { step := input.pipeline.stages[_].stage.spec.execution.steps[_].stepGroup.steps[_].step; check(step); msg := format(step) }
# Step in parallel
deny[msg] { step := input.pipeline.stages[_].stage.spec.execution.steps[_].parallel[_].step; check(step); msg := format(step) }
# Step in step group inside parallel
deny[msg] { step := input.pipeline.stages[_].stage.spec.execution.steps[_].parallel[_].stepGroup.steps[_].step; check(step); msg := format(step) }
```

**Approach 1 (`walk`) is strongly recommended** for any policy that needs to find steps across all nesting levels.

## Input Schema (key paths)

```
# Pipeline root
input.pipeline.identifier
input.pipeline.name
input.pipeline.orgIdentifier
input.pipeline.projectIdentifier
input.pipeline.tags                                    # object {}
input.pipeline.description

# Pipeline-level properties
input.pipeline.properties.ci.codebase.connectorRef
input.pipeline.properties.ci.codebase.repoName
input.pipeline.properties.ci.codebase.build.type               # "branch", "tag", "PR"
input.pipeline.delegateSelectors[i]

# Template reference (when pipeline/stage/step uses a template)
input.pipeline.template.templateRef
input.pipeline.template.versionLabel
input.pipeline.stages[i].stage.template.templateRef
input.pipeline.stages[i].stage.template.versionLabel

# Git config (when pipeline is stored in Git)
input.pipeline.gitConfig.branch
input.pipeline.gitConfig.filePath

# Sequential stages
input.pipeline.stages[i].stage.identifier
input.pipeline.stages[i].stage.name
input.pipeline.stages[i].stage.type                    # See "Stage Types" below
input.pipeline.stages[i].stage.description
input.pipeline.stages[i].stage.tags                    # object {}
input.pipeline.stages[i].stage.when                    # conditional expression

# Parallel stages
input.pipeline.stages[i].parallel[j].stage.identifier
input.pipeline.stages[i].parallel[j].stage.name
input.pipeline.stages[i].parallel[j].stage.type

# Stage failure strategies
input.pipeline.stages[i].stage.failureStrategies[j].onFailure.action.type
  # "Ignore", "Retry", "MarkAsSuccess", "Abort", "StageRollback",
  # "StepGroupRollback", "PipelineRollback", "ManualIntervention",
  # "ProceedWithDefaultValues", "MarkAsFailure", "RetryStepGroup"
input.pipeline.stages[i].stage.failureStrategies[j].onFailure.errors[k]
  # "Unknown", "AllErrors", "Authentication", "Connectivity", "Timeout",
  # "Authorization", "Verification", "DelegateProvisioning",
  # "PolicyEvaluationFailure", "InputTimeoutError", "ApprovalRejection",
  # "DelegateRestart", "UserMarkedFailure"

# Stage strategy (matrix/parallelism/repeat)
input.pipeline.stages[i].stage.strategy.matrix
input.pipeline.stages[i].stage.strategy.parallelism
input.pipeline.stages[i].stage.strategy.repeat

# --- CD / Deployment stage spec ---

# Service config (v1 style — uses serviceRef)
input.pipeline.stages[i].stage.spec.service.serviceRef
input.pipeline.stages[i].stage.spec.service.serviceInputs
input.pipeline.stages[i].stage.spec.service.useFromStage.stage      # reference another stage's service

# Service config (legacy style)
input.pipeline.stages[i].stage.spec.serviceConfig.service.identifier
input.pipeline.stages[i].stage.spec.serviceConfig.service.name
input.pipeline.stages[i].stage.spec.serviceConfig.serviceDefinition.type     # "Kubernetes"

# Multi-service
input.pipeline.stages[i].stage.spec.services.values[j].serviceRef

# Environment config (v2 style — uses environmentRef)
input.pipeline.stages[i].stage.spec.environment.environmentRef
input.pipeline.stages[i].stage.spec.environment.deployToAll                   # boolean
input.pipeline.stages[i].stage.spec.environment.infrastructureDefinition.type
input.pipeline.stages[i].stage.spec.environment.infrastructureDefinitions[j].identifier
input.pipeline.stages[i].stage.spec.environment.gitOpsClusters[j]
input.pipeline.stages[i].stage.spec.environment.provisioner                   # provisioner execution steps

# Environment config (resolved at runtime — available in onrun payloads)
# When a pipeline runs, Harness resolves the full environment object under
# stage.spec.infrastructure.environment.  This is the most reliable way to
# check environment attributes such as type, because it uses the actual
# entity values rather than relying on identifier string matching.
input.pipeline.stages[i].stage.spec.infrastructure.environment.identifier
input.pipeline.stages[i].stage.spec.infrastructure.environment.name
input.pipeline.stages[i].stage.spec.infrastructure.environment.type          # "Production", "PreProduction"
input.pipeline.stages[i].stage.spec.infrastructure.environment.tags

# Infrastructure definition
input.pipeline.stages[i].stage.spec.infrastructure.infrastructureDefinition.type  # See "Infrastructure Types"
input.pipeline.stages[i].stage.spec.infrastructure.infrastructureDefinition.spec.namespace
input.pipeline.stages[i].stage.spec.infrastructure.infrastructureDefinition.spec.connectorRef
input.pipeline.stages[i].stage.spec.infrastructure.infrastructureDefinition.spec.cluster
input.pipeline.stages[i].stage.spec.infrastructure.infrastructureDefinition.spec.releaseName

# Multi-environment
input.pipeline.stages[i].stage.spec.environments.values[j].environmentRef
input.pipeline.stages[i].stage.spec.environments.values[j].infrastructureDefinitions[k]

# Environment group
input.pipeline.stages[i].stage.spec.environmentGroup.envGroupRef
input.pipeline.stages[i].stage.spec.environmentGroup.environments[j].environmentRef
input.pipeline.stages[i].stage.spec.environmentGroup.deployToAll

# GitOps enabled
input.pipeline.stages[i].stage.spec.gitOpsEnabled                            # boolean

# Deployment type
input.pipeline.stages[i].stage.spec.deploymentType                           # "Kubernetes", "NativeHelm", "Ssh", etc.

# --- Execution steps (see "Structural Nesting" above for all paths) ---
input.pipeline.stages[i].stage.spec.execution.steps[j].step.identifier
input.pipeline.stages[i].stage.spec.execution.steps[j].step.name
input.pipeline.stages[i].stage.spec.execution.steps[j].step.type            # See "Step Types" below
input.pipeline.stages[i].stage.spec.execution.steps[j].step.timeout         # "10m", "1d", etc.
input.pipeline.stages[i].stage.spec.execution.steps[j].step.spec            # step-type-specific
input.pipeline.stages[i].stage.spec.execution.steps[j].step.when            # conditional
input.pipeline.stages[i].stage.spec.execution.steps[j].step.failureStrategies[k]
input.pipeline.stages[i].stage.spec.execution.steps[j].step.template.templateRef  # if step uses a template

# Step group
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.identifier
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.name
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.steps[k]   # recursive ExecutionWrapperConfig
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.delegateSelectors[k]
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.when
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.failureStrategies[k]
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.strategy   # matrix/parallelism
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.template.templateRef  # step group from template
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.stepGroupInfra        # container infra for step group
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.variables[k]
input.pipeline.stages[i].stage.spec.execution.steps[j].stepGroup.sharedPaths[k]

# Parallel steps
input.pipeline.stages[i].stage.spec.execution.steps[j].parallel[k].step
input.pipeline.stages[i].stage.spec.execution.steps[j].parallel[k].stepGroup
input.pipeline.stages[i].stage.spec.execution.steps[j].parallel[k].insert

# Insert steps (InsertStepsNode)
input.pipeline.stages[i].stage.spec.execution.steps[j].insert.identifier
input.pipeline.stages[i].stage.spec.execution.steps[j].insert.name
input.pipeline.stages[i].stage.spec.execution.steps[j].insert.steps[k]     # recursive ExecutionWrapperConfig

# Rollback steps (same recursive structure as execution steps)
input.pipeline.stages[i].stage.spec.execution.rollbackSteps[j].step
input.pipeline.stages[i].stage.spec.execution.rollbackSteps[j].stepGroup
input.pipeline.stages[i].stage.spec.execution.rollbackSteps[j].parallel[]

# --- Step-type-specific spec fields ---

# HarnessApproval step
.step.spec.approvers.minimumCount
.step.spec.approvers.userGroups[k]
.step.spec.approvers.serviceAccounts[k]
.step.spec.approvers.disallowPipelineExecutor              # boolean — prevents executor from self-approving
.step.spec.approvers.disallowedUserEmails[k]
.step.spec.approvalMessage
.step.spec.includePipelineExecutionHistory                  # boolean
.step.spec.approverInputs[k].name
.step.spec.autoApproval

# JiraApproval step
.step.spec.connectorRef
.step.spec.issueKey
.step.spec.issueType
.step.spec.projectKey
.step.spec.approvalCriteria
.step.spec.rejectionCriteria
.step.spec.retryInterval

# ServiceNowApproval step
.step.spec.connectorRef
.step.spec.ticketNumber
.step.spec.ticketType
.step.spec.approvalCriteria
.step.spec.rejectionCriteria
.step.spec.changeWindow

# CustomApproval step
.step.spec.shell                                           # "Bash", "PowerShell"
.step.spec.source
.step.spec.approvalCriteria
.step.spec.rejectionCriteria
.step.spec.retryInterval
.step.spec.scriptTimeout

# ShellScript step
.step.spec.shell                                           # "Bash", "PowerShell"
.step.spec.onDelegate                                      # true/false
.step.spec.source.type                                     # "Inline"
.step.spec.source.spec.script                              # the script body
.step.spec.environmentVariables[k]
.step.spec.outputVariables[k]
.step.spec.executionTarget

# Http step
.step.spec.url
.step.spec.method                                          # "GET", "POST", "PUT", "DELETE", etc.
.step.spec.headers[k].key
.step.spec.headers[k].value
.step.spec.body
.step.spec.assertion
.step.spec.inputVariables
.step.spec.outputVariables

# K8sRollingDeploy step
.step.spec.skipDryRun                                      # boolean
.step.spec.pruningEnabled                                  # boolean
.step.spec.delegateSelectors[k]
.step.spec.commandFlags[k]

# K8sCanaryDeploy step
.step.spec.instanceSelection                               # count or percentage
.step.spec.skipDryRun
.step.spec.trafficRouting

# K8sBlueGreenDeploy step
.step.spec.skipDryRun
.step.spec.pruningEnabled
.step.spec.skipDeploymentIfSameManifest
.step.spec.trafficRouting

# K8sApply step
.step.spec.filePaths[k]
.step.spec.skipDryRun
.step.spec.skipRendering
.step.spec.skipSteadyStateCheck
.step.spec.overrides[k]

# TerraformPlan / TerraformApply / TerraformDestroy step
.step.spec.provisionerIdentifier
.step.spec.configuration.type                              # "Inline", "InheritFromPlan"
.step.spec.configuration.spec.configFiles.store.type
.step.spec.delegateSelectors[k]

# Policy step
.step.spec.policySets[k]
.step.spec.type                                            # "Custom"
.step.spec.policySpec

# JiraCreate / JiraUpdate step
.step.spec.connectorRef
.step.spec.projectKey
.step.spec.issueType
.step.spec.fields[k]

# ServiceNowCreate / ServiceNowUpdate step
.step.spec.connectorRef
.step.spec.ticketType
.step.spec.fields[k]

# Email step
.step.spec.to
.step.spec.cc
.step.spec.subject
.step.spec.body

# Barrier step
.step.spec.barrierRef

# Wait step
.step.spec.duration

# FlagConfiguration step
.step.spec.feature
.step.spec.environment
.step.spec.instructions[k]

# Run step (CI)
.step.spec.command
.step.spec.shell                                           # "Sh", "Bash", "Powershell", "Pwsh", "Python"
.step.spec.image
.step.spec.connectorRef
.step.spec.envVariables
.step.spec.outputVariables[k]
.step.spec.resources
.step.spec.privileged
.step.spec.runAsUser
.step.spec.imagePullPolicy                                 # "Always", "Never", "IfNotPresent"
.step.spec.reports

# BuildAndPushDockerRegistry step (CI)
.step.spec.connectorRef
.step.spec.repo
.step.spec.tags[k]
.step.spec.dockerfile
.step.spec.context
.step.spec.target
.step.spec.buildArgs
.step.spec.labels
.step.spec.caching
.step.spec.optimize
.step.spec.resources

# CI stage specific
input.pipeline.stages[i].stage.spec.platform.os            # "Linux", "MacOS", "Windows"
input.pipeline.stages[i].stage.spec.platform.arch           # "Amd64", "Arm64"
input.pipeline.stages[i].stage.spec.runtime.type            # "Cloud", "Machine", "Docker"
input.pipeline.stages[i].stage.spec.runtime.spec
input.pipeline.stages[i].stage.spec.caching
input.pipeline.stages[i].stage.spec.cloneCodebase            # boolean
input.pipeline.stages[i].stage.spec.infrastructure.spec.namespace  # CI K8s namespace
input.pipeline.stages[i].stage.spec.sharedPaths[j]
input.pipeline.stages[i].stage.spec.serviceDependencies[j]
```

## Stage Types

(from harness-schema: `deployment-stage-node.yaml`, `integration-stage-node.yaml`, `approval-stage-node.yaml`, `custom-stage-node.yaml`, `feature-flag-stage-node.yaml`, `security-node.yaml`)

| Stage Type | Description | Key Spec Fields |
|---|---|---|
| `Deployment` | CD deployment stage | `serviceConfig`, `infrastructure`, `execution` |
| `CI` | Continuous Integration stage | `execution`, `infrastructure.spec.namespace`, `platform` |
| `Approval` | Approval gate stage | `execution` (contains approval steps) |
| `Custom` | Custom/generic stage | `execution` |
| `Security` | Security testing stage | `execution` (contains STO steps) |
| `FeatureFlag` | Feature flag stage | `execution` (contains FF steps) |
| `IACM` | Infrastructure as Code Management | `execution` (IACM-specific steps) |
| `Pipeline` | Chained pipeline stage | `org`, `project`, `pipeline`, `inputs` |

## Step Types

(from harness-schema: `execution-wrapper-config.yaml` and step node files)

### Common Steps
`ShellScript`, `Http`, `HarnessApproval`, `JiraApproval`, `ServiceNowApproval`, `CustomApproval`, `JiraCreate`, `JiraUpdate`, `ServiceNowCreate`, `ServiceNowUpdate`, `ServiceNowImportSet`, `Email`, `Barrier`, `Queue`, `Wait`, `Policy`, `FlagConfiguration`

### CD / Deployment Steps
`K8sRollingDeploy`, `K8sRollingRollback`, `K8sBlueGreenDeploy`, `K8sBGSwapServices`, `K8sCanaryDeploy`, `K8sCanaryDelete`, `K8sScale`, `K8sDelete`, `K8sApply`, `K8sDryRunManifest`, `HelmDeploy`, `HelmRollback`, `TerraformPlan`, `TerraformApply`, `TerraformDestroy`, `TerraformRollback`, `TerragruntPlan`, `TerragruntApply`, `TerragruntDestroy`, `TerragruntRollback`, `CloudformationCreateStack`, `CloudformationDeleteStack`, `CloudformationRollback`, `EcsRollingDeploy`, `EcsRollingRollback`, `EcsCanaryDeploy`, `EcsBlueGreenCreateService`, `EcsBlueGreenSwapTargetGroups`, `ServerlessAwsLambdaDeploy`, `ServerlessAwsLambdaRollback`, `AzureWebAppSlotDeployment`, `AzureWebAppSwapSlot`, `AzureWebAppTrafficShift`, `AzureWebAppRollback`, `AzureCreateARMResource`, `AzureARMRollback`, `AsgSetup`, `AsgRollingDeploy`, `AsgRollingRollback`, `AsgBlueGreenDeploy`, `AsgBlueGreenRollback`, `GoogleFunctionsDeploy`, `GoogleFunctionsRollback`, `GoogleCloudRunDeploy`, `GoogleCloudRunRollback`, `AwsLambdaDeploy`, `AwsLambdaRollback`, `AwsSamBuild`, `AwsSamDeploy`, `AwsSamRollback`, `Command`, `ShellScriptProvision`, `MergePR`, `RevertPR`, `UpdateReleaseRepo`, `SyncStep`, `FetchLinkedApps`, `UpdateGitOpsApp`, `DownloadManifests`, `DownloadAwsS3`, `Chaos`

### CI / Build Steps
`Run`, `RunTests`, `BuildAndPushDockerRegistry`, `BuildAndPushGCR`, `BuildAndPushECR`, `BuildAndPushACR`, `BuildAndPushGAR`, `GitClone`, `Plugin`, `RestoreCacheGCS`, `RestoreCacheS3`, `SaveCacheGCS`, `SaveCacheS3`, `Background`, `Action`, `Bitrise`

### Security / STO Steps
`AquaTrivy`, `Bandit`, `BlackDuck`, `BurpScan`, `Checkmarx`, `Grype`, `Mend`, `Nikto`, `Nmap`, `Prowler`, `Qualys`, `Snyk`, `Sonarqube`, `Veracode`, `Zap`, `SscaOrchestration`, `SscaEnforcement`, `VerifyAttestation`

### Verification Steps
`Verify`, `AnalyzeDeployment`

### IACM Steps
`IACMTerraformPlan`, `IACMTerraformApply`, `IACMTerraformDestroy`, `IACMTerragruntPlan`, `IACMOpenTofuPlan`, `IACMAnsiblePlan`

### DB DevOps Steps
`DbopsApplySchema`, `DbopsRollbackSchema`

### AWS CDK Steps
`AwsCdkBootstrap`, `AwsCdkSynth`, `AwsCdkDiff`, `AwsCdkDeploy`, `AwsCdkDestroy`

## Infrastructure Types

(from harness-schema: `infrastructure-def.yaml`)

| Type | Description |
|---|---|
| `KubernetesDirect` | Direct K8s cluster |
| `KubernetesGcp` | K8s on GCP |
| `KubernetesAzure` | K8s on Azure |
| `KubernetesAws` | K8s on AWS |
| `KubernetesRancher` | K8s via Rancher |
| `Pdc` | Physical Data Center |
| `SshWinRmAws` | SSH/WinRM on AWS |
| `SshWinRmAzure` | SSH/WinRM on Azure |
| `ServerlessAwsLambda` | AWS Lambda (Serverless) |
| `ECS` | Amazon ECS |
| `Elastigroup` | Spot Elastigroup |
| `TAS` | Tanzu Application Service |
| `Asg` | AWS Auto Scaling Group |
| `GoogleCloudFunctions` | Google Cloud Functions |
| `GoogleCloudRun` | Google Cloud Run |
| `AzureWebApp` | Azure Web App |
| `AWS_SAM` | AWS SAM |
| `AwsLambda` | AWS Lambda |
| `CustomDeployment` | Custom deployment infra |

## Example 1: Require approval step (walk-based, finds steps at ANY nesting depth)

**Scenario:** Every deployment stage must have a HarnessApproval step — even if it's inside a step group or parallel block.

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "Deployment"
	not stage_has_approval(stage)
	msg := sprintf("deployment stage '%s' does not have a HarnessApproval step", [stage.name])
}

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}

stage_has_approval(stage) {
	[_, value] = walk(stage.spec.execution)
	value.type == "HarnessApproval"
}
```

## Example 2: Require specific steps (walk-based)

**Scenario:** All deployment stages must contain JiraUpdate and HarnessApproval steps (at any nesting depth).

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "Deployment"
	required_step := required_steps[_]
	not stage_has_step_type(stage, required_step)
	msg := sprintf("deployment stage '%s' is missing required step '%s'", [stage.name, required_step])
}

required_steps = ["JiraUpdate", "HarnessApproval"]

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}

stage_has_step_type(stage, step_type) {
	[_, value] = walk(stage.spec.execution)
	value.type == step_type
}
```

## Example 3: Restrict deployment environments

**Scenario:** Deployments can only target specific environments. Handles both v2 (`environment.environmentRef`) and legacy (`infrastructure.environment.identifier`) schema.

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "Deployment"
	env_id := get_environment_id(stage)
	not array_contains(allowed_environments, env_id)
	msg := sprintf("deployment stage '%s' cannot be deployed to environment '%s'", [stage.name, env_id])
}

allowed_environments = ["demoprod", "stage"]

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}

get_environment_id(stage) = id {
	id := stage.spec.environment.environmentRef
}

get_environment_id(stage) = id {
	id := stage.spec.infrastructure.environment.identifier
}

array_contains(arr, elem) {
	arr[_] = elem
}
```

## Example 4: Forbid specific step types (walk-based, catches nested steps)

**Scenario:** ShellScript steps are not allowed anywhere in deployment stages — including inside step groups, parallel blocks, or inserts.

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "Deployment"
	[path, value] = walk(stage.spec.execution)
	path[count(path) - 1] == "step"
	array_contains(forbidden_steps, value.type)
	msg := sprintf("deployment stage '%s' has forbidden '%s' step '%s'", [stage.name, value.type, value.name])
}

forbidden_steps = ["ShellScript"]

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}

array_contains(arr, elem) {
	arr[_] = elem
}
```

## Example 5: Forbid specific shell commands (walk-based)

**Scenario:** Shell scripts must not contain `rm` or `ls` commands — finds ShellScript steps at any depth.

```rego
package pipeline

deny[msg] {
	[_, step] = walk(input.pipeline)
	step.type == "ShellScript"
	shell := step.spec.source.spec.script
	lines := split(shell, "\n")
	regex.match(forbidden_commands[j].regex, trim_space(lines[i]))
	msg := sprintf("shell step '%s' uses forbidden command '%s': %s", [step.name, forbidden_commands[j].label, lines[i]])
}

forbidden_commands = [
	{"regex": "^rm|\\srm\\s", "label": "rm"},
	{"regex": "ls|\\sls\\s", "label": "ls"},
]
```

## Example 6: Enforce step timeouts (walk-based)

**Scenario:** K8sRollingDeploy steps must have a timeout of at least 10 minutes — regardless of nesting.

```rego
package pipeline

deny[msg] {
	[_, step] = walk(input.pipeline)
	step.type == "K8sRollingDeploy"
	step.timeout
	time.parse_duration_ns(step.timeout) < time.parse_duration_ns("10m")
	msg := sprintf("step '%s' has timeout under 10m", [step.identifier])
}

deny[msg] {
	[_, step] = walk(input.pipeline)
	step.type == "K8sRollingDeploy"
	not step.timeout
	msg := sprintf("step '%s' has no timeout", [step.identifier])
}
```

## Example 7: Restrict CI registry host

**Scenario:** Container images can only be pushed to an approved GCR host.

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "CI"
	[_, step] = walk(stage.spec.execution)
	step.type == "BuildAndPushGCR"
	step.spec.host != "us.gcr.io"
	msg := sprintf("CI stage '%s' cannot push images to host '%s'", [stage.name, step.spec.host])
}

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}
```

## Example 8: Require security test steps (walk-based)

**Scenario:** CI/Security stages must include at least one security scan step — found at any depth.

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	stage.type == "CI"
	not stage_has_security_step(stage)
	msg := sprintf("CI stage '%s' does not have a required security test step", [stage.name])
}

deny[msg] {
	stage := all_stages[_]
	stage.type == "Security"
	not stage_has_security_step(stage)
	msg := sprintf("Security stage '%s' does not have a required security test step", [stage.name])
}

security_steps = ["AquaTrivy", "Bandit", "BlackDuck", "BurpScan", "Checkmarx", "Grype", "Mend", "Nikto", "Nmap", "Prowler", "Qualys", "Snyk", "Sonarqube", "Veracode", "Zap"]

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}

stage_has_security_step(stage) {
	[_, value] = walk(stage.spec.execution)
	array_contains(security_steps, value.type)
}

array_contains(arr, elem) {
	arr[_] = elem
}
```

## Example 9: Enforce disallowPipelineExecutor on all approval steps (walk-based)

**Scenario:** All HarnessApproval steps must set `disallowPipelineExecutor` to `true` — regardless of nesting inside step groups or parallel blocks.

```rego
package pipeline

deny[msg] {
	[_, step] = walk(input.pipeline)
	step.type == "HarnessApproval"
	step.spec.approvers.disallowPipelineExecutor != true
	msg := sprintf("approval step '%s' must set disallowPipelineExecutor to true", [step.name])
}
```

## Example 10: Deny Deployment stages (including parallel) without preceding Approval

**Scenario:** Every Deployment stage — whether sequential or inside a parallel group — must have an Approval stage in the immediately preceding stage slot.

```rego
package pipeline

deny[msg] {
	group := input.pipeline.stages[i].parallel
	stage := group[_].stage
	stage.type == "Deployment"
	not has_approval_before(i)
	msg := sprintf("deployment stage '%s' is in a parallel group at index %d without an Approval stage before it", [stage.name, i])
}

deny[msg] {
	input.pipeline.stages[i].stage.type == "Deployment"
	not has_approval_before(i)
	msg := sprintf("deployment stage '%s' (index %d) does not have an Approval stage before it", [input.pipeline.stages[i].stage.name, i])
}

has_approval_before(i) {
	i > 0
	input.pipeline.stages[i - 1].stage.type == "Approval"
}

has_approval_before(i) {
	i > 0
	input.pipeline.stages[i - 1].parallel[_].stage.type == "Approval"
}
```

## Example 11: Enforce failure strategies on all stages

**Scenario:** Every stage must have a failure strategy defined with at least one error type.

```rego
package pipeline

deny[msg] {
	stage := all_stages[_]
	not stage.failureStrategies
	msg := sprintf("stage '%s' has no failure strategy defined", [stage.name])
}

deny[msg] {
	stage := all_stages[_]
	count(stage.failureStrategies) == 0
	msg := sprintf("stage '%s' has an empty failure strategy list", [stage.name])
}

all_stages[stage] {
	stage := input.pipeline.stages[_].stage
}

all_stages[stage] {
	stage := input.pipeline.stages[_].parallel[_].stage
}
```

## Example 12: Enforce step group delegate selectors

**Scenario:** Step groups must specify delegate selectors to control where they execute.

```rego
package pipeline

deny[msg] {
	[path, value] = walk(input.pipeline)
	path[count(path) - 1] == "stepGroup"
	not value.delegateSelectors
	msg := sprintf("step group '%s' must specify delegateSelectors", [value.name])
}
```

## Sample Input JSON (with step groups and parallel steps)

```json
{
  "pipeline": {
    "identifier": "demo",
    "name": "demo",
    "orgIdentifier": "default",
    "projectIdentifier": "demo",
    "stages": [
      {
        "stage": {
          "identifier": "approval_stage",
          "name": "Approval Gate",
          "type": "Approval",
          "spec": {
            "execution": {
              "steps": [
                {
                  "step": {
                    "identifier": "approval1",
                    "name": "Manager Approval",
                    "type": "HarnessApproval",
                    "timeout": "1d",
                    "spec": {
                      "approvers": {
                        "minimumCount": 1,
                        "userGroups": ["managers"],
                        "disallowPipelineExecutor": true
                      }
                    }
                  }
                }
              ]
            }
          }
        }
      },
      {
        "stage": {
          "identifier": "deploy",
          "name": "deploy",
          "type": "Deployment",
          "failureStrategies": [
            {
              "onFailure": {
                "errors": ["AllErrors"],
                "action": {"type": "StageRollback"}
              }
            }
          ],
          "spec": {
            "deploymentType": "Kubernetes",
            "service": {
              "serviceRef": "my_service"
            },
            "environment": {
              "environmentRef": "prod",
              "infrastructureDefinitions": [
                {
                  "identifier": "k8s_prod",
                  "type": "KubernetesDirect",
                  "spec": {
                    "connectorRef": "k8s_cluster",
                    "namespace": "production",
                    "releaseName": "app-release"
                  }
                }
              ]
            },
            "execution": {
              "steps": [
                {
                  "stepGroup": {
                    "identifier": "pre_deploy_checks",
                    "name": "Pre-Deploy Checks",
                    "delegateSelectors": ["prod-delegate"],
                    "steps": [
                      {
                        "parallel": [
                          {
                            "step": {
                              "identifier": "lint",
                              "name": "Lint Check",
                              "type": "ShellScript",
                              "timeout": "5m",
                              "spec": {
                                "shell": "Bash",
                                "source": {"type": "Inline", "spec": {"script": "echo lint"}}
                              }
                            }
                          },
                          {
                            "step": {
                              "identifier": "sec_scan",
                              "name": "Security Scan",
                              "type": "AquaTrivy",
                              "timeout": "10m",
                              "spec": {}
                            }
                          }
                        ]
                      }
                    ]
                  }
                },
                {
                  "step": {
                    "identifier": "rolloutDeployment",
                    "name": "Rollout Deployment",
                    "type": "K8sRollingDeploy",
                    "timeout": "10m",
                    "spec": {"skipDryRun": false, "pruningEnabled": true}
                  }
                }
              ],
              "rollbackSteps": [
                {
                  "step": {
                    "identifier": "rollback",
                    "name": "Rollback",
                    "type": "K8sRollingRollback",
                    "timeout": "10m",
                    "spec": {}
                  }
                }
              ]
            }
          }
        }
      },
      {
        "parallel": [
          {
            "stage": {
              "identifier": "notify_slack",
              "name": "Notify Slack",
              "type": "Custom",
              "spec": {
                "execution": {
                  "steps": [
                    {
                      "step": {
                        "identifier": "email",
                        "name": "Send Email",
                        "type": "Email",
                        "timeout": "5m",
                        "spec": {
                          "to": "team@company.com",
                          "subject": "Deploy Complete",
                          "body": "Deployment finished."
                        }
                      }
                    }
                  ]
                }
              }
            }
          },
          {
            "stage": {
              "identifier": "jira_update",
              "name": "Update Jira",
              "type": "Custom",
              "spec": {
                "execution": {
                  "steps": [
                    {
                      "step": {
                        "identifier": "jira1",
                        "name": "Update Ticket",
                        "type": "JiraUpdate",
                        "timeout": "5m",
                        "spec": {
                          "connectorRef": "jira_conn",
                          "issueKey": "<+pipeline.variables.jiraKey>",
                          "fields": [{"name": "Status", "value": "Done"}]
                        }
                      }
                    }
                  ]
                }
              }
            }
          }
        ]
      }
    ]
  },
  "metadata": {
    "type": "pipeline",
    "action": "onrun",
    "user": {"name": "Rishabh Gupta", "email": "rishabh.gupta@harness.io"},
    "roleAssignmentMetadata": [
      {"roleIdentifier": "_account_admin", "roleName": "Account Admin"}
    ]
  }
}
```

**Key patterns:**
- When writing policies that inspect `stages`, always handle both `stages[i].stage` (sequential) and `stages[i].parallel[j].stage` (parallel).
- When writing policies that inspect `steps`, use `walk()` to find steps at any nesting depth (inside step groups, parallel blocks, and insert nodes). Only use explicit path enumeration if you need positional/ordering information.
- A helper `all_stages` rule is a clean pattern to normalize both sequential and parallel stages into a single set.
