# Harness Skills

Claude Code skills for the [Harness.io](https://harness.io) CI/CD platform. Generate pipeline YAML, manage resources, debug failures, analyze costs, and more from natural language.

This repository is designed as a workflow system, not just a folder of prompts. The top-level instructions (`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`) establish shared behavior, while individual skills specialize in creation, debugging, governance, and reporting tasks.

## Prerequisites

- [Harness MCP v2 Server](https://github.com/harness/mcp-server) - required for MCP-powered skills. Most skills in this repo depend on it for Harness API access.

## Setup

### Claude Code

Clone the repo and run Claude Code from the project directory. Skills are automatically discovered from `CLAUDE.md` and `skills/*/SKILL.md`:

```bash
git clone https://github.com/harness/harness-skills.git
cd harness-skills
claude
```

To add the Harness MCP server, configure it in your Claude Code settings (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "harness-mcp-v2": {
      "command": "npx",
      "args": ["-y", "harness-mcp-v2"],
      "env": {
        "HARNESS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

Invoke skills by name:

```
/create-pipeline
Create a CI pipeline for a Node.js app that builds, runs tests,
and pushes a Docker image to ECR
```

### Cursor

1. Clone the repo into your project or as a reference workspace:

```bash
git clone https://github.com/harness/harness-skills.git
```

2. The repo includes `.cursor/rules/harness.mdc`, which Cursor automatically loads as a project rule.

3. Configure the Harness MCP server in Cursor (`~/.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "harness-mcp-v2": {
      "command": "npx",
      "args": ["-y", "harness-mcp-v2"],
      "env": {
        "HARNESS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

4. Reference individual skills in your prompts using `@file`:

```
@harness-skills/skills/create-pipeline/SKILL.md
Create a CI pipeline for my Go service
```

### OpenAI Codex

1. Clone the repo into your working directory:

```bash
git clone https://github.com/harness/harness-skills.git
```

2. The repo includes `AGENTS.md` at the root, which Codex automatically reads as system instructions.

3. Configure the Harness MCP server in your Codex MCP config:

```json
{
  "mcpServers": {
    "harness-mcp-v2": {
      "command": "npx",
      "args": ["-y", "harness-mcp-v2"],
      "env": {
        "HARNESS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

4. Reference individual skill files as context when prompting:

```
Using the instructions in harness-skills/skills/debug-pipeline/SKILL.md,
diagnose why my deploy pipeline failed
```

### GitHub Copilot

1. Clone the repo into your project:

```bash
git clone https://github.com/harness/harness-skills.git
```

2. The repo includes `.github/copilot-instructions.md`, which Copilot automatically reads as project-level context in both GitHub.com and VS Code.

3. For VS Code, configure the Harness MCP server in your workspace settings (`.vscode/mcp.json`):

```json
{
  "servers": {
    "harness-mcp-v2": {
      "command": "npx",
      "args": ["-y", "harness-mcp-v2"],
      "env": {
        "HARNESS_API_KEY": "<your-api-key>"
      }
    }
  }
}
```

4. Reference skill files in Copilot Chat using `#file`:

```
#file:harness-skills/skills/create-pipeline/SKILL.md
Create a CI pipeline for my Python service
```

5. For GitHub Copilot on GitHub.com, attach skill files as context in Copilot Chat or add them as knowledge base references in your Copilot organization settings.

### Windsurf / Other AI Editors

The skills in this repo are plain Markdown files with YAML frontmatter. They work with any AI coding tool that supports:

1. **System instructions** - Use `CLAUDE.md` as project-level context.
2. **MCP servers** - Connect the [Harness MCP v2 server](https://github.com/harness/mcp-server) for API access.
3. **File context** - Reference individual `skills/*/SKILL.md` files in prompts.

## Operating Model

The best Harness skills follow the same control flow even when they target different resource types:

1. **Establish scope first** - confirm account/org/project context before listing, creating, updating, or deleting resources.
2. **Verify dependencies before generating dependents** - do not reference connectors, secrets, environments, infrastructure, or templates that have not been confirmed to exist.
3. **Discover schema before writing payloads** - use `harness_describe` and API validation feedback instead of guessing field names or payload shape.

These repo-level playbooks live in:

- [`references/scope-establishment.md`](references/scope-establishment.md)
- [`references/dependency-check-playbook.md`](references/dependency-check-playbook.md)
- [`references/schema-validation-loop.md`](references/schema-validation-loop.md)
- [`templates/operation-summary.md`](templates/operation-summary.md)

## Workflow Modes

| Workflow mode | Representative skills | Use when |
|---------------|-----------------------|----------|
| Create and scaffold | `/create-pipeline`, `/create-service`, `/create-connector`, `/create-template` | You need to define or generate new Harness resources and their YAML or MCP payloads. |
| Run and debug | `/run-pipeline`, `/debug-pipeline`, `/migrate-pipeline`, `/manage-delegates` | You already have resources and need to execute, diagnose, or repair behavior. |
| Govern and secure | `/manage-roles`, `/manage-users`, `/create-policy`, `/security-report`, `/audit-report` | You need RBAC, policy, compliance, or security workflows with blast-radius awareness. |
| Analyze and report | `/dora-metrics`, `/analyze-costs`, `/scorecard-review`, `/template-usage` | You need structured reports, summaries, recommendations, or adoption analysis. |

## End-to-End Workflows

### New microservice setup

Use these skills in order:

1. `/create-connector`
2. `/create-secret`
3. `/create-service`
4. `/create-environment`
5. `/create-infrastructure`
6. `/create-pipeline`
7. `/create-trigger`

### Debug a failed deployment

Typical sequence:

1. `/run-pipeline` to identify the latest execution or reproduce the issue
2. `/debug-pipeline` to classify the failure and inspect root cause
3. `/template-usage` if shared templates may have propagated the issue
4. `/manage-delegates` if the failure points to delegate capacity or connectivity

## Skills

### Pipeline & Template Creation

| Skill | Description |
|-------|-------------|
| [`/create-pipeline`](skills/create-pipeline/SKILL.md) | Generate v0 Pipeline YAML (CI, CD, approvals, matrix strategies) |
| [`/create-pipeline-v1`](skills/create-pipeline-v1/SKILL.md) | Generate v1 simplified Pipeline YAML - **Alpha: internal testing only** |
| [`/create-template`](skills/create-template/SKILL.md) | Create reusable Step, Stage, Pipeline, or StepGroup templates |
| [`/create-trigger`](skills/create-trigger/SKILL.md) | Create webhook, scheduled, and artifact triggers |
| [`/create-agent-template`](skills/create-agent-template/SKILL.md) | Create AI-powered agent templates - **Alpha: internal testing only** |

### Resource Management

| Skill | Description |
|-------|-------------|
| [`/create-service`](skills/create-service/SKILL.md) | Create service definitions (K8s, Helm, ECS, Lambda) |
| [`/create-environment`](skills/create-environment/SKILL.md) | Create environment definitions with overrides |
| [`/create-infrastructure`](skills/create-infrastructure/SKILL.md) | Create infrastructure definitions |
| [`/create-connector`](skills/create-connector/SKILL.md) | Create connectors (Git, cloud, registries, clusters) |
| [`/create-secret`](skills/create-secret/SKILL.md) | Create secrets (text, file, SSH, WinRM) |

### Access Control & Feature Flags (MCP)

| Skill | Description |
|-------|-------------|
| [`/manage-users`](skills/manage-users/SKILL.md) | Manage users, user groups, and service accounts |
| [`/manage-roles`](skills/manage-roles/SKILL.md) | Manage role assignments and RBAC |
| [`/manage-feature-flags`](skills/manage-feature-flags/SKILL.md) | Create, list, toggle, and delete feature flags |

### Operations & Debugging (MCP)

| Skill | Description |
|-------|-------------|
| [`/run-pipeline`](skills/run-pipeline/SKILL.md) | Execute pipelines, monitor progress, handle approvals |
| [`/debug-pipeline`](skills/debug-pipeline/SKILL.md) | Analyze execution failures, diagnose root causes |
| [`/migrate-pipeline`](skills/migrate-pipeline/SKILL.md) | Convert pipelines from v0 to v1 format |
| [`/template-usage`](skills/template-usage/SKILL.md) | Track template dependencies and adoption |
| [`/manage-delegates`](skills/manage-delegates/SKILL.md) | Monitor delegate health and manage tokens |

### Platform Intelligence (MCP)

| Skill | Description |
|-------|-------------|
| [`/analyze-costs`](skills/analyze-costs/SKILL.md) | Cloud cost analysis and optimization (CCM) |
| [`/security-report`](skills/security-report/SKILL.md) | Vulnerability reports, SBOMs, compliance (SCS/STO) |
| [`/dora-metrics`](skills/dora-metrics/SKILL.md) | DORA metrics and engineering performance (SEI) |
| [`/gitops-status`](skills/gitops-status/SKILL.md) | GitOps application health and sync status |
| [`/chaos-experiment`](skills/chaos-experiment/SKILL.md) | Create and run chaos experiments |
| [`/scorecard-review`](skills/scorecard-review/SKILL.md) | Service maturity scorecards (IDP) |
| [`/audit-report`](skills/audit-report/SKILL.md) | Audit trails and compliance reports |
| [`/create-policy`](skills/create-policy/SKILL.md) | Create OPA governance policies for supply chain security |

## Project Structure

```
harness-skills/
├── skills/
│   ├── create-pipeline/
│   │   ├── SKILL.md
│   │   └── references/
│   ├── create-template/
│   │   └── SKILL.md
│   ├── debug-pipeline/
│   │   └── SKILL.md
│   └── ...                      # Skill definitions
├── references/                  # Shared repo-level playbooks
├── templates/                   # Shared repo-level output templates
├── scripts/
│   └── validate-skills.sh       # Structural validation
├── examples/
│   ├── v0/                      # v0 pipeline examples
│   ├── v1/                      # v1 pipeline examples
│   ├── templates/               # Template examples
│   ├── triggers/                # Trigger examples
│   ├── services/                # Service definition examples
│   ├── environments/            # Environment examples
│   ├── connectors/              # Connector examples
│   └── ...
├── .cursor/rules/harness.mdc    # Auto-loaded by Cursor
├── .github/copilot-instructions.md
├── AGENTS.md                    # Auto-loaded by OpenAI Codex
├── CLAUDE.md                    # Auto-loaded by Claude Code
├── CONTRIBUTING.md              # Contribution guidelines
├── LICENSE
└── README.md
```

## Shared Playbooks and Templates

Use root-level shared assets for behavior that should stay consistent across many skills:

- `references/` - reusable operating guidance such as scope establishment, dependency verification, and schema-validation loops
- `templates/` - reusable output contracts such as operation summaries and report formats

Use per-skill `references/` or `templates/` when the content is domain-specific and should not be imported broadly.

## Skill Anatomy

Each skill is a directory under `skills/` containing a `SKILL.md` with YAML frontmatter and a consistent markdown body:

```yaml
---
name: my-skill
description: >-
  Explain what the skill does, when to use it, when not to use it, and likely
  trigger phrases. Keep it under 1024 characters.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# My Skill

One or two sentences describing the operating mode and expected outcome.

## Instructions

Phase-based steps for Claude to follow.

## Examples

Invocation examples and, for complex skills, brief worked examples.

## Performance Notes

Validation checks, tradeoffs, or speed/accuracy guidance.

## Troubleshooting

Common errors, recovery steps, and expected fallbacks.
```

For complex skills, add `references/` or `templates/` under the skill directory rather than bloating `SKILL.md`.

## MCP Tools

MCP-powered skills use the [Harness MCP v2 server](https://github.com/harness/mcp-server), which provides 10 generic tools dispatched by `resource_type`:

| Tool | Purpose |
|------|---------|
| `harness_list` | List resources |
| `harness_get` | Get resource details |
| `harness_create` | Create a resource |
| `harness_update` | Update a resource |
| `harness_delete` | Delete a resource |
| `harness_execute` | Execute an action |
| `harness_search` | Search across resources |
| `harness_describe` | Get resource schema |
| `harness_diagnose` | Diagnose issues |
| `harness_status` | Check system status |

## Schema References

- [v0 Pipeline/Template/Trigger Schema](https://github.com/harness/harness-schema/tree/main/v0)
- [v1 Pipeline Spec](https://github.com/thisrohangupta/spec)
- [Agent Templates](https://github.com/thisrohangupta/agents)
- [Harness MCP v2 Server](https://github.com/harness/mcp-server)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for skill authoring standards, validation rules, and contribution workflow.

## License

This project is licensed under the [Apache License 2.0](LICENSE).

Copyright 2026 Harness Inc.
