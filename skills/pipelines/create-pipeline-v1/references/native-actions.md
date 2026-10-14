# Harness v1 Native Actions Reference

Always prefer native action steps and template steps over generic `run:` steps. Native actions provide built-in error handling, steady-state checks, rollback support, UI integration, and telemetry that shell scripts cannot match.

## Step Selection Priority

1. **Use an `action:` step** if a Harness action exists for the task
2. **Use a `template:` step** if a step template exists in the template library
3. **Use a `run:` step** only for custom build/test/lint commands with no native equivalent

## How to Reference Native Steps in v1

### Action syntax (spec-defined actions)

```yaml
- action:
    uses: <action-name>
    with:
      param: value
```

### Template syntax (template library steps)

```yaml
- template:
    uses: <templateId>@<version>
    with:
      param: value
```

## Kubernetes Deployment

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Rolling deploy | `action: uses: kubernetes-rolling-deploy` or `template: uses: k8sRollingDeployStep` | `run: kubectl apply` |
| Rolling rollback | `template: uses: k8sRollingRollbackStep` | `run: kubectl rollout undo` |
| Blue-green deploy | `action: uses: kubernetes-blue-green-deploy` or `template: uses: k8sBlueGreenDeployStep` | Complex kubectl scripts |
| Blue-green swap | `action: uses: kubernetes-blue-green-swap` or `template: uses: k8sBlueGreenSwapServicesSelectorsStep` | `run: kubectl patch` |
| Blue-green scale down | `action: uses: kubernetes-blue-green-scale-down` or `template: uses: k8sBlueGreenStageScaleDownStep` | `run: kubectl scale --replicas=0` |
| Canary deploy | `action: uses: kubernetes-canary-deploy` or `template: uses: k8sCanaryDeployStep` | Partial kubectl apply |
| Canary delete | `action: uses: kubernetes-canary-delete` or `template: uses: k8sCanaryDeleteStep` | `run: kubectl delete` |
| Apply manifests | `template: uses: k8sApplyStep` | `run: kubectl apply` |
| Scale workload | `action: uses: kubernetes-scale` or `template: uses: k8sScaleStep` | `run: kubectl scale` |
| Delete resources | `action: uses: kubernetes-delete` or `template: uses: k8sDeleteStep` | `run: kubectl delete` |
| Diff / Dry run | `template: uses: k8sDiffStep` | `run: kubectl diff` |
| Patch resources | `template: uses: k8sPatchStep` | `run: kubectl patch` |
| Traffic routing | `template: uses: k8sTrafficRoutingStep` | `run: kubectl edit ingress` |
| Steady state check | `template: uses: k8sSteadyStateCheckStep` | `run: kubectl rollout status` |
| Rollout operations | `template: uses: k8sRolloutStep` | `run: kubectl rollout` |
| Download manifests | `action: uses: manifest-download` | `run: git clone` |
| Render templates | `action: uses: manifest-bake` | `run: helm template` / `kustomize build` |

### k8sRollingDeployStep Key Inputs

```yaml
- template:
    uses: k8sRollingDeployStep@1.0.0
    with:
      skip_dry_run: false
      pruning: false
      print_manifests: true
      server_side_apply: false
      log_level: info
```

## Helm Deployment

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Helm deploy (basic) | `action: uses: helm-deploy` or `template: uses: helmDeployBasicStep` | `run: helm upgrade --install` |
| Helm blue-green deploy | `template: uses: helmDeployBluegreenStep` | Complex helm scripts |
| Helm canary deploy | `template: uses: helmDeployCanaryStep` | Complex helm scripts |
| Helm rollback | `action: uses: helm-rollback` or `template: uses: helmRollbackStep` | `run: helm rollback` |
| Helm delete | `template: uses: helmDeleteStep` | `run: helm uninstall` |
| Helm blue-green swap | `template: uses: helmBluegreenSwapStep` | Custom swap scripts |

### helmDeployBasicStep Key Inputs

```yaml
- template:
    uses: helmDeployBasicStep@1.0.0
    with:
      ignore_failed_release: false
      skip_deploy_steady_check: false
      upgrade_with_install: true
      deploy_test: false
      server_render: false
      log_level: info
```

## AWS ECS Deployment

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| ECS blue-green deploy | `template: uses: ecsBluegreenDeployStep` | `run: aws ecs create-service` |
| ECS swap target groups | `template: uses: ecsBluegreenSwapTargetGroupsStep` | `run: aws elbv2 modify-listener` |
| ECS rollback | `template: uses: ecsBluegreenRollbackStep` | Complex ECS rollback scripts |
| ECS traffic shift | `template: uses: ecsBluegreenTrafficShiftStep` | `run: aws elbv2 modify-rule` |
| ECS run task | `template: uses: ecsRunTaskStep` | `run: aws ecs run-task` |

### ecsBluegreenDeployStep Key Inputs

```yaml
- template:
    uses: ecsBluegreenDeployStep@1.0.0
    with:
      connector: aws_connector
      cluster: my-cluster
      region: us-east-1
      task_def_mode: inline
```

## AWS Serverless & Lambda

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| SAM build | `template: uses: awsSamBuildStep` | `run: sam build` |
| SAM deploy | `template: uses: awsSamDeployStep` | `run: sam deploy` |
| Serverless deploy | `template: uses: serverlessDeployStep` | `run: serverless deploy` |
| Serverless package | `template: uses: serverlessPackageStep` | `run: serverless package` |
| Serverless rollback | `template: uses: serverlessRollbackStep` | `run: serverless rollback` |
| CDK deploy | `template: uses: awsCdkDeployStep` | `run: cdk deploy` |
| CDK destroy | `template: uses: awsCdkDestroyStep` | `run: cdk destroy` |

## Azure Deployment

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Azure Function deploy | `template: uses: azureFunctionDeployStep` | `run: func azure functionapp publish` |
| Azure Function rollback | `template: uses: azureFunctionRollbackStep` | Complex rollback scripts |

## Google Cloud Deployment

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Cloud Run deploy | `template: uses: googleCloudRunDeploy` | `run: gcloud run deploy` |
| Cloud Run job | `template: uses: googleCloudRunJob` | `run: gcloud run jobs create` |
| Cloud Run rollback | `template: uses: googleCloudRunRollback` | Complex rollback scripts |
| Cloud Run traffic shift | `template: uses: googleCloudRunTrafficShift` | `run: gcloud run services update-traffic` |

## Infrastructure as Code

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Terraform (plan, apply, destroy, etc.) | `action: uses: terraform-plan` or `template: uses: terraformStep` | `run: terraform plan/apply/destroy` |
| OpenTofu | `template: uses: openTofuStep` | `run: tofu plan/apply/destroy` |
| TFLint | `template: uses: tfLintStep` | `run: tflint` |

### terraformStep Key Inputs

```yaml
- template:
    uses: terraformStep@1.0.0
    with:
      command: plan    # init, plan, apply, destroy, plan-destroy, validate, import
```

## CI Build & Push

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Build + push to Docker Hub | `template: uses: buildAndPushToDocker` | `run: docker build && docker push` |
| Build + push to AWS ECR | `template: uses: buildAndPushToECR` | `run: docker build && aws ecr` |
| Build + push to Google GAR | `template: uses: buildAndPushToGAR` | `run: docker build && gcloud` |
| Build + push to Harness Registry | `template: uses: buildAndPushToHAR` | `run: docker build && docker push` |

### buildAndPushToDocker Key Inputs

```yaml
- template:
    uses: buildAndPushToDocker@1.0.0
    with:
      connector: dockerhub
      repo: myorg/myimage
      tags: [${{ pipeline.sequenceId }}, latest]
      dockerfile: Dockerfile
      context: .
```

## Artifact Upload

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Upload to S3 | `template: uses: uploadArtifactsToS3` | `run: aws s3 cp` |
| Upload to GCS | `template: uses: uploadArtifactsToGCS` | `run: gsutil cp` |
| Upload to Artifactory | `template: uses: uploadArtifactsToJfrogArtifactory` | `run: curl -X PUT` |

## Cache

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Save cache to S3 | `template: uses: saveCacheToS3` | `run: aws s3 cp` |
| Restore cache from S3 | `template: uses: restoreCacheFromS3` | `run: aws s3 cp` |
| Save cache to GCS | `template: uses: saveCacheToGCS` | `run: gsutil cp` |
| Restore cache from GCS | `template: uses: restoreCacheFromGCS` | `run: gsutil cp` |

Note: v1 pipelines also have built-in `cache:` at the stage level for cache intelligence. Use that for automatic caching and the template steps for explicit cache control.

## Git Operations

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Clone a repo | `action: uses: git-clone` or `template: uses: gitCloneStep` | `run: git clone` |

## Approvals

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Manual approval | `approval: uses: harness` (stage-level) | Custom polling scripts |
| Jira approval | `approval: uses: jira` or `template: uses: jiraApproval` | `run: curl Jira API` |
| ServiceNow approval | `template: uses: serviceNowApproval` | `run: curl ServiceNow API` |

### Harness Approval (stage-level)

```yaml
- approval:
    uses: harness
    with:
      timeout: 30m
      message: "Approve deployment?"
      groups: [admins, ops]
      min-approvers: 1
```

## Ticketing & Notifications

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Create Jira issue | `action: uses: jira-create` or `template: uses: jiraCreate` | `run: curl Jira API` |
| Update Jira issue | `action: uses: jira-update` or `template: uses: jiraUpdate` | `run: curl Jira API` |
| Create ServiceNow ticket | `action: uses: snow-create` or `template: uses: serviceNowCreate` | `run: curl ServiceNow API` |
| Update ServiceNow ticket | `action: uses: snow-update` or `template: uses: serviceNowUpdate` | `run: curl ServiceNow API` |
| ServiceNow import set | `template: uses: serviceNowImportSet` | `run: curl ServiceNow API` |
| HTTP request | `action: uses: http` or `template: uses: httpStep` | `run: curl` |
| Send email | `template: uses: email` | `run: sendmail` |

## Security Scanning

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Secret detection | `template: uses: gitleaksStep` | `run: gitleaks detect` |
| Python security scan | `template: uses: banditStep` | `run: bandit` |
| SBOM generation | `template: uses: sbomOrchestrationStep` | `run: syft` |
| AI security verify | `template: uses: aiVerifyStep` | Custom verification scripts |

## Remote Execution

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| SSH execution | `template: uses: ssh` | `run: ssh user@host` |

## CI/CD Integration

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Jenkins build | `template: uses: jenkinsBUILD` | `run: curl Jenkins API` |
| Bamboo build | `template: uses: bambooBuild` | `run: curl Bamboo API` |

## Other

| Task | Action / Template | Instead of |
|------|-------------------|------------|
| Wait/delay | `action: uses: wait` | `run: sleep` |
| OPA policy check | `action: uses: policy` | Custom policy scripts |

## When to Use Run Steps

A `run:` step is appropriate when:

- **Custom build commands** - `npm ci && npm run build`, `go build ./...`, `mvn clean package`
- **Custom test commands** - `npm test`, `pytest`, `go test ./...` (use `run-test:` for test intelligence)
- **Custom linting** - `eslint .`, `ruff check .`, `golangci-lint run`
- **One-off scripts** - Data migration, environment setup, custom validation
- **No native action or template exists** - Check this reference first before defaulting to `run:`

A `run:` step should NOT be used for:

- Docker build/push (use `buildAndPushToDocker` / `buildAndPushToECR` / `buildAndPushToGAR`)
- kubectl/helm commands (use K8s or Helm actions/templates)
- AWS/Azure/GCP deployment CLI commands (use cloud-native deploy actions/templates)
- Terraform/OpenTofu (use `terraformStep` / `openTofuStep`)
- Security scanning (use STO scanner templates)
- File uploads to cloud storage (use `uploadArtifactsToS3` / `uploadArtifactsToGCS`)
- API calls to Jira/ServiceNow (use native ticketing actions/templates)
- Waiting/sleeping (use `action: uses: wait`)
- HTTP health checks (use `action: uses: http` or `template: uses: httpStep`)
- Git clone (use `action: uses: git-clone` or `template: uses: gitCloneStep`)
