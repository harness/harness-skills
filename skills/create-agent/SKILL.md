---
name: create-agent
description: >-
  Create and update Harness AI agent instances for automated code and infrastructure tasks. Supports
  multi-stage execution, MCP server integration, LLM connector configuration, runtime inputs, repository
  cloning, and task/rules-based instruction. Use when asked to create an agent, update agent spec,
  modify agent configuration, automate tasks, perform agentic workflows, build autonomous systems, or
  work with AI agents. Trigger phrases: create agent, update agent, modify agent spec, AI agent,
  autonomous agent, agentic pipeline, automation task, automate workflow, Harness agent, code coverage
  agent, review agent, agentic task.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Agent

Create and update Harness AI agent instances for automated code, build agentic workflows, and infrastructure tasks.

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
3. **Refer to agent schema when needed** — If you're not sure about the YAML structure, use `harness_schema` with `resource_type="agent-pipeline"` to explore available fields and sections
   - **Use the `path` parameter to avoid context pollution**: The full schema is 4k+ lines. Load only what you need:
     - `harness_schema(resource_type="agent-pipeline")` → Top-level summary (shows available sections)
     - `harness_schema(resource_type="agent-pipeline", path="Agent")` → Agent structure only
     - `harness_schema(resource_type="agent-pipeline", path="stages")` → Stage definitions only
   - **For operations/API metadata**: Use `harness_describe(resource_type="agent")` to see supported operations, filters, and execute actions
   - **CRITICAL**: The agent spec uses first-class `agent` format (version: 1, agent:, stages:, etc.), NOT `pipeline` format

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

4. **MCP servers** (`mcp_servers` in spec):
   - Identify which external services the agent needs to interact with
   - GitHub? → Recommend GitHub Copilot MCP: `https://api.githubcopilot.com/mcp/`
   - Harness platform? → Recommend Harness MCP URL
   - Slack/notifications? → Recommend notification MCP
   - Recommend MCPs based on the user's task or workflows

5. **Secrets** (via `<+secrets.getValue("key")`):
   - List all secrets needed for authentication (GitHub PAT, API keys, tokens)
   - Remind user to create these in Harness UI before running the agent
   - Example: `bedrock_api_key`, `github_pat`, `slack_token`

6. **Connectors**:
   - GitHub/GitLab/Bitbucket connector for repository access
   - Container registry connector for custom images (if needed)
   - Cloud connectors (if agent interacts with AWS/GCP/Azure)

7. **Tools** (`with.allowed_tools`):
   - Recommend tools based on what the agent needs to do
   - File operations: `Read`, `Write`, `Grep`, `Glob`
   - MCP tools: `mcp__github__*`, `mcp__harness__*` (use `*` for all tools from that MCP)
   - Shell: `Bash`

**Present this recommended configuration to the user and iterate until confirmed.**

#### 3. Default Configuration

**Use these defaults unless user specifies otherwise:**

**Repository clone:**
- Only add this section if the task depends on a repository
```yaml
clone:
  depth: 1000
  ref:
    type: branch
    name: main
  repo: <repo>
  connector: <connector>
```

**Platform:**
```yaml
platform:
  os: linux
  arch: arm64
```

**Container image:**
- The Claude Code plugin is packaged via this image
```yaml
container:
  image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/claude-code-plugin:main
```

**Environment variables (Bedrock configuration):**
```yaml
env:
  ANTHROPIC_MODEL: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw
  AWS_BEARER_TOKEN_BEDROCK: <+secrets.getValue("bedrock_api_key")>
  AWS_REGION: us-east-1
  CLAUDE_CODE_USE_BEDROCK: "1"
```

**Max turns:**
- Depending on task complexity, adjust this in the range from 100 to 200
```yaml
max_turns: 150
```

#### 4. MCP Servers

Based on the MCPs needed (clarified with the user), configure MCP server connections:

**How to Connect MCP Servers?**

**Remote MCP Server:**
- If your MCP server is publicly accessible, connect it directly using a Personal Access Token (PAT)
- Create a secret in Harness for the PAT and reference it in the agent YAML

Example — Remote MCP Server:
```yaml
mcp_servers:
  harness:
    url: https://<your-ngrok-url>/mcp
  github:
    url: https://api.githubcopilot.com/mcp/
    headers:
      Authorization: Bearer <+secrets.getValue("github_pat")>
```

**Local MCP Server:**
- Use ngrok to expose your local MCP server so the Harness runner can reach it

Example — Single MCP Server:
```yaml
mcp_servers:
  harness:
    url: https://<your-ngrok-url>/mcp
```

**Allowing MCP Tools:**
- To allow the coding agent to use MCP tools, add `mcp__name__*` in `allowed_tools`
- Optionally specify a `log_file` for debugging MCP interactions
```yaml
mcp_servers:
  harness:
    url: https://<your-ngrok-url>/mcp
with:
  allowed_tools: Read,Edit,Bash,Glob,Grep,Write,mcp__harness__*
  log_file: .agent/output/mcp-test-log.jsonl
```

**Common MCP servers:**
- **GitHub/Code/PRs**: `https://api.githubcopilot.com/mcp/` with `Bearer <+secrets.getValue("github_pat")>`
- **Harness platform**: `https://<your-harness-mcp-url>/mcp` with Bearer token
- **Slack/Notifications**: `https://<your-slack-mcp-url>/mcp` with Bearer token
- **Grafana**: `https://<your-grafana-mcp-url>/mcp` (dashboards, alerts, annotations) with Bearer token
- **Datadog**: `https://<your-datadog-mcp-url>/mcp` with Bearer token
- **Jira**: `https://<your-jira-mcp-url>/mcp` with Bearer token
- **PagerDuty**: `https://<your-pagerduty-mcp-url>/mcp` with Bearer token

#### 5. MCP Tool Access
- **All tools**: `mcp__harness__*,mcp__github__*,Read,Edit,Bash,Glob,Grep,Write`
- **Specific tools**: `mcp__github__create_pr,mcp__github__list_files,Read,Write`

#### 6. Runtime Inputs (optional)
**Only add `inputs` section in the agent spec if user confirms it's needed.**

## Inputs

```yaml
agent:
  inputs:
    branch:
      type: string
      default: main
    version:
      type: string
      required: true
    deploy_env:
      type: string
      enum: [dev, staging, prod]
    api_key:
      type: secret
      default: account.my_secret
```

**Input types:** `string`, `secret`, `boolean`

**Reference inputs with:** `${{ inputs.branch }}`

Common input examples:
- `repo` (string): Repository identifier
- `llmKey` (secret): LLM API key
- `executionId` (string): Pipeline execution ID
- `branch` (string): Branch to analyze

**Expression syntax:**
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

### Phase 3: Generate Agent Spec

Using the requirements from Phase 2 and defaults from section 3-6, assemble the complete agent YAML specification (`spec` field):

1. Start with `version: 1` and `agent:` structure
2. Add `clone:` section if task depends on repository
3. Create `stages:` with platform (linux/arm64) and steps
4. For each step, include:
   - Container image and connector
   - Environment variables (Bedrock configuration)
   - `task:` field with step-by-step instructions AND a `## RULES` section at the end containing user preferences
   - `mcp_servers:` based on external services needed
   - `with.allowed_tools:` and `with.log_file:`
   - `max_turns:` adjusted for task complexity (100-200)
5. Add `inputs:` section only if confirmed with user (reference with `${{ inputs.fieldName }}`)

Generate complete, valid YAML ready to be used as the `spec` value.

### Phase 4: Present for Review

Present the complete agent configuration to the user:
- Agent metadata (name, description, uid)
- Full spec YAML
- Required secrets and connectors

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

## Agent YAML Extends Pipeline Constructs

**CRITICAL UNDERSTANDING: Agent YAML extends the traditional Harness pipeline schema. You can use BOTH agent-specific features AND traditional pipeline steps.**

### What This Means

1. **Agent-specific features** (new):
   - `agent` step type with `task`, `rules`, `mcp_servers`, `max_turns`
   - Claude Code plugin integration
   - MCP server connections
   - AI-powered autonomous execution

2. **Traditional pipeline features** (still valid):
   - Shell script steps (`run.shell`, `run.script`)
   - Container plugin steps (`run.container`)
   - Step groups
   - Parallel execution
   - Environment variables
   - Conditional execution
   - All other standard pipeline constructs
   - **Only use these when the requirement needs them or user explicitly requests them — don't add unnecessarily**
   - **For traditional pipeline constructs**: Reference the `/create-pipeline-v1` skill to look up native actions, templates, and step syntax if it's available

### When to Use Traditional Steps

- **Shell scripts**: For running git commands, file operations, or custom scripts
- **Container plugins**: For integrating with existing Harness plugins (SonarQube, Snyk, etc.)
- **Mixed workflows**: Combine agent steps with traditional steps in the same pipeline

### Example: Mixed Agent and Shell Steps

```yaml
version: 1
agent:
  stages:
    - name: Build and Analyze
      id: build_analyze
      platform:
        os: linux
        arch: arm64
      steps:
        # Traditional shell step
        - name: Run Tests
          run:
            shell: bash
            script: |-
              go test -cover ./...
              echo "Tests completed"
        
        # Agent step (AI-powered)
        - id: analyze_coverage
          name: Analyze Coverage with AI
          agent:
            container:
              image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/claude-code-plugin:main
            env:
              ANTHROPIC_MODEL: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw
              AWS_BEARER_TOKEN_BEDROCK: <+secrets.getValue("bedrock_api_key")>
              AWS_REGION: us-east-1
              CLAUDE_CODE_USE_BEDROCK: "1"
            task: |
              Analyze the test coverage output and generate improvement recommendations.
              
              ## RULES
              - Focus on actionable recommendations
              - Prioritize high-impact improvements
            max_turns: 100
```

### Schema Validation

All agent specs are validated using `harness_schema(resource_type="agent-pipeline")` which supports BOTH:
- Agent-specific constructs (use `path="Agent"` to explore)
- Traditional pipeline constructs (use `path="stages"`, `path="steps"` to explore)

**If a user asks to add shell steps, container steps, or any traditional pipeline feature, it's perfectly valid to include them in the agent spec.**

### Chaining Agents Together

**⚠️ ADVANCED FEATURE: THIS IS FOR ADVANCED USERS ONLY. BUILD SINGLE-AGENT WORKFLOWS FIRST AND ONLY USE AGENT CHAINING WHEN YOU HAVE PUSHED A SINGLE AGENT TO ITS ABSOLUTE LIMIT. SINGLE AGENTS ARE EXTREMELY POWERFUL AND EFFICIENT — MOST TASKS DO NOT REQUIRE CHAINING.**

**Agents can pass data to each other by writing outputs to fixed file locations and reading from those locations in subsequent steps.**

#### How Agent Chaining Works

1. **Agent 1** outputs its results to a fixed file location using `with.log_file`
2. **Agent 2** reads from that file location in its `task` instructions
3. This creates a sequential chain where each agent builds on the previous agent's work

#### Key Pattern

```yaml
steps:
  # First agent - outputs to fixed location
  - id: analyzer
    name: Analyze Code
    agent:
      task: |
        Analyze the codebase and write findings to analysis-report.md
      with:
        allowed_tools: Read,Write,Grep,Glob
        log_file: .agent/output/analyzer-log.jsonl  # ← Agent 1 outputs here
      max_turns: 100

  # Second agent - reads from first agent's output
  - id: recommender
    name: Generate Recommendations
    agent:
      task: |
        Read the analysis from .agent/output/analyzer-log.jsonl  # ← Agent 2 reads here
        and generate actionable recommendations.
      with:
        allowed_tools: Read,Write
        log_file: .agent/output/recommender-log.jsonl
      max_turns: 50
```

**Important:** The file path (`.agent/output/analyzer-log.jsonl`) must match exactly between the first agent's `log_file` and the second agent's `task` instructions. This creates the handoff between agents.

### Adding Custom Skills to Agents

**IMPORTANT: This is NOT a default feature. Only add custom skills when the user explicitly insists on it.**

By default, agents work with the task instructions provided in the `task` field. Custom skills are an advanced feature and should only be added if the user specifically requests them.

**Example: Adding a Custom Skill**

```yaml
version: 1
agent:
  stages:
    - name: Setup and Execute
      id: setup_execute
      platform:
        os: linux
        arch: arm64
      steps:
        # Step 1: Create custom skill (runs BEFORE agent step)
        - id: create_skill
          name: Setup Hello World Skill
          run:
            shell: bash
            script: |
              mkdir -p /harness/.claude/skills/hello-world
              cat > /harness/.claude/skills/hello-world/SKILL.md << 'EOF'
              ---
              name: hello-world
              description: Responds to greetings with a funny joke
              triggers:
                - hi
                - hello
                - hii claude
              ---

              You are a greeting assistant.

              When the user says "hi", "hello", or "hii claude":
              - Respond with "Hi!"
              - Include a short funny joke

              Keep responses short and fun.
              EOF

        # Step 2: Agent step (can now use the custom skill)
        - id: run_agent
          name: Run Agent with Custom Skill
          agent:
            container:
              image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/claude-code-plugin:main
            env:
              ANTHROPIC_MODEL: arn:aws:bedrock:us-east-1:587817102444:application-inference-profile/7p8sn93lhspw
              AWS_BEARER_TOKEN_BEDROCK: <+secrets.getValue("bedrock_api_key")>
              AWS_REGION: us-east-1
              CLAUDE_CODE_USE_BEDROCK: "1"
            task: |
              Execute the task using the available skills.

              ## RULES
              - Use the hello-world skill when appropriate
            max_turns: 100
```

**Key Points:**
- The working directory for the agent is `/harness`
- Skills path format: `/harness/.claude/skills/<skill-name>/SKILL.md`
- Use heredoc (`<< 'EOF'`) to write multi-line skill files
- The skill file must include valid frontmatter and instructions
- Multiple skills can be created in the same step by repeating the mkdir/cat commands

## CRITICAL GUIDELINES

**These are essential rules you MUST follow when creating/updating agents:**

| Guideline                | Rule                                                                                                                                     |
| --------------------------| ------------------------------------------------------------------------------------------------------------------------------------------|
| **Check existing first** | Always call `harness_list(resource_type="agent")` to see if an existing agent can solve the use case before creating new                 |
| **Updating agents**      | Use `harness_get` to retrieve current config, then `harness_update` (not `harness_create`) to modify. Only custom agents can be updated. |
| **Use schema tool**      | Use `harness_schema(resource_type="agent-pipeline", path="...")` for YAML structure. Use `path` parameter to load specific sections only |
| **Agent spec format**    | The `spec` field contains agent YAML (version: 1, agent:, stages:, etc.) — this is NOT pipeline format                                   |
| **Secrets**              | Reference as `<+secrets.getValue("key")>` — user must create in Harness UI                                                               |
| **Connectors**           | Reference by identifier (e.g. `connector_github_id`, `account.harnessImage`) — must exist before agent execution                         |
| **Multi-stage**          | Steps run sequentially — pass state between stages via files (e.g. INFO.md)                                                              |
| **Quality first**        | Agent quality is paramount — verify YAML structure, validate all references, ensure complete task instructions before creating           |


## Examples

- "Create an agent that reviews PRs for security issues" - Gather requirements, generate agent spec with GitHub MCP, create via `harness_create`
- "Update my code coverage agent to use a different model" - Fetch agent with `harness_get`, modify spec, update via `harness_update`
- "Build an agent that runs tests and reports results to Slack" - Multi-MCP setup with GitHub and Slack servers
- "Create an autonomous agent to fix failing tests" - Agent with repo clone, shell steps, and Claude Code plugin

## Performance Notes

- Use `harness_schema(resource_type="agent-pipeline", path="...")` with specific `path` values to avoid loading the full 4k+ line schema into context.
- Always check for existing agents with `harness_list` before creating new ones to avoid duplicates.
- Set `max_turns` proportional to task complexity: 100 for simple tasks, 150-200 for complex multi-step workflows.
- Use `depth: 1` for branch clones and `depth: 1000` for PR clones to balance clone speed and diff history.

## Troubleshooting

### SCM Provider Detection Failing

1. Verify `DRONE_REPO_SCM` environment variable is available
2. Check that connector tokens have correct permissions
3. Test with a known SCM provider before adding multi-provider logic

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
- Provide detailed step-by-step instructions in `task` field
- Increase `max_turns` in the spec (default: 150) if task is complex.

