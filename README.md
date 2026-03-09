# Harness Skills

Claude Code skills for the [Harness.io](https://harness.io) CI/CD platform. Generate pipeline YAML, manage resources, debug failures, analyze costs, and more -- all from natural language.

## Prerequisites

- [Harness MCP v2 Server](https://github.com/thisrohangupta/harness-mcp-v2) -- required for MCP-powered skills. Most skills in this repo depend on this server for Harness API access.

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

2. The repo includes `.cursor/rules/harness.mdc` which Cursor automatically loads as a project rule -- no manual copying needed.

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

2. The repo includes `AGENTS.md` at the root, which Codex automatically reads as system instructions -- no manual copying needed.

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

2. The repo includes `.github/copilot-instructions.md`, which Copilot automatically reads as project-level context in both GitHub.com and VS Code -- no manual copying needed.

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

1. **System instructions** -- Use `CLAUDE.md` as project-level context
2. **MCP servers** -- Connect the [Harness MCP v2 server](https://github.com/thisrohangupta/harness-mcp-v2) for API access
3. **File context** -- Reference individual `skills/*/SKILL.md` files in prompts

## Skills

### Pipeline & Template Creation

| Skill | Description |
|-------|-------------|
| [`/create-pipeline`](skills/create-pipeline/SKILL.md) | Generate v0 Pipeline YAML (CI, CD, approvals, matrix strategies) |
| [`/create-pipeline-v1`](skills/create-pipeline-v1/SKILL.md) | Generate v1 simplified Pipeline YAML -- **Alpha: internal testing only** |
| [`/create-template`](skills/create-template/SKILL.md) | Create reusable Step, Stage, Pipeline, or StepGroup templates |
| [`/create-trigger`](skills/create-trigger/SKILL.md) | Create webhook, scheduled, and artifact triggers |
| [`/create-agent-template`](skills/create-agent-template/SKILL.md) | Create AI-powered agent templates -- **Alpha: internal testing only** |

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
│   └── ...                  # 26 skills total
├── scripts/
│   └── validate-skills.sh   # Frontmatter validation
├── examples/
│   ├── v0/                  # v0 pipeline examples
│   ├── v1/                  # v1 pipeline examples
│   ├── templates/           # Template examples
│   ├── triggers/            # Trigger examples
│   ├── services/            # Service definition examples
│   ├── environments/        # Environment examples
│   ├── connectors/          # Connector examples
│   └── ...
├── .cursor/rules/harness.mdc  # Auto-loaded by Cursor
├── .github/copilot-instructions.md  # Auto-loaded by GitHub Copilot
├── AGENTS.md                # Auto-loaded by OpenAI Codex
├── CLAUDE.md                # Auto-loaded by Claude Code
├── CONTRIBUTING.md          # Contribution guidelines
├── LICENSE                  # Apache 2.0
└── README.md
```

## Skill Anatomy

Each skill is a directory under `skills/` containing a `SKILL.md` with YAML frontmatter and markdown instructions:

```yaml
---
name: my-skill
description: >-
  What the skill does, when to use it, and trigger phrases.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# My Skill

Instructions for Claude to follow when this skill is invoked.
```

Skills can include a `references/` directory for supplementary material (report templates, role tables, extended examples) that Claude loads on demand.

## MCP Tools

MCP-powered skills use the [Harness MCP v2 server](https://github.com/thisrohangupta/harness-mcp-v2), which provides 10 generic tools dispatched by `resource_type`:

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
- [Harness MCP v2 Server](https://github.com/thisrohangupta/harness-mcp-v2)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on adding or modifying skills.

## License

This project is licensed under the [Apache License 2.0](LICENSE).

Copyright 2026 Harness Inc.
