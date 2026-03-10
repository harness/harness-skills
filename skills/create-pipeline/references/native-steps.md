# Harness Native Steps Reference

Always prefer Harness native steps over generic `Run` or `ShellScript` steps. Native steps provide built-in error handling, retry logic, rollback support, telemetry, and Harness UI integration that shell commands cannot match.

## Step Selection Priority

1. **Use a native step** if one exists for the task (this file)
2. **Use a Plugin step** if a Harness plugin covers the use case
3. **Use a Run step** only for custom logic with no native equivalent

## CI Build & Push Steps

Use these instead of running `docker build` / `docker push` in a Run step:

| Task | Native Step | Instead of |
|------|------------|------------|
| Build + push to Docker Hub | `BuildAndPushDockerRegistry` | `Run: docker build && docker push` |
| Build + push to AWS ECR | `BuildAndPushECR` | `Run: docker build && aws ecr ...` |
| Build + push to Google GCR | `BuildAndPushGCR` | `Run: docker build && gcloud ...` |
| Build + push to Google Artifact Registry | `BuildAndPushGAR` | `Run: docker build && gcloud artifacts ...` |
| Build + push to Azure ACR | `BuildAndPushACR` | `Run: docker build && az acr ...` |

### BuildAndPushDockerRegistry
```yaml
- step:
    identifier: docker_push
    name: Build and Push
    type: BuildAndPushDockerRegistry
    spec:
      connectorRef: dockerhub
      repo: myorg/myimage
      tags: [<+pipeline.sequenceId>, latest]
      dockerfile: Dockerfile
      context: .
      optimize: true
```

### BuildAndPushECR
```yaml
- step:
    identifier: ecr_push
    name: Build and Push ECR
    type: BuildAndPushECR
    spec:
      connectorRef: aws_connector
      region: us-east-1
      account: "123456789012"
      imageName: my-image
      tags: [<+pipeline.sequenceId>, latest]
```

## Artifact Upload Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Upload to S3 | `S3Upload` | `Run: aws s3 cp ...` |
| Upload to GCS | `GCSUpload` | `Run: gsutil cp ...` |
| Upload to Artifactory | `ArtifactoryUpload` | `Run: curl -X PUT ...` |
| Download from S3 | `DownloadAwsS3` | `Run: aws s3 cp ...` |

### S3Upload
```yaml
- step:
    identifier: upload_artifacts
    name: Upload to S3
    type: S3Upload
    spec:
      connectorRef: aws_connector
      region: us-east-1
      bucket: my-artifacts
      sourcePath: dist/
      target: builds/<+pipeline.sequenceId>/
```

## Cache Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Save cache to GCS | `SaveCacheGCS` | `Run: gsutil cp ...` |
| Restore cache from GCS | `RestoreCacheGCS` | `Run: gsutil cp ...` |
| Save cache to S3 | `SaveCacheS3` | `Run: aws s3 cp ...` |
| Restore cache from S3 | `RestoreCacheS3` | `Run: aws s3 cp ...` |
| Save cache (generic) | `SaveCache` | `Run: tar + upload` |
| Restore cache (generic) | `RestoreCache` | `Run: download + tar` |

### SaveCacheS3
```yaml
- step:
    identifier: save_cache
    name: Save Cache
    type: SaveCacheS3
    spec:
      connectorRef: aws_connector
      region: us-east-1
      bucket: ci-cache
      key: node-{{ checksum "package-lock.json" }}
      sourcePaths: [node_modules/]
```

## Git Operations

| Task | Native Step | Instead of |
|------|------------|------------|
| Clone a repo | `GitClone` | `Run: git clone ...` |

### GitClone
```yaml
- step:
    identifier: clone_manifests
    name: Clone Manifests
    type: GitClone
    spec:
      connectorRef: github
      repoName: k8s-manifests
      build:
        type: branch
        spec:
          branch: main
      cloneDirectory: /harness/manifests
```

## Kubernetes Deployment Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Rolling deploy | `K8sRollingDeploy` | `Run: kubectl apply ...` |
| Rolling rollback | `K8sRollingRollback` | `Run: kubectl rollout undo ...` |
| Blue-green deploy | `K8sBlueGreenDeploy` | Complex kubectl scripts |
| Blue-green swap | `K8sBGSwapServices` | `Run: kubectl patch ...` |
| Canary deploy | `K8sCanaryDeploy` | `Run: kubectl apply ... (partial)` |
| Canary delete | `K8sCanaryDelete` | `Run: kubectl delete ...` |
| Apply manifests | `K8sApply` | `Run: kubectl apply ...` |
| Scale workload | `K8sScale` | `Run: kubectl scale ...` |
| Delete resources | `K8sDelete` | `Run: kubectl delete ...` |
| Dry run | `K8sDryRun` | `Run: kubectl apply --dry-run ...` |
| Traffic routing | `K8sTrafficRouting` | `Run: kubectl edit ingress ...` |

## Helm Deployment Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Helm install/upgrade | `HelmDeploy` | `Run: helm upgrade --install ...` |
| Helm rollback | `HelmRollback` | `Run: helm rollback ...` |
| Helm uninstall | `HelmDelete` | `Run: helm uninstall ...` |

## ECS Deployment Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| ECS rolling deploy | `EcsRollingDeploy` | `Run: aws ecs update-service ...` |
| ECS rolling rollback | `EcsRollingRollback` | Complex ECS rollback scripts |
| ECS blue-green create | `EcsBlueGreenCreateService` | AWS CLI scripts |
| ECS blue-green swap | `EcsBlueGreenSwapTargetGroups` | AWS CLI scripts |
| ECS canary deploy | `EcsCanaryDeploy` | AWS CLI scripts |
| ECS run task | `EcsRunTask` | `Run: aws ecs run-task ...` |

## Serverless & Lambda Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Lambda deploy | `AwsLambdaDeploy` | `Run: aws lambda update-function ...` |
| Lambda rollback | `AwsLambdaRollback` | `Run: aws lambda ...` |
| Serverless deploy | `ServerlessAwsLambdaDeployV2` | `Run: serverless deploy` |
| SAM deploy | `AwsSamDeploy` | `Run: sam deploy ...` |
| SAM build | `AwsSamBuild` | `Run: sam build ...` |
| CDK deploy | `AwsCdkDeploy` | `Run: cdk deploy ...` |
| CDK synth | `AwsCdkSynth` | `Run: cdk synth ...` |
| CDK diff | `AwsCdkDiff` | `Run: cdk diff ...` |
| CloudFormation create | `CreateStack` | `Run: aws cloudformation ...` |
| CloudFormation delete | `DeleteStack` | `Run: aws cloudformation delete ...` |

## Azure Deployment Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Azure Web App slot deploy | `AzureSlotDeployment` | `Run: az webapp deployment ...` |
| Azure traffic shift | `AzureTrafficShift` | `Run: az webapp traffic-routing ...` |
| Azure swap slot | `AzureSwapSlot` | `Run: az webapp deployment slot swap ...` |
| Azure Function deploy | `AzureFunctionDeploy` | `Run: func azure functionapp publish ...` |
| ARM template | `AzureCreateARMResource` | `Run: az deployment group create ...` |

## Google Cloud Deployment Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Cloud Function deploy | `DeployCloudFunction` | `Run: gcloud functions deploy ...` |
| Cloud Run deploy | `GoogleCloudRunDeploy` | `Run: gcloud run deploy ...` |
| Cloud Run traffic shift | `GoogleCloudRunTrafficShift` | `Run: gcloud run services update-traffic ...` |
| Cloud Function rollback | `CloudFunctionRollback` | Complex gcloud scripts |

## Infrastructure as Code Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Terraform plan | `TerraformPlan` | `Run: terraform plan ...` |
| Terraform apply | `TerraformApply` | `Run: terraform apply ...` |
| Terraform destroy | `TerraformDestroy` | `Run: terraform destroy ...` |
| Terraform rollback | `TerraformRollback` | Manual state manipulation |
| Terragrunt plan | `TerragruntPlan` | `Run: terragrunt plan ...` |
| Terragrunt apply | `TerragruntApply` | `Run: terragrunt apply ...` |

## Approval Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Manual approval | `HarnessApproval` | Custom webhook polling |
| Jira approval | `JiraApproval` | `Run: curl Jira API ...` |
| ServiceNow approval | `ServiceNowApproval` | `Run: curl ServiceNow API ...` |
| Custom approval | `CustomApproval` | `ShellScript` with polling |

### HarnessApproval (required fields)

The API requires `approvers.disallowPipelineExecutor`. Always include it (set to `true` so the pipeline executor cannot approve their own run).

```yaml
- step:
    identifier: approve
    name: Approve
    type: HarnessApproval
    spec:
      approvalMessage: "Please review and approve"
      approvers:
        userGroups: [prod_approvers]
        minimumCount: 1
        disallowPipelineExecutor: true
      includePipelineExecutionHistory: true
    timeout: 1d
```

## Ticketing & Notification Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Create Jira issue | `JiraCreate` | `Run: curl Jira API ...` |
| Update Jira issue | `JiraUpdate` | `Run: curl Jira API ...` |
| Create ServiceNow ticket | `ServiceNowCreate` | `Run: curl ServiceNow ...` |
| Update ServiceNow ticket | `ServiceNowUpdate` | `Run: curl ServiceNow ...` |
| HTTP request | `Http` | `Run: curl ...` |
| Send email | `Email` | `Run: sendmail ...` |

## Security Scanning Steps

Use these instead of running scanners via `Run` steps — native steps integrate with Harness STO dashboards:

| Scanner | Native Step | Instead of |
|---------|------------|------------|
| Aqua Trivy | `AquaTrivy` | `Run: trivy image ...` |
| Snyk | `Snyk` | `Run: snyk test ...` |
| SonarQube | `Sonarqube` | `Run: sonar-scanner ...` |
| Checkmarx | `Checkmarx` | `Run: cx scan ...` |
| Black Duck | `BlackDuck` | `Run: synopsys-detect ...` |
| Veracode | `Veracode` | `Run: veracode ...` |
| Prisma Cloud | `PrismaCloud` | `Run: twistcli ...` |
| OWASP ZAP | `Zap` | `Run: zap-cli ...` |
| Grype | `Grype` | `Run: grype ...` |
| Bandit (Python) | `Bandit` | `Run: bandit ...` |
| Brakeman (Ruby) | `Brakeman` | `Run: brakeman ...` |
| Semgrep | `Semgrep` | `Run: semgrep ...` |
| Gitleaks | `Gitleaks` | `Run: gitleaks detect ...` |
| CodeQL | `CodeQL` | `Run: codeql ...` |
| Checkov (IaC) | `Checkov` | `Run: checkov ...` |
| Prowler (AWS) | `Prowler` | `Run: prowler ...` |
| Wiz | `Wiz` | `Run: wiz-cli ...` |
| FOSSA | `Fossa` | `Run: fossa analyze ...` |

## Supply Chain Security Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Generate/attach SBOM | `SscaOrchestration` | `Run: syft ...` |
| Enforce SBOM policies | `SscaEnforcement` | Custom policy scripts |
| SLSA provenance verification | `SlsaVerification` | Manual verification |
| Deployment impact analysis | `AnalyzeDeploymentImpact` | Custom analysis scripts |

## GitOps Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Sync ArgoCD app | `GitOpsSync` | `Run: argocd app sync ...` |
| Update release repo | `GitOpsUpdateReleaseRepo` | `Run: git commit && push ...` |
| Fetch linked apps | `GitOpsFetchLinkedApps` | `Run: argocd app list ...` |

## Chaos Engineering Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Run chaos experiment | `Chaos` | External chaos tool scripts |

## Verification Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Continuous verification | `Verify` | Manual monitoring checks |

## Database Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Apply DB schema | `DBSchemaApply` | `Run: flyway migrate ...` |
| Rollback DB schema | `DBSchemaRollback` | `Run: flyway undo ...` |

## Other Useful Steps

| Task | Native Step | Instead of |
|------|------------|------------|
| Wait/delay | `Wait` | `Run: sleep ...` |
| Barrier (sync parallel) | `Barrier` | Complex coordination scripts |
| Background service | `Background` | Docker Compose in Run step |
| Jenkins build | `JenkinsBuild` | `Run: curl Jenkins API ...` |
| Bamboo build | `BambooBuild` | `Run: curl Bamboo API ...` |
| Bitrise build | `Bitrise` | `Run: curl Bitrise API ...` |
| Revert PR | `RevertPR` | `Run: git revert && gh pr create ...` |

## When to Use Run Steps

A `Run` step is appropriate when:

- **Custom build commands** - `npm ci && npm run build`, `go build ./...`, `mvn clean package`
- **Custom test commands** - `npm test`, `pytest`, `go test ./...` — **must include a `reports` block** (e.g. `type: JUnit`, `spec.paths`) so Harness captures test results; see codebase-analysis.md for framework → report path.
- **Custom linting** - `eslint .`, `ruff check .`, `golangci-lint run`
- **One-off scripts** - Data migration, environment setup, custom validation
- **No native step exists** - Check this reference first before defaulting to Run

A `Run` step should NOT be used for:
- Docker build/push (use `BuildAndPush*` steps)
- kubectl/helm commands (use `K8s*` / `Helm*` steps)
- AWS/Azure/GCP CLI deployment commands (use cloud-native deploy steps)
- Security scanning (use STO scanner steps)
- File uploads to cloud storage (use `S3Upload` / `GCSUpload`)
- API calls to Jira/ServiceNow (use native ticketing steps)
- Waiting/sleeping (use `Wait` step)
- HTTP health checks (use `Http` step)
