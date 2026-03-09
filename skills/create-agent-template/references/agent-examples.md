# Agent Template Examples

## Code Review Agent

**metadata.json:**
```json
{
  "name": "Code Review",
  "description": "AI-powered agent that reviews code changes and comments on pull requests",
  "version": "1.0.0"
}
```

**pipeline.yaml:**
```yaml
version: 1
pipeline:
  clone:
    depth: 1000
    ref:
      type: pull-request
      number: <+inputs.pullReq>
    repo: <+inputs.repo>

  stages:
    - name: review
      steps:
        - name: review_prompt_generation
          run:
            container:
              image: myregistry/ai-review:latest
            with:
              output_file: /harness/review/task.txt
              review_output_file: /harness/review/review.json
              working_directory: /harness

        - name: coding_agent
          run:
            container:
              image: myregistry/coding-agent:latest
            with:
              detailed_logging: "true"
              max_iterations: "50"
              task_file_path: /harness/review/task.txt
              working_directory: /harness
            env:
              ANTHROPIC_API_KEY: <+inputs.llmConnector.token>

        - name: post_comments
          run:
            container:
              image: myregistry/comment-plugin:latest
            with:
              comments_file: /harness/review/review.json
              repo: <+inputs.repo>
              pr_number: <+inputs.pullReq>
            env:
              TOKEN: <+inputs.harnessKey>

      platform:
        os: linux
        arch: arm64

  inputs:
    llmConnector:
      type: connector
    harnessKey:
      type: secret
      default: account.harness_api_key
    repo:
      type: string
      required: true
    pullReq:
      type: string
      required: true
```

## Security Scanner Agent

**metadata.json:**
```json
{
  "name": "Security Scanner",
  "description": "AI-powered agent that scans code for security vulnerabilities and suggests fixes",
  "version": "1.0.0"
}
```

**pipeline.yaml:**
```yaml
version: 1
pipeline:
  clone:
    depth: 1
    ref:
      name: <+inputs.branch>
      type: branch
    repo: <+inputs.repo>
    connector: "<+inputs.gitConnector != null ? inputs.gitConnector.id : ''>"

  stages:
    - name: security-scan
      steps:
        - name: vulnerability_scanner
          run:
            container:
              image: myregistry/security-scanner:latest
            with:
              scan_type: "full"
              severity_threshold: "medium"
              output_file: /harness/security/findings.json
              working_directory: /harness
            env:
              ANTHROPIC_API_KEY: <+inputs.llmConnector.token>

        - name: generate_report
          run:
            container:
              image: myregistry/report-generator:latest
            with:
              findings_file: /harness/security/findings.json
              report_file: /harness/security/SECURITY_REPORT.md
              format: markdown

        - name: post_findings
          run:
            container:
              image: myregistry/pr-comment:latest
            with:
              report_file: /harness/security/SECURITY_REPORT.md
              repo: <+inputs.repo>
              pr_number: <+inputs.pullReq>
            env:
              TOKEN: <+inputs.harnessKey>
          if: <+inputs.pullReq> != ""

      platform:
        os: linux
        arch: arm64

  inputs:
    llmConnector:
      type: connector
    harnessKey:
      type: secret
      default: harness_api_key
    gitConnector:
      type: connector
    repo:
      type: string
      required: true
    branch:
      type: string
      default: main
    pullReq:
      type: string
      default: ""
      description: Pull request number (optional, for PR comments)
```

## Documentation Generator Agent

**metadata.json:**
```json
{
  "name": "Documentation Generator",
  "description": "AI-powered agent that analyzes code and generates comprehensive documentation",
  "version": "1.0.0"
}
```

**pipeline.yaml:**
```yaml
version: 1
pipeline:
  clone:
    depth: 1
    ref:
      name: <+inputs.branch>
      type: branch
    repo: <+inputs.repo>
    connector: "<+inputs.gitConnector != null ? inputs.gitConnector.id : ''>"

  stages:
    - name: doc-generator
      steps:
        - name: analyze_and_generate
          run:
            container:
              image: myregistry/coding-agent:latest
            with:
              detailed_logging: "true"
              max_iterations: "50"
              working_directory: /harness
              prompt: |
                Analyze this codebase and generate:
                - README.md with project overview
                - API documentation
                - Usage examples
                - Architecture diagrams (mermaid)
            env:
              ANTHROPIC_API_KEY: <+inputs.llmConnector.token>

        - name: show_changes
          run:
            shell: bash
            script: |-
              git add -A
              git diff --cached

        - name: detect_scm_provider
          run:
            shell: bash
            script: |-
              SCM_PROVIDER="${DRONE_REPO_SCM}"
              if [ "$SCM_PROVIDER" = "Git" ]; then
                SCM_PROVIDER="harness"
              fi
              SCM_PROVIDER=$(echo "$SCM_PROVIDER" | tr '[:upper:]' '[:lower:]')

              if [ "$SCM_PROVIDER" = "harness" ]; then
                TOKEN="${HARNESS_API_KEY:-$SCM_TOKEN}"
                NETRC_USERNAME="${DRONE_NETRC_USERNAME}"
                NETRC_PASSWORD="${DRONE_NETRC_PASSWORD}"
              else
                NETRC_USERNAME=$(echo "$DRONE_REPO_LINK" | sed -E 's|https?://[^/]+/([^/]+)/.*|\1|')
                TOKEN="${SCM_TOKEN}"
                NETRC_PASSWORD="${SCM_TOKEN}"
              fi

              BASE_URL="${DRONE_SYSTEM_PROTO}://${DRONE_SYSTEM_HOST}"

              echo "SCM_PROVIDER=$SCM_PROVIDER" >> $DRONE_OUTPUT
              echo "TOKEN=$TOKEN" >> $HARNESS_OUTPUT_SECRET_FILE
              echo "NETRC_USERNAME=$NETRC_USERNAME" >> $DRONE_OUTPUT
              echo "NETRC_PASSWORD=$NETRC_PASSWORD" >> $HARNESS_OUTPUT_SECRET_FILE
              echo "BASE_URL=$BASE_URL" >> $DRONE_OUTPUT
            env:
              HARNESS_API_KEY: <+inputs.harnessKey>
              SCM_TOKEN: <+inputs.gitConnector.token>

        - name: create_pr
          run:
            container:
              image: myregistry/create-pr-plugin:latest
            env:
              PLUGIN_SCM_PROVIDER: <+pipeline.stages.doc-generator.steps.detect_scm_provider.output.outputVariables.SCM_PROVIDER>
              PLUGIN_TOKEN: <+pipeline.stages.doc-generator.steps.detect_scm_provider.output.outputVariables.TOKEN>
              PLUGIN_REPO: ${{inputs.repo}}
              PLUGIN_SOURCE_BRANCH: ${{inputs.branch}}
              PLUGIN_NETRC_MACHINE: <+env.DRONE_NETRC_MACHINE>
              PLUGIN_NETRC_USERNAME: <+pipeline.stages.doc-generator.steps.detect_scm_provider.output.outputVariables.NETRC_USERNAME>
              PLUGIN_NETRC_PASSWORD: <+pipeline.stages.doc-generator.steps.detect_scm_provider.output.outputVariables.NETRC_PASSWORD>
              PLUGIN_BRANCH_SUFFIX: ai-docs
              PLUGIN_COMMIT_MESSAGE: "docs: AI-generated documentation"
              PLUGIN_PUSH_CHANGES: "true"
              PLUGIN_CREATE_PR: "true"
              PLUGIN_PR_TITLE: "AI: Generated Documentation"
              PLUGIN_PR_DESCRIPTION: "Automated documentation generation. Please review before merging."
              PLUGIN_HARNESS_ACCOUNT_ID: <+env.HARNESS_ACCOUNT_ID>
              PLUGIN_HARNESS_ORG_ID: <+env.HARNESS_ORG_ID>
              PLUGIN_HARNESS_PROJECT_ID: <+env.HARNESS_PROJECT_ID>
              PLUGIN_HARNESS_BASE_URL: <+pipeline.stages.doc-generator.steps.detect_scm_provider.output.outputVariables.BASE_URL>

      platform:
        os: linux
        arch: arm64

  inputs:
    llmConnector:
      type: connector
      description: LLM connector for AI operations
    harnessKey:
      type: secret
      default: harness_api_key
    gitConnector:
      type: connector
      description: Git connector for repository access
    repo:
      type: string
      required: true
    branch:
      type: string
      default: main
```

## Common Patterns

### SCM Provider Detection

Standard pattern for multi-SCM support (GitHub, GitLab, Bitbucket, Harness Code):

```yaml
- name: detect_scm_provider
  run:
    shell: bash
    script: |-
      SCM_PROVIDER="${DRONE_REPO_SCM}"
      if [ "$SCM_PROVIDER" = "Git" ]; then
        SCM_PROVIDER="harness"
      fi
      SCM_PROVIDER=$(echo "$SCM_PROVIDER" | tr '[:upper:]' '[:lower:]')

      if [ "$SCM_PROVIDER" = "harness" ]; then
        TOKEN="${HARNESS_API_KEY:-$SCM_TOKEN}"
        NETRC_USERNAME="${DRONE_NETRC_USERNAME}"
        NETRC_PASSWORD="${DRONE_NETRC_PASSWORD}"
      else
        NETRC_USERNAME=$(echo "$DRONE_REPO_LINK" | sed -E 's|https?://[^/]+/([^/]+)/.*|\1|')
        TOKEN="${SCM_TOKEN}"
        NETRC_PASSWORD="${SCM_TOKEN}"
      fi

      BASE_URL="${DRONE_SYSTEM_PROTO}://${DRONE_SYSTEM_HOST}"

      echo "SCM_PROVIDER=$SCM_PROVIDER" >> $DRONE_OUTPUT
      echo "TOKEN=$TOKEN" >> $HARNESS_OUTPUT_SECRET_FILE
      echo "NETRC_USERNAME=$NETRC_USERNAME" >> $DRONE_OUTPUT
      echo "NETRC_PASSWORD=$NETRC_PASSWORD" >> $HARNESS_OUTPUT_SECRET_FILE
      echo "BASE_URL=$BASE_URL" >> $DRONE_OUTPUT
    env:
      HARNESS_API_KEY: <+inputs.harnessKey>
      SCM_TOKEN: <+inputs.gitConnector.token>
```

### Coding Agent Step

Standard AI coding agent pattern:

```yaml
- name: coding_agent
  run:
    container:
      image: myregistry/coding-agent:latest
    with:
      detailed_logging: "true"
      max_iterations: "50"
      task_file_path: /harness/task.txt
      working_directory: /harness
    env:
      ANTHROPIC_API_KEY: <+inputs.llmConnector.token>
```

### PR Creation Plugin

Standard pattern for creating pull requests with changes:

```yaml
- name: create_pr
  run:
    container:
      image: myregistry/create-pr-plugin:latest
    env:
      PLUGIN_SCM_PROVIDER: <+pipeline.stages.STAGE.steps.detect_scm_provider.output.outputVariables.SCM_PROVIDER>
      PLUGIN_TOKEN: <+pipeline.stages.STAGE.steps.detect_scm_provider.output.outputVariables.TOKEN>
      PLUGIN_REPO: ${{inputs.repo}}
      PLUGIN_SOURCE_BRANCH: ${{inputs.branch}}
      PLUGIN_BRANCH_SUFFIX: ai-changes
      PLUGIN_COMMIT_MESSAGE: "AI: Changes by Harness Agent"
      PLUGIN_PUSH_CHANGES: "true"
      PLUGIN_CREATE_PR: "true"
      PLUGIN_PR_TITLE: "AI: Automated Changes"
```
