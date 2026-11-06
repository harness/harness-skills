# Triggers: PR trigger & baseline trigger

> **Both are required.** The PR trigger gates PRs on patch coverage. The baseline trigger runs on
> pushes/merges to the default branch to record and refresh baseline coverage in HCC.

## Why the baseline trigger is essential

- Without it, merges to the default branch never run the coverage step: zero default-branch
  executions, no baseline in HCC, empty/stale trend graphs, and no fresh base for delta
  comparisons on later PRs.
- With it, every merge runs tests, `hcli cov upload`, and updates the baseline snapshot.
- A freshly created baseline trigger produces **no execution until a PR is merged** — surface this
  in the final summary and ask the user to monitor the first post-merge run.

## Checking existing triggers

`harness_list(resource_type="trigger", pipeline_id=<id>, org_id=<org>, project_id=<project>)`.
Create only what's missing; show the YAML and include it in the batched approval first.

## 1. PR trigger (PullRequest events)

```yaml
trigger:
  name: PR Coverage Check
  identifier: pr_coverage_check
  orgIdentifier: <org>
  projectIdentifier: <project>
  pipelineIdentifier: <pipeline_id>
  source:
    type: Webhook
    spec:
      type: Github # or HarnessCode / Gitlab
      spec:
        type: PullRequest
        spec:
          connectorRef: <git_connector>
          autoAbortPreviousExecutions: true
          payloadConditions:
            - key: targetBranch
              operator: Equals
              value: main # default branch
          actions:
            - Open
            - Reopen
            - Synchronize
  inputYaml: |
    pipeline:
      identifier: <pipeline_id>
      properties:
        ci:
          codebase:
            build:
              type: PR
              spec:
                number: <+trigger.prNumber>
```

## 2. Baseline trigger (Push/merge to the default branch)

```yaml
trigger:
  name: Baseline Main Coverage Trigger
  identifier: baseline_main_coverage_trigger
  orgIdentifier: <org>
  projectIdentifier: <project>
  pipelineIdentifier: <pipeline_id>
  source:
    type: Webhook
    spec:
      type: Github # or HarnessCode / Gitlab
      spec:
        type: Push
        spec:
          connectorRef: <git_connector>
          autoAbortPreviousExecutions: false
          payloadConditions:
            - key: targetBranch # or branch
              operator: Equals
              value: main # default branch
  inputYaml: |
    pipeline:
      identifier: <pipeline_id>
      properties:
        ci:
          codebase:
            build:
              type: branch
              spec:
                branch: <+trigger.branch>
```

Create via `harness_create(resource_type="trigger", ...)` after approval.
