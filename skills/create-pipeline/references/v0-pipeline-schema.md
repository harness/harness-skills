# v0 Pipeline Schema Reference

Full step type reference for Harness v0 pipelines.

## Build and Push Steps

### BuildAndPushECR
```yaml
- step:
    identifier: push_ecr
    name: Push to ECR
    type: BuildAndPushECR
    spec:
      connectorRef: aws_connector
      region: us-east-1
      account: "123456789012"
      imageName: my-image
      tags: [latest]
```

### BuildAndPushGCR
```yaml
- step:
    identifier: push_gcr
    name: Push to GCR
    type: BuildAndPushGCR
    spec:
      connectorRef: gcp_connector
      host: gcr.io
      projectID: my-project
      imageName: my-image
      tags: [latest]
```

### BuildAndPushACR
```yaml
- step:
    identifier: push_acr
    name: Push to ACR
    type: BuildAndPushACR
    spec:
      connectorRef: azure_connector
      repository: myregistry.azurecr.io/myimage
      tags: [latest]
```

## Cache Steps

### RestoreCacheGCS
```yaml
- step:
    identifier: restore_cache
    name: Restore Cache
    type: RestoreCacheGCS
    spec:
      connectorRef: gcp_connector
      bucket: cache-bucket
      key: cache-{{ checksum "package-lock.json" }}
      archiveFormat: Tar
```

### SaveCacheGCS
```yaml
- step:
    identifier: save_cache
    name: Save Cache
    type: SaveCacheGCS
    spec:
      connectorRef: gcp_connector
      bucket: cache-bucket
      key: cache-{{ checksum "package-lock.json" }}
      sourcePaths: [node_modules]
      archiveFormat: Tar
```

### RestoreCacheS3 / SaveCacheS3
Same structure but with S3-specific fields (region, bucket).

## Upload Steps

### S3Upload
```yaml
- step:
    identifier: upload_s3
    name: Upload to S3
    type: S3Upload
    spec:
      connectorRef: aws_connector
      region: us-east-1
      bucket: my-bucket
      sourcePath: dist/
      target: artifacts/
```

### GCSUpload
```yaml
- step:
    identifier: upload_gcs
    name: Upload to GCS
    type: GCSUpload
    spec:
      connectorRef: gcp_connector
      bucket: my-bucket
      sourcePath: dist/
      target: artifacts/
```

## Kubernetes Steps

### K8sApply
```yaml
- step:
    identifier: k8s_apply
    name: Apply Manifests
    type: K8sApply
    spec:
      filePaths: [manifests/]
      skipDryRun: false
      skipSteadyStateCheck: false
    timeout: 10m
```

### K8sBlueGreenDeploy
```yaml
- step:
    identifier: bg_deploy
    name: Blue Green Deploy
    type: K8sBlueGreenDeploy
    spec:
      skipDryRun: false
    timeout: 10m
```

### K8sCanaryDeploy
```yaml
- step:
    identifier: canary
    name: Canary Deploy
    type: K8sCanaryDeploy
    spec:
      instanceSelection:
        type: Count
        spec:
          count: 1
    timeout: 10m
```

### K8sCanaryDelete
```yaml
- step:
    identifier: canary_delete
    name: Canary Delete
    type: K8sCanaryDelete
    spec: {}
    timeout: 10m
```

### K8sScale
```yaml
- step:
    identifier: scale
    name: Scale
    type: K8sScale
    spec:
      workload: Deployment/my-app
      instanceSelection:
        type: Count
        spec:
          count: 5
    timeout: 10m
```

### K8sDelete
```yaml
- step:
    identifier: delete
    name: Delete Resources
    type: K8sDelete
    spec:
      deleteResources:
        type: ReleaseName
        spec:
          deleteNamespace: false
    timeout: 10m
```

## Helm Steps

### HelmDeploy
```yaml
- step:
    identifier: helm_deploy
    name: Helm Deploy
    type: HelmDeploy
    spec:
      skipDryRun: false
    timeout: 10m
```

### HelmRollback
```yaml
- step:
    identifier: helm_rollback
    name: Helm Rollback
    type: HelmRollback
    spec: {}
    timeout: 10m
```

## Terraform Steps

### TerraformPlan
```yaml
- step:
    identifier: tf_plan
    name: Terraform Plan
    type: TerraformPlan
    spec:
      configuration:
        type: Inline
        spec:
          configFiles:
            store:
              type: Github
              spec:
                connectorRef: git_connector
                repoName: terraform-repo
                branch: main
                folderPath: terraform/
      provisionerIdentifier: my_provisioner
    timeout: 10m
```

### TerraformApply
```yaml
- step:
    identifier: tf_apply
    name: Terraform Apply
    type: TerraformApply
    spec:
      configuration:
        type: InheritFromPlan  # or Inline
      provisionerIdentifier: my_provisioner
    timeout: 10m
```

### TerraformDestroy
```yaml
- step:
    identifier: tf_destroy
    name: Terraform Destroy
    type: TerraformDestroy
    spec:
      configuration:
        type: InheritFromApply
      provisionerIdentifier: my_provisioner
    timeout: 10m
```

## CD Steps

### ShellScript (CD)
```yaml
- step:
    identifier: shell
    name: Run Script
    type: ShellScript
    spec:
      shell: Bash
      source:
        type: Inline
        spec:
          script: |
            echo "Deploying..."
      onDelegate: true
    timeout: 10m
```

### Http
```yaml
- step:
    identifier: http_call
    name: Health Check
    type: Http
    spec:
      url: https://api.example.com/health
      method: GET
      headers:
        - key: Authorization
          value: Bearer <+secrets.getValue("api_token")>
      assertion: <+httpResponseCode> == 200
    timeout: 30s
```

## Stage validation (required by API)

- **Stage name:** Must match `^[a-zA-Z_0-9-.][-0-9a-zA-Z_\\s.]{0,127}$`. No commas; use letters, numbers, spaces, hyphens, underscores, or periods only.
- **failureStrategies:** Every CI and CD stage must include a `failureStrategies` array (Approval stages do not require one). Use `MarkAsFailure` for CI; use `StageRollback` for CD. Example for CI:
  ```yaml
  failureStrategies:
    - onFailure:
        errors: [AllErrors]
        action:
          type: MarkAsFailure
  ```

## HarnessApproval (required by API)

`approvers.disallowPipelineExecutor` is required. Set to `true` so the pipeline executor cannot approve their own run; omit it and the API returns "disallowPipelineExecutor: is missing but it is required".

## CI Steps

### GitClone
```yaml
- step:
    identifier: clone
    name: Clone Repo
    type: GitClone
    spec:
      connectorRef: git_connector
      repoName: my-repo
      build:
        type: branch
        spec:
          branch: main
```

### Background (Service Dependency)
```yaml
- step:
    identifier: postgres
    name: Postgres
    type: Background
    spec:
      connectorRef: dockerhub
      image: postgres:14
      envVariables:
        POSTGRES_PASSWORD: password
      portBindings:
        "5432": "5432"
```

### Plugin
```yaml
- step:
    identifier: slack_notify
    name: Notify Slack
    type: Plugin
    spec:
      connectorRef: dockerhub
      image: plugins/slack
      settings:
        webhook: <+secrets.getValue("slack_webhook")>
        channel: builds
```

### RunTests (Test Intelligence)
```yaml
- step:
    identifier: test
    name: Run Tests
    type: RunTests
    spec:
      language: Java           # Java, Kotlin, Scala, CSharp, Python
      buildTool: Maven         # Maven, Gradle, Bazel, SBT, DotNet, Pytest, Unittest, Nunit
      args: test
      packages: com.mycompany
      runOnlySelectedTests: true
      reports:
        type: JUnit
        spec:
          paths: ["**/surefire-reports/*.xml"]
```

## Step Groups

```yaml
- stepGroup:
    identifier: test_suite
    name: Test Suite
    steps:
      - step: ...
      - step: ...
    failureStrategies:
      - onFailure:
          errors: [AllErrors]
          action:
            type: MarkAsFailure
```

## Notification Rules

```yaml
pipeline:
  notificationRules:
    - name: Notify on Failure
      enabled: true
      pipelineEvents:
        - type: PipelineFailed
        - type: StageFailed
      notificationMethod:
        type: Slack
        spec:
          webhookUrl: <+secrets.getValue("slack_webhook")>
    - name: Email on Success
      enabled: true
      pipelineEvents:
        - type: PipelineSuccess
      notificationMethod:
        type: Email
        spec:
          recipients: [team@example.com]
```

Event types: AllEvents, PipelineStart, PipelineSuccess, PipelineFailed, PipelinePaused, StageStart, StageSuccess, StageFailed, StepFailed

## Expression Reference

| Expression | Description |
|-----------|-------------|
| `<+pipeline.identifier>` | Pipeline ID |
| `<+pipeline.name>` | Pipeline name |
| `<+pipeline.sequenceId>` | Build number |
| `<+pipeline.executionId>` | Execution UUID |
| `<+pipeline.variables.VAR>` | Pipeline variable |
| `<+stage.identifier>` | Current stage ID |
| `<+stage.variables.VAR>` | Stage variable |
| `<+steps.STEP_ID.output.outputVariables.VAR>` | Step output |
| `<+trigger.branch>` | Trigger branch |
| `<+trigger.commitSha>` | Trigger commit |
| `<+trigger.prNumber>` | PR number |
| `<+trigger.sourceBranch>` | PR source branch |
| `<+trigger.targetBranch>` | PR target branch |
| `<+codebase.branch>` | Codebase branch |
| `<+codebase.commitSha>` | Codebase commit |
| `<+secrets.getValue("name")>` | Secret value |
| `<+input>` | Runtime input marker |

## Timeout Formats

`<number><unit>` where unit: `s` (seconds), `m` (minutes), `h` (hours), `d` (days), `w` (weeks)

## Deployment Types

Kubernetes, NativeHelm, Ssh, WinRm, ServerlessAwsLambda, AzureWebApp, AzureFunction, ECS, Elastigroup, TAS, Asg, GoogleCloudFunctions, AwsLambda, AWS_SAM, GoogleCloudRun, CustomDeployment

## Error Types for Failure Strategies

AllErrors, Unknown, Timeout, Authentication, Authorization, Connectivity, DelegateProvisioning, Verification, PolicyEvaluationFailure, InputTimeoutError, ApprovalRejection

## Action Types for Failure Strategies

Ignore, Retry, MarkAsSuccess, Abort, StageRollback, PipelineRollback, ManualIntervention, MarkAsFailure
