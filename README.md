# Harness Skills

Claude Code skills for the [Harness.io](https://harness.io) CI/CD platform. Generate pipeline YAML, manage resources, debug failures, analyze costs, and more -- all from natural language.

## Prerequisites

- [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)
- [Harness MCP v2 Server](https://github.com/thisrohangupta/harness-mcp-v2) -- required for MCP-powered skills. Most skills in this repo depend on this server for Harness API access.

## Installation

```bash
git clone https://github.com/harness/harness-skills.git
cd harness-skills
```

Skills are automatically available when Claude Code runs in this directory.

## Skills

### Pipeline & Template Creation

| Skill | Description |
|-------|-------------|
| [`/create-pipeline`](skills/create-pipeline/SKILL.md) | Generate v0 Pipeline YAML (CI, CD, approvals, matrix strategies) |
| [`/create-pipeline-v1`](skills/create-pipeline-v1/SKILL.md) | Generate v1 simplified Pipeline YAML |
| [`/create-template`](skills/create-template/SKILL.md) | Create reusable Step, Stage, Pipeline, or StepGroup templates |
| [`/create-trigger`](skills/create-trigger/SKILL.md) | Create webhook, scheduled, and artifact triggers |
| [`/create-agent-template`](skills/create-agent-template/SKILL.md) | Create AI-powered agent templates |

### Resource Management

| Skill | Description |
|-------|-------------|
| [`/create-service`](skills/create-service/SKILL.md) | Create service definitions (K8s, Helm, ECS, Lambda) |
| [`/create-environment`](skills/create-environment/SKILL.md) | Create environment definitions with overrides |
| [`/create-infrastructure`](skills/create-infrastructure/SKILL.md) | Create infrastructure definitions |
| [`/create-connector`](skills/create-connector/SKILL.md) | Create connectors (Git, cloud, registries, clusters) |
| [`/create-secret`](skills/create-secret/SKILL.md) | Create secrets (text, file, SSH, WinRM) |
| [`/create-input-set`](skills/create-input-set/SKILL.md) | Create reusable input sets and overlays |
| [`/create-freeze`](skills/create-freeze/SKILL.md) | Create deployment freeze windows |
| [`/manage-roles`](skills/manage-roles/SKILL.md) | Manage role assignments and RBAC |
| [`/webhook-manager`](skills/webhook-manager/SKILL.md) | Manage GitX webhooks |

### Operations & Debugging (MCP)

| Skill | Description |
|-------|-------------|
| [`/run-pipeline`](skills/run-pipeline/SKILL.md) | Execute pipelines, monitor progress, handle approvals |
| [`/debug-pipeline`](skills/debug-pipeline/SKILL.md) | Analyze execution failures, diagnose root causes |
| [`/migrate-pipeline`](skills/migrate-pipeline/SKILL.md) | Convert pipelines from v0 to v1 format |
| [`/template-usage`](skills/template-usage/SKILL.md) | Track template dependencies and adoption |

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

## Usage

Invoke any skill by name in Claude Code:

```
/create-pipeline
Create a CI pipeline for a Node.js app that builds, runs tests,
and pushes a Docker image to ECR
```

```
/debug-pipeline
Why did my deploy-to-prod pipeline fail last night?
```

```
/security-report
Show me all critical vulnerabilities in the payments project
```

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
│   └── ...                  # 23 skills total
├── examples/
│   ├── v0/                  # v0 pipeline examples
│   ├── v1/                  # v1 pipeline examples
│   ├── templates/           # Template examples
│   ├── triggers/            # Trigger examples
│   ├── services/            # Service definition examples
│   ├── environments/        # Environment examples
│   ├── connectors/          # Connector examples
│   └── ...
├── CLAUDE.md                # Project instructions for Claude Code
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
