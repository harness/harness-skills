---
name: create-trigger
description: Generate Harness Trigger YAML for automated pipeline execution and create via MCP. Use when user says "create trigger", "webhook trigger", "cron trigger", "scheduled build", "artifact trigger", or wants pipelines to run automatically.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Trigger

Generate Harness Trigger YAML and push to Harness via MCP.

## Instructions

1. **Identify trigger type** - Webhook (Git events), Scheduled (cron), Artifact (registry updates), or Manifest (Helm chart updates)
2. **Configure conditions** - Branch filters, payload conditions, cron expression, or artifact path
3. **Generate YAML** using the templates below, referencing the target pipeline
4. **Create via MCP** using `harness_create` with resource_type `trigger`
5. **Verify webhook registration** - For webhook triggers, confirm the webhook is registered in the Git provider

## Trigger Types

- **Webhook** - GitHub, GitLab, Bitbucket, Azure Repos, Custom
- **Scheduled** - Cron-based scheduling
- **Artifact** - Docker Hub, ECR, GCR, ACR, Nexus
- **Manifest** - Helm chart updates

## Webhook Trigger (GitHub)

```yaml
trigger:
  name: PR Trigger
  identifier: pr_trigger
  orgIdentifier: default
  projectIdentifier: my_project
  pipelineIdentifier: ci_pipeline
  source:
    type: Webhook
    spec:
      type: Github
      spec:
        type: PullRequest
        spec:
          connectorRef: github_connector
          autoAbortPreviousExecutions: true
          payloadConditions:
            - key: targetBranch
              operator: Equals
              value: main
          headerConditions: []
          jexlCondition: ""
          actions:
            - Open
            - Reopen
            - Synchronize
  inputYaml: |
    pipeline:
      identifier: ci_pipeline
      properties:
        ci:
          codebase:
            build:
              type: PR
              spec:
                number: <+trigger.prNumber>
```

### GitHub Event Types
- `Push` - Code pushed to branch
- `PullRequest` - PR events (Open, Close, Reopen, Synchronize, Edit)
- `IssueComment` - PR comments (Create, Edit, Delete)
- `Release` - Release events (Create, Publish, Edit)

## Webhook Trigger (GitLab)

```yaml
trigger:
  name: GitLab Push
  identifier: gitlab_push
  pipelineIdentifier: ci_pipeline
  source:
    type: Webhook
    spec:
      type: Gitlab
      spec:
        type: Push
        spec:
          connectorRef: gitlab_connector
          payloadConditions:
            - key: ref
              operator: Contains
              value: main
```

## Scheduled (Cron) Trigger

```yaml
trigger:
  name: Nightly Build
  identifier: nightly_build
  orgIdentifier: default
  projectIdentifier: my_project
  pipelineIdentifier: ci_pipeline
  source:
    type: Scheduled
    spec:
      type: Cron
      spec:
        expression: "0 2 * * *"    # 2 AM daily
  inputYaml: |
    pipeline:
      identifier: ci_pipeline
      properties:
        ci:
          codebase:
            build:
              type: branch
              spec:
                branch: main
```

Cron format: `<minute> <hour> <day-of-month> <month> <day-of-week>`

## Artifact Trigger (Docker Registry)

```yaml
trigger:
  name: New Image Trigger
  identifier: new_image
  pipelineIdentifier: deploy_pipeline
  source:
    type: Artifact
    spec:
      type: DockerRegistry
      spec:
        connectorRef: dockerhub
        imagePath: myorg/myimage
        tag: <+trigger.artifact.build>
  inputYaml: |
    pipeline:
      identifier: deploy_pipeline
      stages:
        - stage:
            identifier: deploy
            spec:
              service:
                serviceRef: my_service
```

### Artifact Source Types
- `DockerRegistry` - Docker Hub
- `Ecr` - AWS ECR
- `Gcr` - Google Container Registry
- `Acr` - Azure Container Registry
- `Nexus3Registry` - Nexus
- `AmazonS3` - S3 artifacts

## Creating via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "trigger"
  org_id: "<organization>"
  project_id: "<project>"
  body: <trigger YAML>
```

To list existing triggers:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "trigger"
  org_id: "<organization>"
  project_id: "<project>"
```

## Payload Conditions

Filter triggers by webhook payload:

```yaml
payloadConditions:
  - key: targetBranch
    operator: Equals        # Equals, NotEquals, In, NotIn, StartsWith, EndsWith, Contains, Regex
    value: main
  - key: sourceBranch
    operator: StartsWith
    value: feature/
```

Common keys: `sourceBranch`, `targetBranch`, `ref`, `action`, `tag`

## Examples

- "Create a GitHub PR trigger for CI" - Webhook trigger with PullRequest type
- "Set up nightly builds at 2 AM" - Scheduled trigger with cron
- "Trigger deploy when new Docker image is pushed" - Artifact trigger with DockerRegistry
- "Create a release trigger for tags" - Webhook with Push type, tag filter

## Performance Notes

- Verify payload conditions match actual webhook payloads from the Git provider.
- For cron triggers, double-check the expression — cron uses UTC timezone.
- Confirm the target pipeline identifier and inputYaml match the pipeline's expected inputs.

## Troubleshooting

### Trigger Not Firing
- Verify webhook is registered in Git provider
- Check payload conditions match actual payload
- Ensure connector has correct permissions
- Test with `harness_get` on the trigger to verify config

### Duplicate Executions
- Enable `autoAbortPreviousExecutions` for PR triggers
- Check for overlapping trigger conditions

### Cron Not Running
- Verify cron expression syntax (5 fields, UTC timezone)
- Check pipeline identifier is correct
- Ensure trigger is enabled
