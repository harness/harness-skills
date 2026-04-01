# Agent Pipeline Examples

This reference provides complete examples of agent YAML specifications and common patterns for building agents.

## Table of Contents

1. [Complete Agent Examples](#complete-agent-examples)
   - [Multi-Stage Agent: Code Coverage + Review](#multi-stage-agent-code-coverage--review)
2. [Common Patterns](#common-patterns)
   - [PR Creation Plugin](#pr-creation-plugin)
   - [SCM Provider Detection](#scm-provider-detection)

---

## Complete Agent Examples

### Multi-Stage Agent: Code Coverage + Review

This example demonstrates a two-stage agent that generates code coverage tests and then reviews the resulting PR.

### Agent Metadata (API Body)

```json
{
  "uid": "coverage_and_review_agent",
  "name": "Coverage and Review Agent",
  "description": "Two-stage agent that generates tests and reviews the resulting PR",
  "spec": "<see YAML below>"
}
```

### Agent Spec YAML

```yaml
version: 1
agent:
  clone:
    depth: 1000
    ref:
      type: branch
      name: main
    repo: username/test-repo
    connector: connector_github_test
  stages:
    - name: Coverage Stage
      id: coverage
      platform:
        os: linux
        arch: arm64
      steps:
        - id: run_code_coverage_agent
          name: Run Code Coverage Agent
          agent:
            container:
              image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/claude-code-plugin:main
            env:
              ANTHROPIC_MODEL: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw
              AWS_BEARER_TOKEN_BEDROCK: <+secrets.getValue("aws_bedrock_claude_code_ha")>
              AWS_REGION: us-east-1
              CLAUDE_CODE_USE_BEDROCK: "1"
            task: |
              You are a code coverage agent. The repository has already been cloned into the current working directory. It is a Go project. If go is not installed then install the latest version of go.
              1. Measure the current test coverage. Parse the output to determine overall and per-file coverage percentages.
              2. Identify all Go packages and source files below 80% coverage (or with no tests).
              3. Generate comprehensive unit tests to bring overall coverage to ≥80%:
                - Write idiomatic Go test functions in *_test.go files in the same package.
                - Cover all exported functions, edge cases, error paths, and boundary conditions.
                - Use table-driven tests where appropriate.
                - Do not delete or modify existing tests.
              4. Re-run coverage to confirm ≥80%. If not, continue adding tests.
              5. Generate COVERAGE.md (under 10000 chars) with: overall before/after, per-file summary table, key improvements.
              6. Use GitHub MCP tools to:
                a. Create branch "code-coverage-agent-<unique-suffix>" from current branch.
                b. Commit all new/modified test files and COVERAGE.md.
                c. Open a PR titled "Code Coverage: Automated coverage increase by Harness AI".
                d. Post COVERAGE.md contents as a PR comment under "## Code Coverage Report".
              7. Write INFO.md with PR url, repo, branch, and PR number.
              
              ## RULES
              - Use idiomatic Go code with table-driven tests
              - Do not modify or delete existing tests
              - Keep COVERAGE.md under 10000 characters
            max_turns: 150
            mcp_servers:
              harness:
                url: https://harmfully-unregulative-theressa.ngrok-free.dev/mcp
              github:
                url: https://api.githubcopilot.com/mcp/
                headers:
                  Authorization: Bearer <+secrets.getValue("github_pat_ha")>
            with:
              allowed_tools: mcp__harness__*,mcp__github__*,Read,Edit,Bash,Glob,Grep,Write
              log_file: .agent/output/mcp-coverage-log.jsonl

    - name: Review Stage
      id: review
      platform:
        os: linux
        arch: arm64
      steps:
        - id: run_code_review_agent
          name: Run Code Review Agent
          agent:
            container:
              image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/claude-code-plugin:main
            env:
              ANTHROPIC_MODEL: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw
              AWS_BEARER_TOKEN_BEDROCK: <+secrets.getValue("aws_bedrock_claude_code_ha")>
              AWS_REGION: us-east-1
              CLAUDE_CODE_USE_BEDROCK: "1"
            task: |
              Read PR url and info from INFO.md in the current directory.
              You are a code review agent. Review the pull request by:
              1. Analyzing all changed files for correctness, code quality, security issues, performance, and best practices.
              2. Posting inline review comments via GitHub MCP tools for any issues or suggestions.
              3. Posting a final summary comment with: key issues found, suggestions made, and overall verdict (Approve / Request Changes).
              
              ## RULES
              - Focus on security vulnerabilities first
              - Check test coverage for new code
              - Provide constructive feedback only
            max_turns: 150
            mcp_servers:
              harness:
                url: https://harmfully-unregulative-theressa.ngrok-free.dev/mcp
              github:
                url: https://api.githubcopilot.com/mcp/
                headers:
                  Authorization: Bearer <+secrets.getValue("github_pat_ha")>
            with:
              allowed_tools: mcp__harness__*,mcp__github__*,Read,Edit,Bash,Glob,Grep,Write
              log_file: .agent/output/mcp-review-log.jsonl
```

---

## Common Patterns

These are reusable patterns for common agent tasks that combine traditional pipeline steps with agent steps.

### SCM Provider Detection

Use this pattern to detect the SCM provider (GitHub, GitLab, Bitbucket) and extract the appropriate token:

```yaml
- name: detect_scm_provider
  run:
    shell: bash
    script: |-
      # Detect SCM provider from DRONE_REPO_SCM environment variable
      if [[ "$DRONE_REPO_SCM" == "github" ]]; then
        echo "SCM_PROVIDER=github" >> $DRONE_OUTPUT
        echo "TOKEN=<+inputs.githubConnector.token>" >> $DRONE_OUTPUT
      elif [[ "$DRONE_REPO_SCM" == "gitlab" ]]; then
        echo "SCM_PROVIDER=gitlab" >> $DRONE_OUTPUT
        echo "TOKEN=<+inputs.gitlabConnector.token>" >> $DRONE_OUTPUT
      elif [[ "$DRONE_REPO_SCM" == "bitbucket" ]]; then
        echo "SCM_PROVIDER=bitbucket" >> $DRONE_OUTPUT
        echo "TOKEN=<+inputs.bitbucketConnector.token>" >> $DRONE_OUTPUT
      else
        echo "Unsupported SCM provider: $DRONE_REPO_SCM"
        exit 1
      fi
```

**Usage:** Reference outputs with `<+pipeline.stages.STAGE_ID.steps.detect_scm_provider.output.outputVariables.SCM_PROVIDER>` and `<+pipeline.stages.STAGE_ID.steps.detect_scm_provider.output.outputVariables.TOKEN>`

### PR Creation Plugin

Standard pattern for creating pull requests with changes after an agent makes modifications:

```yaml
- name: create_pr
  run:
    container:
      image: myregistry/create-pr-plugin:latest
    env:
      PLUGIN_SCM_PROVIDER: <+pipeline.stages.STAGE_ID.steps.detect_scm_provider.output.outputVariables.SCM_PROVIDER>
      PLUGIN_TOKEN: <+pipeline.stages.STAGE_ID.steps.detect_scm_provider.output.outputVariables.TOKEN>
      PLUGIN_REPO: ${{inputs.repo}}
      PLUGIN_SOURCE_BRANCH: ${{inputs.branch}}
      PLUGIN_BRANCH_SUFFIX: ai-changes
      PLUGIN_COMMIT_MESSAGE: "AI: Changes by Harness Agent"
      PLUGIN_PUSH_CHANGES: "true"
      PLUGIN_CREATE_PR: "true"
      PLUGIN_PR_TITLE: "AI: Automated Changes"
```

**Prerequisites:** 
- Requires SCM provider detection step (see above)
- Use after agent step that makes code changes
- Replace `STAGE_ID` with your actual stage identifier
