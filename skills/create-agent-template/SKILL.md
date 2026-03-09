---
name: create-agent-template
description: >-
  Generate Harness Agent Template files for AI-powered automation agents. Produces metadata.json,
  pipeline.yaml (v1 syntax), and wiki.MD files. Agents automate tasks like code review, security
  scanning, test generation, and documentation. This is a YAML generation skill. Use when asked to
  create an agent template, build an AI agent, create an automation agent, generate agent pipeline
  files, or set up a Harness agent. Trigger phrases: create agent template, agent template, AI agent,
  automation agent, build agent, code review agent, security scanner agent, Harness agent.
metadata:
  author: Harness
  mcp-server: harness-mcp-v2
  version: 1.0.0
license: Apache-2.0
compatibility: No MCP server required. Generates YAML files locally.
---

# Create Agent Template Skill

Generate Harness Agent Template files for AI-powered automation agents.

## Instructions

1. **Identify the agent's purpose** - What task should the agent automate (code review, security scanning, test generation, documentation)?
2. **Define inputs and configuration** - What parameters does the agent need (repo, branch, connector, secrets)?
3. **Generate three files** - metadata.json (template metadata), pipeline.yaml (v1 syntax), and wiki.MD (user documentation)
4. **Validate consistency** - Ensure input references in pipeline.yaml match definitions in metadata.json

## Overview

Agent templates are modular pipeline definitions that encapsulate AI-powered automation. Each template produces three files:

| File | Required | Purpose |
|------|----------|---------|
| `metadata.json` | Yes | Template name, description, version |
| `pipeline.yaml` | Yes | Pipeline definition (v1 syntax) |
| `wiki.MD` | Recommended | User-facing documentation |

## Directory Structure

```
templates/<agent-name>/
  metadata.json
  pipeline.yaml
  wiki.MD
```

## metadata.json

```json
{
  "name": "Agent Name",
  "description": "Brief description of what this agent does (1-2 sentences)",
  "version": "1.0.0"
}
```

**Rules:**
- `name`: Sentence Case (`Code Review`, not `code-review`)
- `description`: Under 200 characters, clear value proposition
- `version`: Semantic versioning `MAJOR.MINOR.PATCH`

## pipeline.yaml

### Core Structure

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
    - name: <stage-name>
      steps:
        - name: <step-name>
          run:
            container:
              image: <registry>/<image>:<tag>
            with:
              param: value
            env:
              SECRET_VAR: <+inputs.secretInput>
      platform:
        os: linux
        arch: arm64

  inputs:
    repo:
      type: string
      required: true
    branch:
      type: string
      default: main
    llmConnector:
      type: connector
    gitConnector:
      type: connector
```

### Clone Configurations

**Branch clone:**

```yaml
clone:
  depth: 1
  ref:
    name: <+inputs.branch>
    type: branch
  repo: <+inputs.repo>
  connector: "<+inputs.gitConnector != null ? inputs.gitConnector.id : ''>"
```

**Pull request clone:**

```yaml
clone:
  depth: 1000
  ref:
    type: pull-request
    number: <+inputs.pullReq>
  repo: <+inputs.repo>
```

### Input Types

| Type | Usage | Example |
|------|-------|---------|
| `string` | Text values | repo name, branch, file paths |
| `secret` | Sensitive values | API keys, tokens |
| `connector` | Harness connectors | Git connector, LLM connector |

```yaml
inputs:
  repo:
    type: string
    required: true
  branch:
    type: string
    default: main
    description: Branch to analyze
  apiKey:
    type: secret
    default: account.my_secret
  llmConnector:
    type: connector
    description: LLM provider connector
  gitConnector:
    type: connector
    description: Git repository connector
```

### Step Types

**Container plugin step:**

```yaml
- name: my-step
  run:
    container:
      image: registry/image:tag
    with:
      plugin_param: value
    env:
      API_KEY: <+inputs.apiKey>
```

**Shell script step:**

```yaml
- name: shell-step
  run:
    shell: bash
    script: |-
      echo "Running script"
      git add -A
      git diff --cached
    env:
      MY_VAR: value
```

### Expression Syntax

```yaml
# Input references
<+inputs.variableName>

# Connector token
<+inputs.connectorName.token>

# Step outputs
<+pipeline.stages.STAGE.steps.STEP.output.outputVariables.VAR>

# Environment variables
<+env.HARNESS_ACCOUNT_ID>
<+env.HARNESS_ORG_ID>
<+env.HARNESS_PROJECT_ID>

# Alternative syntax for inputs in env blocks
${{inputs.repo}}
```

## wiki.MD

```markdown
# Agent Name

**Version:** 1.0.0
**Name:** Agent Name

## Overview

What this agent does and why it is useful.

---

## Key Capabilities

- **Capability 1**: Description
- **Capability 2**: Description

---

## How It Works

1. **Step 1**: Description
2. **Step 2**: Description
3. **Step 3**: Description

## Required Inputs

| Input | Type | Description | Default |
|-------|------|-------------|---------|
| `repo` | string | Repository identifier | -- |
| `branch` | string | Branch to analyze | main |

## Usage Example

\`\`\`yaml
inputs:
  repo: "my-org/my-repo"
  branch: "main"
\`\`\`

## Troubleshooting

### Common Issue 1
Solution description.
```

## Complete Examples and Common Patterns

For complete agent examples (Code Review, Security Scanner, Documentation Generator) and reusable patterns (SCM detection, coding agent, PR creation), consult references/agent-examples.md.

## Examples

### Create a code review agent

```
/create-agent-template
Create an agent template for code review that analyzes pull requests,
provides feedback, and posts review comments
```

### Create a security scanner agent

```
/create-agent-template
Generate a security scanner agent that finds vulnerabilities and
creates a report
```

### Create a documentation generator

```
/create-agent-template
Create an agent that analyzes a codebase and generates documentation,
then opens a PR with the results
```

### Create a test generator

```
/create-agent-template
Build an agent template that generates unit tests to improve code coverage
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Invalid metadata | Missing name, description, or version | Include all three required fields |
| Invalid version | Not semver format | Use `MAJOR.MINOR.PATCH` (e.g., `1.0.0`) |
| Pipeline validation error | Invalid v1 YAML syntax | Verify pipeline structure follows v1 schema |
| Connector not found | Referenced connector does not exist | Create the connector before running the agent |
| Undefined input reference | `<+inputs.x>` used but `x` not defined in inputs | Add missing input definition |

## Performance Notes

- Validate all three generated files (metadata.json, pipeline.yaml, wiki.MD) are consistent with each other.
- Ensure the pipeline YAML uses correct v1 syntax with lowercase types and ${{ }} expressions.
- Test that all input references in the pipeline match the inputs defined in metadata.json.

## Troubleshooting

### Agent Not Executing

1. Verify all `required: true` inputs have values
2. Check connector inputs are valid and accessible
3. Confirm container images exist and are accessible from the build infrastructure

### SCM Provider Detection Failing

1. Verify `DRONE_REPO_SCM` environment variable is available
2. Check that connector tokens have correct permissions
3. Test with a known SCM provider before adding multi-provider logic

### PR Creation Failing

1. Confirm git changes exist (`git diff --cached` is non-empty)
2. Verify the token has write access to create branches and PRs
3. Check that `PLUGIN_REPO` format matches the SCM provider expectations

### Output Variables Not Available

1. Write outputs using `echo "KEY=value" >> $DRONE_OUTPUT`
2. Write secret outputs using `echo "KEY=value" >> $HARNESS_OUTPUT_SECRET_FILE`
3. Reference with full path: `<+pipeline.stages.STAGE.steps.STEP.output.outputVariables.KEY>`

## Best Practices

- Never hardcode secrets -- use `type: secret` inputs
- Use `type: connector` for authentication rather than raw tokens
- Include meaningful descriptions on all inputs
- Keep stages focused on single responsibilities
- Always include the SCM detection pattern for multi-provider support
- Store secret outputs with `$HARNESS_OUTPUT_SECRET_FILE`, not `$DRONE_OUTPUT`
- Set `depth: 1000` for PR clones to ensure full diff history
- Set `depth: 1` for branch clones to minimize clone time
