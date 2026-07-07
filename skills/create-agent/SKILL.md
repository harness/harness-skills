---
name: custom-ai-agents
description: >-
  Create and update Harness AI agent instances - standalone templates for agentic workflows in pipelines. Use when asked to create agent, update agent, modify agent spec, build autonomous systems, or work with AI agents.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  module: global
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Custom AI Agents

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
- **UID/UUID**: Always generate this from the name and pass it explicitly to create/update APIs. Do not rely on the create API fallback.
  - Generation rule : prefix with `ca_`, then lowercase the name, convert spaces and hyphens (`-`) to `_`, replace any remaining non-alphanumeric runs with `_`, collapse duplicate `_`, and trim leading/trailing `_` from the slug portion (e.g. "Code Coverage Agent" → `ca_code_coverage_agent`, "PR Reviewer" → `ca_pr_reviewer`)
  - If the generated UID conflicts with an existing agent, ask the user whether to reuse/update that agent or append a short suffix

#### 2. Task Details - Interactive Requirements Gathering

**Ask and clarify the following with the user:**

1. **Agent's exact goal**: What specific outcome should the agent achieve? Be specific — avoid vague goals.
2. **Inputs the agent needs**: Repository info? Execution context? Configuration? Secrets?
3. **Outputs the agent produces**: Files? External actions? Data/metrics?
4. **What the agent works on**: Specific file paths? External services? Databases/APIs?
5. **Task workflow**: Step-by-step workflow (do 1, then 2, then 3, etc.)
6. **Constraints and preferences**: Limitations, rules, or coding standards (e.g., "Use idiomatic Go code", "Do not modify existing tests")
7. **Definition of done**: How do you know the agent succeeded? Specific criteria, artifacts, or exit conditions.

#### 3. Recommend Configuration

Based on requirements, recommend and verify with the user:

1. **Task instructions** (`task` field):
   - Break down the goal into detailed step-by-step instructions
   - Include specific commands, file paths, and expected outcomes
   - Reference inputs using `${{inputs.fieldName}}` syntax inside `PLUGIN_TASK` and other env vars
   - Add `## RULES` section at the end with constraints formatted as markdown bullet points

2. **Runtime inputs** (`inputs` section in spec):
   - Only add if user confirms runtime parameters are needed
   - Map each input to what the agent needs (repo, branch, executionId, thresholds, etc.)
   - **Always set a `default` value for every non-required input** — if `${{inputs.fieldName}}` is referenced in `PLUGIN_TASK` or any env var and no value is supplied at runtime nor a default exists, the agent will error at execution time
   - Always include `allowedDomains` so users understand and control non-LLM/non-MCP network access

3. **Connectors**:
   - LLM connector for model access (required for all agents) - User must create via Harness UI or MCP
   - MCP connectors for external services (GitHub, Slack, Harness platform, etc.) - only if needed
   - All authentication and secrets are managed within the connectors

**Present this recommended configuration to the user and iterate until confirmed.**

#### 4. Default Configuration & Inputs

**Agent Structure:** Agents use `agent.step.group.steps` format — the run step is nested inside a named step group.

**Default structure:**
```yaml
version: 1
agent:
  step:
    group:
      steps:
        - name: Agent
          if: <+Always>
          id: agent
          run:
            container:
              image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/harness-ai-agent:latest
            env:
              PLUGIN_TASK: |
                <step-by-step task instructions>
              PLUGIN_MAX_TURNS: 150
              PLUGIN_HARNESS_CONNECTOR: ${{inputs.llmConnector.id}}
              PLUGIN_ALLOWED_DOMAINS: ${{inputs.allowedDomains}}
```

**Required environment variables:**
```yaml
env:
  PLUGIN_TASK: |                                   # Task instructions go here as a multiline string
    <step-by-step instructions>
  PLUGIN_MAX_TURNS: 150                            # Adjust 100-200 based on task complexity
  PLUGIN_HARNESS_CONNECTOR: ${{inputs.llmConnector.id}}  # References llmConnector input's id property
  PLUGIN_ALLOWED_DOMAINS: ${{inputs.allowedDomains}}      # Regexes for additional network access
```

**MCP configuration (only if external services needed):**
```yaml
env:
  PLUGIN_MCP_FORMAT: harness
  PLUGIN_MCP_SERVERS: <+connectorInputs.resolveList(<+inputs.mcpConnectors>)>  # References mcpConnectors input
```

**Optional model override (only if user explicitly requests it):**
```yaml
env:
  ANTHROPIC_MODEL: ${{inputs.modelName}}  # Only add when user insists on a modelName input
```

**Required inputs (always include):**
```yaml
agent:
  inputs:
    llmConnector:
      type: connector
      required: true
      default: your_llm_connector_id  # User must replace with actual connector ID
      ui:
        connectorCategories:
          - AI

    allowedDomains:
      type: string
      default: ""
```

**Network access:** Agent network access is limited to the LLM connector, configured MCP connectors, and domains matching `allowedDomains`. `allowedDomains` accepts regexes separated by `|`. Default to an empty string if the user does not specify domains; if they do specify domains, work with them to build the right regex.

**Optional inputs (add as needed):**
```yaml
    # MCP connectors - only if agent needs external services
    mcpConnectors:
      type: array
      default:
        - your_github_mcp_connector  # User must replace
        - your_slack_mcp_connector   # User must replace
      ui:
        component: array
        input:
          inputType: connector
          inputConfig:
            connectorTypes:
              - Mcp
    
    # Model name override - ONLY add if user explicitly requests it
    modelName:
      type: string
      default: your_model_arn_or_id  # User must replace with their model ARN or ID
    
    # Custom parameters
    repo_name:
      type: string
      default: my-org/my-repo
```

**`layout` block (always include, only list fields that are present as inputs):**

The `layout` block controls what appears in the agent configuration UI. It contains **at most four items** — `llmConnector`, `allowedDomains`, `modelName`, and `mcpConnectors` — and only those that exist as first-class input fields in the `inputs` section. Never include any other fields (e.g. custom inputs like `repo_name`) in the layout block:

```yaml
agent:
  layout:
    - title: Agent Configuration
      items:
        - llmConnector          # always present
        - allowedDomains        # always present
        - modelName             # only if modelName input exists
        - mcpConnectors         # only if mcpConnectors input exists
```

**Supported input types:** `string`, `secret`, `boolean`, `connector`, `array`

**IMPORTANT:** Users must create connectors via Harness UI or `harness_create` with `resource_type="connector"` before running the agent.

### Phase 3: Generate Agent Spec

Assemble the complete agent YAML specification (`spec` field):

1. Start with `version: 1` and `agent:` structure
2. Create `agent.step.group.steps` block with a single step entry:
   - `name: Agent`, `if: <+Always>`, `id: agent`
   - `run.container.image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/harness-ai-agent:latest`
   - `run.env` section (all task config lives here as env vars):
     - `PLUGIN_TASK:` — multiline string with step-by-step instructions and `## RULES` section
     - `PLUGIN_MAX_TURNS: 150` (adjust 100-200 based on complexity)
     - `PLUGIN_HARNESS_CONNECTOR: ${{inputs.llmConnector.id}}`
     - `PLUGIN_ALLOWED_DOMAINS: ${{inputs.allowedDomains}}`
     - `PLUGIN_MCP_FORMAT: harness` (only if MCPs needed)
     - `PLUGIN_MCP_SERVERS: <+connectorInputs.resolveList(<+inputs.mcpConnectors>)>` (only if MCPs needed)
     - `ANTHROPIC_MODEL: ${{inputs.modelName}}` (**only** if user explicitly requests a `modelName` input)
3. Add `agent.inputs` section with:
   - `llmConnector` (required) with `ui.connectorCategories: [AI]`
   - `allowedDomains` (default `""`) to allow additional network domains using regexes
   - `mcpConnectors` (optional - only if needed) with `ui.component: array`, `ui.input.inputType: connector`, and `ui.input.inputConfig.connectorTypes: [Mcp]`
   - `modelName` (optional - **only** if user explicitly requests it)
   - Custom inputs (as needed)
4. Add `agent.layout` block — only include items that are present as inputs:
   - Always include `llmConnector`
   - Always include `allowedDomains`
   - Include `modelName` only if that input exists
   - Include `mcpConnectors` only if that input exists

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
    uid: "<generated_from_agent_name>",
    name: "<Agent Display Name>",
    description: "<Brief description of agent purpose>",
    spec: "<agent YAML spec as a string>",
    wiki: "<optional: markdown documentation>"
  }
```

**Key fields for creation:**
- `uid` (required): Unique identifier. Always generate from `name` as `ca_<slug>` and send explicitly (e.g. "Code Coverage Agent" → `ca_code_coverage_agent`). Do not omit it or rely on API-side auto-generation.
- `name` (required): Display name for the agent
- `description` (optional): Brief description
- `spec` (required): The full agent YAML specification as a string (includes `version: 1`, `agent:`, `agent.step.group.steps`, `agent.inputs`, and `agent.layout`)
- `wiki` (optional): Markdown documentation for the agent

#### Updating an Existing Agent

```
Call MCP tool: harness_update
Parameters:
  resource_type: "agent"
  resource_id: "<agent_identifier>"
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
    group:
      steps:
        - name: Agent
          if: <+Always>
          id: agent
          run:
            container:
              image: pkg.harness.io/vrvdt5ius7uwygso8s0bia/harness-agents/harness-ai-agent:latest
            env:
              PLUGIN_TASK: |
                Review the pull request for repository ${{inputs.repo_name}} on branch ${{inputs.branch}}.

                1. Analyze code changes for security vulnerabilities
                2. Check for code quality issues
                3. Verify test coverage
                4. Post review comments using GitHub MCP tools

                ## RULES
                - Focus on critical security issues first
                - Be constructive in feedback
                - Suggest specific code improvements
              PLUGIN_MAX_TURNS: 150
              PLUGIN_HARNESS_CONNECTOR: ${{inputs.llmConnector.id}}
              PLUGIN_ALLOWED_DOMAINS: ${{inputs.allowedDomains}}
              PLUGIN_MCP_FORMAT: harness
              PLUGIN_MCP_SERVERS: <+connectorInputs.resolveList(<+inputs.mcpConnectors>)>

  inputs:
    llmConnector:
      type: connector
      required: true
      default: your_llm_connector_id  # User must replace with actual connector ID
      ui:
        connectorCategories:
          - AI

    allowedDomains:
      type: string
      default: ""

    mcpConnectors:
      type: array
      default:
        - your_github_mcp_connector  # User must replace with actual connector ID
      ui:
        component: array
        input:
          inputType: connector
          inputConfig:
            connectorTypes:
              - Mcp

    repo_name:
      type: string
      default: my-org/my-repo

    branch:
      type: string
      default: main

  layout:
    - title: Agent Configuration
      items:
        - llmConnector
        - allowedDomains
        - mcpConnectors
```

## Using Agents in Pipelines

Once an agent is created, it is published as a template and can be used in pipelines. The agent can be referenced in both v0 and v1 pipeline YAML formats.

### v1 Pipeline YAML (Template-based)

In v1 pipelines, the agent template exposes its custom inputs (excluding `llmConnector` and `mcpConnectors`, which are handled internally).

**Example: Using Code Review Agent in a v1 Pipeline**

Assuming you created a "Code Review Agent" with custom inputs `repo_name` and `branch`:

```yaml
pipeline:
  identifier: code_review_pipeline
  name: Code Review Pipeline
  inputs:
    repo_name:
      type: string
      default: my-org/my-repo
    branch:
      type: string
      default: feature/new-feature
  stages:
    - name: Code Review
      steps:
        - name: review_pr
          template:
            uses: ca_code_review_agent@1.0.0
            with:
              repo_name: <+inputs.repo_name>
              branch: <+inputs.branch>
```

**Key points:**
- Pipeline-level `inputs:` section defines runtime parameters
- `uses: <agent_uid>@<version>` references the published agent template
- `with:` block provides values for the agent's custom inputs using `<+inputs.variableName>` syntax
- `llmConnector` and `mcpConnectors` are configured at the agent level by default
- `modelName` is optional — only present in the agent if the user explicitly requested it
- Optionally, you can override `llmConnector` (and `modelName` if it exists) at the pipeline level if needed
- Only custom inputs (like `repo_name`, `branch`, thresholds, etc.) are passed in the pipeline

### v0 Pipeline YAML (Agent Step Type)

In v0 pipelines, agents are referenced using the `Agent` step type, which internally references the v1 template. The step expands the v1 template and converts it to a v0 Run Step.

**Example: Using Code Review Agent in a v0 Pipeline**

```yaml
pipeline:
  stages:
    - stage:
        type: Deployment
        spec:
          execution:
            steps:
              - stepGroup:
                  stepGroupInfra:
                    type: KubernetesDirect
                  steps:
                    - step:
                        type: Agent
                        name: ReviewPRAgent
                        identifier: ReviewPRAgent
                        spec:
                          agentName: ca_code_review_agent
                          agentSettings: |-
                            {
                              "repo_name": "my-org/my-repo",
                              "branch": "feature/new-feature",
                              "llmConnector": "your_llm_connector_id",
                              "modelName": "your_model_arn_or_id",
                              "mcpConnectors": ["your_github_mcp_connector", "your_slack_mcp_connector"]
                            }
                          llmConnector: your_llm_connector_id
                          mcpConnectors:
                            - your_github_mcp_connector
```

**Key fields explained:**

- `type: Agent` - Step type for v0 pipelines that references a v1 agent template
- `name` (required) - Display name for the step in the pipeline UI
- `identifier` (required) - Unique identifier for the step within the pipeline
- `agentName` (required) - The agent's UID (v1 template identifier) created via `harness_create`
- `agentSettings` (optional) - JSON string containing template inputs for the agent:
  - **Custom inputs**: Agent-specific fields like `repo_name`, `branch`, thresholds, etc.
  - **llmConnector**: LLM connector ID (overrides agent default and first-class field)
  - **modelName**: Model ARN or ID — only present if the agent was created with a `modelName` input
  - **mcpConnectors**: Array of MCP connector IDs (overrides agent default and first-class field)
- `llmConnector` (optional) - First-class field to specify LLM connector ID at pipeline level
- `mcpConnectors` (optional) - First-class array field to specify MCP connector IDs at pipeline level

**Precedence rules:**
1. Values in `agentSettings` JSON have **highest precedence** - they override both agent defaults and first-class fields
2. First-class fields (`llmConnector`, `mcpConnectors`) override agent defaults
3. If neither are provided, the agent's default configuration from the template is used

## CRITICAL GUIDELINES

**These are essential rules you MUST follow when creating/updating agents:**

| Guideline                  | Rule                                                                                                                                     |
| ----------------------------| ------------------------------------------------------------------------------------------------------------------------------------------|
| **Check existing first**   | Always call `harness_list(resource_type="agent")` to see if an existing agent can solve the use case before creating new                                                     |
| **Updating agents**        | Use `harness_get` to retrieve current config, then `harness_update` (not `harness_create`) to modify. Only custom agents can be updated.                                     |
| **Generate UID**           | Always derive `uid` as `ca_<slug>` (e.g. "Code Coverage Agent" → `ca_code_coverage_agent`) — matches platform UI `nameToUid()`. Pass it explicitly; do not rely on create API fallback. |
| **Agent spec format**      | The `spec` field uses `agent.step.group.steps` structure — the run step is nested inside a named group with `name: Agent`, `if: <+Always>`, `id: agent`                     |
| **Task in env**            | Task instructions go in `PLUGIN_TASK` env var (multiline string). Max turns in `PLUGIN_MAX_TURNS`. There is no `with:` block.                                                |
| **Expression syntax**      | Use `${{inputs.fieldName}}` inside env values. Use `<+connectorInputs.resolveList(...)>` for MCP server resolution.                                                          |                |
| **modelName is optional**  | Do NOT add `modelName` input or `ANTHROPIC_MODEL` env var by default — only add when the user explicitly requests it                                                         |
| **Allowed domains**       | Always include `PLUGIN_ALLOWED_DOMAINS: ${{inputs.allowedDomains}}`, an `allowedDomains` string input with default `""`, and `allowedDomains` in layout. If the user specifies domains, help build the regex. |
| **Input defaults**         | Every non-required input that is referenced via `${{inputs.fieldName}}` **must have a `default` value** — omitting it causes a runtime error if the caller does not supply the value  |
| **Connector placeholders** | Always use placeholders like `your_llm_connector_id` and `your_mcp_connector_id` and notify users to replace both LLM and MCP connector IDs with actual values before running the agent |
| **No clone/platform**      | Do NOT add `clone`, `platform`, `os`, `arch`, or `allowed_tools` sections — agents are standalone with simplified structure                                                  |
| **Quality first**          | Agent quality is paramount — verify YAML structure, validate all references, ensure complete task instructions before creating                                                |
