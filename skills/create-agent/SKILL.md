---
name: create-agent
description: >-
  Create and update Harness AI agent instances - standalone templates used as building blocks in pipelines. Agents contain a single agent step with connector-driven architecture requiring llmConnector (LLM access) and optional mcpConnectors (GitHub, Slack, Harness platform). Supports runtime inputs and task/rules-based instruction. Use when asked to create an agent, update agent spec, modify agent configuration, automate tasks, perform agentic workflows, build autonomous systems, or work with AI agents. Trigger phrases: create agent, update agent, modify agent spec, AI agent, autonomous agent, agentic pipeline, automation task, automate workflow, Harness agent, code coverage agent, review agent, agentic task.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Agent

Create and update Harness AI agent instances - standalone templates used as building blocks in pipelines for automated code, agentic workflows, and infrastructure tasks.

## Instructions

Follow this workflow to create or update an agent. **This is INTERACTIVE — show YAML for review and wait for confirmation before creating/updating the agent.**

### Phase 1: Check Existing Solutions First

**IMPORTANT: Before creating a new agent, check if an existing one can solve the use case.**

1. **List existing agents** — Call `harness_list` with `resource_type="agent"` (include `org_id` and `project_id` if scoped to a project)
   - Check if any system or custom agents already exist that can handle this task
   - Ask user if they want to use/modify an existing agent instead of creating new
2. **For updating existing agents** — Use `harness_get` with `resource_type="agent"` and `agent_id` to retrieve the current agent configuration
   - Review the current `spec`, `name`, `description`, and other fields
   - Identify what needs to be changed (spec, name, description, wiki, logo)
   - Use `harness_update` (not `harness_create`) to update the agent with only the fields that need modification

### Phase 2: Requirements Gathering

If creating a new agent or updating an existing one, collect the following before generating YAML:

#### 1. Agent Metadata
- **Name**: Display name for the agent (e.g. "Code Coverage Agent", "PR Reviewer")
- **Description**: Brief description of the agent's purpose (optional)
- **UID**: Unique identifier (auto-generated from name if not provided — e.g. "Code Coverage Agent" → "code_coverage_agent")

#### 2. Task Details

**This is an INTERACTIVE requirements gathering process. Ask clarifying questions and verify understanding with the user before proceeding.**

##### Step 1: Understand the Agent's Purpose

Ask and clarify the following with the user:

1. **Agent's exact goal**: What specific outcome should the agent achieve?
   - Examples: "Increase code coverage to 80%", "Review PRs for security vulnerabilities", "Generate unit tests for uncovered functions"
   - Be specific — avoid vague goals like "improve code quality"

2. **Inputs the agent needs**: What data or context does the agent require to start?
   - Repository information? (repo name, branch, PR number)
   - Execution context? (pipeline execution ID, previous step outputs)
   - Configuration? (coverage threshold, target files, exclusion patterns)
   - Secrets? (API keys, tokens for external services)

3. **Outputs the agent produces**: What artifacts, reports, or actions should result?
   - Files? (COVERAGE.md, test files, reports)
   - External actions? (create PR, post comments, send notifications)
   - Data? (metrics, logs, analysis results)

4. **What the agent works on**: What files, services, or systems does it interact with?
   - Specific file paths or patterns? (e.g., `pkg/**/*.go`, `src/services/`)
   - External services? (GitHub API, Slack, monitoring systems)
   - Databases or APIs? (read-only access, write operations)

5. **Task workflow**: Understand the user's workflow for the task — what should happen step-by-step (do 1, then 2, then 3, etc.)

6. **Constraints and preferences**: Any user preferences for completing the task — limitations, rules, or coding standards the agent should follow
   - Examples: "Use idiomatic Go code", "Do not modify existing tests", "Keep reports under 10000 characters"

7. **Definition of done**: How do you know the agent succeeded?
   - Specific criteria? ("Coverage increased by X%", "All files have tests")
   - Artifacts created? ("PR created with tests", "COVERAGE.md updated")
   - Exit conditions? ("No security vulnerabilities found", "All checks passed")

##### Step 2: Recommend Configuration

Based on the requirements gathered in Step 1, recommend specific configurations and verify with the user:

1. **Task instructions** (`task` field):
   - Break down the goal into detailed step-by-step instructions
   - Include specific commands, file paths, and expected outcomes
   - Reference inputs using `<+inputs.fieldName>` syntax
   - Example: "1. Run `go test -cover ./...` to measure coverage\n2. Identify functions below 80% coverage\n3. Generate tests for uncovered functions\n4. Create PR with new tests"

2. **Runtime inputs** (`inputs` section in spec):
   - Only add if user confirms runtime parameters are needed
   - Map each input to what the agent needs (repo, branch, executionId, thresholds, etc.)
   - Example: `repo` (string), `coverageThreshold` (string), `llmKey` (secret)

3. **User preferences** (RULES section in `task` field):
   - Convert constraints and coding standards into a dedicated RULES section at the end of the task
   - Format as a markdown section with bullet points
   - Be specific and actionable
   - Example: Add `## RULES\n- Use idiomatic Go code\n- Do not modify existing tests\n- Keep COVERAGE.md under 10000 characters` at the end of the task

4. **Connectors**:
   - LLM connector for model access (required for all agents) - User must create via Harness UI or MCP
   - MCP connectors for external services (GitHub, Slack, Harness platform, etc.) - only if needed
   - All authentication and secrets are managed within the connectors

**Present this recommended configuration to the user and iterate until confirmed.**

#### 3. Default Configuration & Inputs

**Agent Structure:** Agents use `agent.step.run` format with a single step.

**Default container image:**
```yaml
container:
  image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/harness-ai-agent:latest
```

**Required environment variables:**
```yaml
env:
  ANTHROPIC_MODEL: <+inputs.anthropicModel>           # Points to anthropicModel input field
  PLUGIN_HARNESS_CONNECTOR: <+inputs.llmConnector.id> # Points to llmConnector input's id property
```

**Default max_turns:**
```yaml
max_turns: 150  # Adjust 100-200 based on task complexity
```

**MCP configuration (only if external services needed):**
```yaml
mcp_format: harness
mcp_servers: <+connectorInputs.resolveList(<+inputs.mcpConnectors>)>  # Points to mcpConnectors input field
```

**Required inputs (always include):**
```yaml
agent:
  inputs:
    llmConnector:
      type: connector
      required: true
      default: your_llm_connector_id  # User must replace with actual connector ID
    
    anthropicModel:
      type: string
      required: true
      default: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw # User may replace with their preferred model
```

**Optional inputs (add as needed):**
```yaml
    # MCP connectors - only if agent needs external services
    mcpConnectors:
      type: array
      default:
        - your_github_mcp_connector  # User must replace
        - your_slack_mcp_connector   # User must replace
    
    # Custom parameters
    repo_name:
      type: string
      default: my-org/my-repo
```

**Supported input types:** `string`, `secret`, `boolean`, `connector`, `array`

**IMPORTANT:** Users must create connectors via Harness UI or `harness_create` with `resource_type="connector"` before running the agent.

### Phase 3: Generate Agent Spec

Assemble the complete agent YAML specification (`spec` field):

1. Start with `version: 1` and `agent:` structure
2. Create `agent.step.run` block with:
   - `container.image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/harness-ai-agent:latest`
   - `with` section:
     - `task:` with step-by-step instructions and `## RULES` section
     - `max_turns: 150` (adjust 100-200 based on complexity)
     - `mcp_format: harness` (only if MCPs needed)
     - `mcp_servers: <+connectorInputs.resolveList(<+inputs.mcpConnectors>)>` (only if MCPs needed)
   - `env` section:
     - `ANTHROPIC_MODEL: <+inputs.anthropicModel>`
     - `PLUGIN_HARNESS_CONNECTOR: <+inputs.llmConnector.id>`
3. Add `agent.inputs` section with:
   - `llmConnector` (required - use placeholder ID)
   - `anthropicModel` (required - use default ARN, but user may update)
   - `mcpConnectors` (optional - only if needed)
   - Custom inputs (as needed)

**Always notify users to create connectors and replace placeholder IDs before running the agent.**

### Phase 4: Present for Review

Present the complete agent configuration to the user:
- Agent metadata (name, description, uid)
- Full spec YAML
- Required connectors

**Wait for explicit confirmation before creating/updating the agent.**

### Phase 5: Create or Update Agent

Only after confirmation, use `harness_create` to create a new agent or `harness_update` to update an existing one:

#### Creating a New Agent

```
Call MCP tool: harness_create
Parameters:
  resource_type: "agent"
  org_id: "<organization>"
  project_id: "<project>"
  body: {
    uid: "<agent_identifier>",
    name: "<Agent Display Name>",
    description: "<Brief description of agent purpose>",
    spec: "<agent YAML spec as a string>",
    wiki: "<optional: markdown documentation>"
  }
```

**Key fields for creation:**
- `uid` (required): Unique identifier. Auto-generated from `name` if not provided (e.g. "Code Coverage Agent" → "code_coverage_agent")
- `name` (required): Display name for the agent
- `description` (optional): Brief description
- `spec` (required): The full agent YAML specification as a string (includes `version: 1`, `agent:`, `stages:`, etc.)
- `wiki` (optional): Markdown documentation for the agent

#### Updating an Existing Agent

```
Call MCP tool: harness_update
Parameters:
  resource_type: "agent"
  agent_id: "<agent_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: {
    name: "<Updated Display Name>",           # optional
    description: "<Updated description>",     # optional
    spec: "<updated agent YAML spec>",        # optional
    wiki: "<updated markdown docs>"           # optional
  }
```

**Key notes for updates:**
- All fields in the body are optional — only provide fields you want to update
- Only custom agents (role='custom') can be updated; system agents cannot be modified
- The `spec` field replaces the entire agent specification when provided
- Use `harness_get` first to retrieve the current agent configuration before updating

## Example: Code Review Agent

```yaml
version: 1
agent:
  step:
    run:
      container:
        image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/harness-ai-agent:latest
      with:
        task: |
          Review the pull request for repository <+inputs.repo_name> on branch <+inputs.branch>.
          
          1. Analyze code changes for security vulnerabilities
          2. Check for code quality issues
          3. Verify test coverage
          4. Post review comments using GitHub MCP tools
          
          ## RULES
          - Focus on critical security issues first
          - Be constructive in feedback
          - Suggest specific code improvements
        max_turns: 150
        mcp_format: harness
        mcp_servers: <+connectorInputs.resolveList(<+inputs.mcpConnectors>)>
      env:
        ANTHROPIC_MODEL: <+inputs.anthropicModel>
        PLUGIN_HARNESS_CONNECTOR: <+inputs.llmConnector.id>
  
  inputs:
    llmConnector:
      type: connector
      required: true
      default: your_llm_connector_id  # User must replace with actual connector ID
    
    anthropicModel:
      type: string
      required: true
      default: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw
    
    mcpConnectors:
      type: array
      default:
        - your_github_mcp_connector  # User must replace with actual connector ID
    
    repo_name:
      type: string
      default: my-org/my-repo
    
    branch:
      type: string
      default: main
```

## CRITICAL GUIDELINES

**These are essential rules you MUST follow when creating/updating agents:**

| Guideline                  | Rule                                                                                                                                     |
| ----------------------------| ------------------------------------------------------------------------------------------------------------------------------------------|
| **Check existing first**   | Always call `harness_list(resource_type="agent")` to see if an existing agent can solve the use case before creating new                 |
| **Updating agents**        | Use `harness_get` to retrieve current config, then `harness_update` (not `harness_create`) to modify. Only custom agents can be updated. |
| **Agent spec format**      | The `spec` field contains standalone agent YAML (version: 1, agent:, stages:, steps:, inputs:)                                           |
| **Connectors required**    | All agents require `llmConnector` (required) and optional `mcpConnectors` (array) in the inputs section — users must create these first  |
| **Connector placeholders** | Always use placeholders like `your_llm_connector_id` and notify users to replace with actual connector IDs                               |
| **Prefer inputs**          | Use `inputs` for configuration instead of environment variables — reference with `${{ inputs.variableName }}`                            |
| **No clone/platform**      | Do NOT add `clone`, `platform`, `os`, `arch`, or `allowed_tools` sections — agents are standalone with simplified structure              |
| **Quality first**          | Agent quality is paramount — verify YAML structure, validate all references, ensure complete task instructions before creating           |


## Examples

- "Create an agent that reviews PRs for security issues" - Gather requirements, generate agent spec with GitHub MCP connector, create via `harness_create`
- "Update my code coverage agent to use a different model" - Fetch agent with `harness_get`, modify spec, update via `harness_update`
- "Build an agent that runs tests and reports results to Slack" - Multi-MCP setup with GitHub and Slack connectors
- "Create an autonomous agent to fix failing tests" - Agent with shell steps and Claude Code plugin

## Troubleshooting

### Connector Not Found

1. Verify the connector exists in Harness UI with the exact ID used in the agent spec
2. Check that the connector is in the correct scope (account/org/project)
3. Create the connector using `harness_create` with `resource_type="connector"` if it doesn't exist

### MCP Tools Not Available

1. Verify `mcpConnectors` input includes the correct connector IDs
2. Check that MCP connectors are properly configured with valid endpoints
3. Ensure the connector has the necessary permissions for the MCP server

### Agent Task Failing

1. Check `max_turns` is sufficient for task complexity (increase if needed)
2. Verify all input references use correct syntax: `${{ inputs.variableName }}`
3. Review task instructions for clarity and completeness

## Best Practices

- Use `type: connector` for LLM and MCP access
- **Prefer inputs over environment variables** for all configuration
- Include meaningful descriptions on all inputs
- Provide detailed step-by-step instructions in `task` field with `## RULES` section
- Adjust `max_turns` based on task complexity (100-200)
- Always use placeholder connector IDs and notify users to replace them
- Create connectors via Harness UI or `harness_create` with `resource_type="connector"`

