# Harness Skills

Model-agnostic AI coding skills for the [Harness.io](https://harness.io) CI/CD platform. Generate pipeline YAML, manage resources, debug failures, analyze costs, and more from natural language.

This repository is designed as a workflow system, not just a folder of prompts. The top-level instructions (`AGENTS.md`, with `CLAUDE.md` importing it for Claude Code, plus `.github/copilot-instructions.md`) establish shared behavior, while individual skills specialize in creation, debugging, governance, and reporting tasks.

## Prerequisites

- [Harness MCP v2 Server](https://github.com/harness/mcp-server) - required for MCP-powered skills. Most skills in this repo depend on it for Harness API access.

## Setup

### FME with CLI or MCP (any coding agent)

1. Keep the repository's `skills/`, shared `references/`, and `templates/` available together. Load `AGENTS.md` and the selected skill; referencing just its SKILL.md without the linked playbooks is insufficient.
2. Choose the transport available to your agent: a preconfigured Harness CLI with shell access, or the [Harness MCP server](https://github.com/harness/mcp-server). Confirm the account, organization, project and intended environments without exposing credentials. CLI-only FME sessions do not require MCP; authentication should use the tool's supported secure setup outside the prompt.
3. Read the [FME tool map](references/fme/tool-map.md#transport-preflight-and-handoffs) and check capabilities for the installed version. It documents unsupported operations; CLI/MCP support is not identical. Segment key operations require MCP; some experiment updates also require MCP.
4. Use the skill file as instructions even if the host has no slash-skill invocation. Load linked skills explicitly during handoffs. Code-editing workflows also need the application repository and its test tools; live verification additionally needs an authorized running application.

The editor-specific MCP examples below apply to MCP-powered sessions, not as a prerequisite for every FME workflow. See the [MCP setup playbook](references/mcp-setup.md) for connection, authentication, and read-only verification guidance.

### Claude Code

Clone the repo and run Claude Code from the project directory. Skills are automatically discovered from `skills/*/SKILL.md`; project rules load via `CLAUDE.md` → `@AGENTS.md`:

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
@harness-skills/skills/pipelines/create-pipeline/SKILL.md
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
Using the instructions in harness-skills/skills/pipelines/debug-pipeline/SKILL.md,
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
#file:harness-skills/skills/pipelines/create-pipeline/SKILL.md
Create a CI pipeline for my Python service
```

5. For GitHub Copilot on GitHub.com, attach skill files as context in Copilot Chat or add them as knowledge base references in your Copilot organization settings.

### Windsurf / Other AI Editors

The skills in this repo are plain Markdown files with YAML frontmatter. They work with any AI coding tool that supports:

1. **System instructions** - Use `AGENTS.md` as project-level context (`CLAUDE.md` imports it for Claude Code).
2. **Resource access** - Connect the [Harness MCP server](https://github.com/harness/mcp-server), or use the Harness CLI for supported FME operations.
3. **File context** - Reference individual `skills/*/SKILL.md` files in prompts.

## Operating Model

The best Harness skills follow the same control flow even when they target different resource types:

1. **Establish scope first** - confirm account/org/project context before listing, creating, updating, or deleting resources.
2. **Verify dependencies before generating dependents** - do not reference connectors, secrets, environments, infrastructure, or templates that have not been confirmed to exist.
3. **Discover schema before writing payloads** - use MCP `harness_describe` or the installed CLI command specification and documented payload schema; stop when required capabilities are unavailable rather than guessing fields.

These repo-level playbooks live in:

- [`references/scope-establishment.md`](references/scope-establishment.md)
- [`references/dependency-check-playbook.md`](references/dependency-check-playbook.md)
- [`references/schema-validation-loop.md`](references/schema-validation-loop.md)
- [`templates/operation-summary.md`](templates/operation-summary.md)

## Workflow Modes

| Workflow mode | Representative skills | Use when |
|---------------|-----------------------|----------|
| Create and scaffold | `/create-pipeline`, `/create-service`, `/create-connector`, `/create-template`, `/fme-pipeline` | You need to define or generate new Harness resources and their YAML or MCP payloads. |
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

<!-- BEGIN GENERATED:skills -->
<!-- Generated by scripts/generate_catalog.py from skills/categories.json and SKILL.md frontmatter. Do not edit. -->

### Harness Pipelines & Execution

Plugin `harness-pipelines` (8 skills), folder `skills/pipelines/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [create-pipeline](skills/pipelines/create-pipeline/SKILL.md) | `/harness-pipelines:create-pipeline` | Generate v0 pipeline YAML (CI, CD, combined, approvals) |
| [create-pipeline-v1](skills/pipelines/create-pipeline-v1/SKILL.md) | `/harness-pipelines:create-pipeline-v1` | Generate v1 simplified pipeline YAML |
| [create-template](skills/pipelines/create-template/SKILL.md) | `/harness-pipelines:create-template` | Create reusable step, stage, pipeline, and step group templates |
| [create-trigger](skills/pipelines/create-trigger/SKILL.md) | `/harness-pipelines:create-trigger` | Create webhook, scheduled, and artifact triggers |
| [debug-pipeline](skills/pipelines/debug-pipeline/SKILL.md) | `/harness-pipelines:debug-pipeline` | Diagnose pipeline execution failures |
| [manage-freeze-windows](skills/pipelines/manage-freeze-windows/SKILL.md) | `/harness-pipelines:manage-freeze-windows` | Create, toggle, and manage deployment freeze windows and the project-level global freeze |
| [migrate-pipeline](skills/pipelines/migrate-pipeline/SKILL.md) | `/harness-pipelines:migrate-pipeline` | Convert v0 pipelines to v1 format |
| [run-pipeline](skills/pipelines/run-pipeline/SKILL.md) | `/harness-pipelines:run-pipeline` | Execute and monitor pipeline runs |

### Harness Infrastructure & Resources

Plugin `harness-infrastructure` (5 skills), folder `skills/infrastructure/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [create-connector](skills/infrastructure/create-connector/SKILL.md) | `/harness-infrastructure:create-connector` | Create connectors (GitHub, AWS, GCP, Azure, Docker, K8s) |
| [create-environment](skills/infrastructure/create-environment/SKILL.md) | `/harness-infrastructure:create-environment` | Create environments (PreProduction, Production) with overrides |
| [create-infrastructure](skills/infrastructure/create-infrastructure/SKILL.md) | `/harness-infrastructure:create-infrastructure` | Define infrastructure (K8s, ECS, Serverless) |
| [create-secret](skills/infrastructure/create-secret/SKILL.md) | `/harness-infrastructure:create-secret` | Manage secrets (SecretText, SecretFile, SSHKey, WinRM) |
| [create-service](skills/infrastructure/create-service/SKILL.md) | `/harness-infrastructure:create-service` | Define services (Kubernetes, Helm, ECS) with artifact sources |

### Harness Access Control & Users

Plugin `harness-access-control` (2 skills), folder `skills/access-control/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [manage-roles](skills/access-control/manage-roles/SKILL.md) | `/harness-access-control:manage-roles` | RBAC roles, assignments, permissions, and resource groups |
| [manage-users](skills/access-control/manage-users/SKILL.md) | `/harness-access-control:manage-users` | Manage users, user groups, and service accounts |

### Harness FME (Feature Flags & Experimentation)

Plugin `harness-fme` (16 skills), folder `skills/fme/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [choose-metric](skills/fme/choose-metric/SKILL.md) | `/harness-fme:choose-metric` | Recommend primary/guardrail metrics for an experiment or rollout, judged against a good-metric checklist |
| [cleanup-feature-flags](skills/fme/cleanup-feature-flags/SKILL.md) | `/harness-fme:cleanup-feature-flags` | Remove a launched FME flag from code and open a PR; archive is handed to manage-flag-lifecycle |
| [create-experiment](skills/fme/create-experiment/SKILL.md) | `/harness-fme:create-experiment` | Creation-only entry point to the manage-experiments workflow |
| [create-feature-flag](skills/fme/create-feature-flag/SKILL.md) | `/harness-fme:create-feature-flag` | Create an FME flag that follows project conventions, with safe-default definitions |
| [create-metric](skills/fme/create-metric/SKILL.md) | `/harness-fme:create-metric` | Design and create an FME metric, with intent-to-config guidance, traffic type, events, cap, and owners |
| [discover-feature-flags](skills/fme/discover-feature-flags/SKILL.md) | `/harness-fme:discover-feature-flags` | Inventory, targeting-pattern search, promotion-aware rollout report, and stale-flag audit (read-only) |
| [explain-flag](skills/fme/explain-flag/SKILL.md) | `/harness-fme:explain-flag` | Explain one flag's purpose, treatments, and per-environment targeting, flagging inconsistencies (read-only) |
| [feature-flag-onboarding](skills/fme/feature-flag-onboarding/SKILL.md) | `/harness-fme:feature-flag-onboarding` | Set up and verify a first feature flag in an existing project; resume partial onboarding |
| [fme-pipeline](skills/fme/fme-pipeline/SKILL.md) | `/harness-fme:fme-pipeline` | Generate FME pipelines for rollout scenarios, gates, and flag lifecycle |
| [instrument-feature-flag](skills/fme/instrument-feature-flag/SKILL.md) | `/harness-fme:instrument-feature-flag` | Gate application code through an extensible flag abstraction, after stack detection and clarification |
| [instrument-metric](skills/fme/instrument-metric/SKILL.md) | `/harness-fme:instrument-metric` | Wire up a track() call for a metric's event, placed at the real outcome, and verify it arrives |
| [manage-experiments](skills/fme/manage-experiments/SKILL.md) | `/harness-fme:manage-experiments` | Feature-flag experiment design/lifecycle; delegates metrics and states CLI update limitations |
| [manage-flag-lifecycle](skills/fme/manage-flag-lifecycle/SKILL.md) | `/harness-fme:manage-flag-lifecycle` | Flag metadata, archive readiness, archive/unarchive, and delete |
| [manage-segments](skills/fme/manage-segments/SKILL.md) | `/harness-fme:manage-segments` | Segment metadata, STANDARD membership, and RULE_BASED editor workflows with mandatory pre-write reference checks |
| [review-experiment-results](skills/fme/review-experiment-results/SKILL.md) | `/harness-fme:review-experiment-results` | Explain experiment results, including winner, significance, guardrail impact, and data-quality caveats |
| [update-flag-targeting](skills/fme/update-flag-targeting/SKILL.md) | `/harness-fme:update-flag-targeting` | Ramp, rules, individual targets, allocation, treatments, kill/restore, env-to-env copy, and initializing definitions |

### Harness Database DevOps

Plugin `harness-database` (1 skill), folder `skills/database/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [dbops-changeset](skills/database/dbops-changeset/SKILL.md) | `/harness-database:dbops-changeset` | Generate, refine, review, and execute Liquibase changesets with Harness DBOPS |

### Harness Platform Operations

Plugin `harness-platform` (8 skills), folder `skills/platform/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [create-sbom](skills/platform/create-sbom/SKILL.md) | `/harness-platform:create-sbom` | Add SBOM Orchestration (generation/attestation) to existing pipelines |
| [enforce-sbom](skills/platform/enforce-sbom/SKILL.md) | `/harness-platform:enforce-sbom` | Add SBOM Policy Enforcement (verify attestation + OPA policy sets) |
| [manage-artifacts](skills/platform/manage-artifacts/SKILL.md) | `/harness-platform:manage-artifacts` | Artifact registry setup, security scanning, and cross-region replication |
| [manage-cde](skills/platform/manage-cde/SKILL.md) | `/harness-platform:manage-cde` | Cloud development environments, workspace templates, and auto-hibernation |
| [manage-delegates](skills/platform/manage-delegates/SKILL.md) | `/harness-platform:manage-delegates` | Monitor delegate health and manage registration tokens |
| [manage-iacm](skills/platform/manage-iacm/SKILL.md) | `/harness-platform:manage-iacm` | Terraform workspaces, drift detection, cost estimation, and approval workflows |
| [manage-pull-requests](skills/platform/manage-pull-requests/SKILL.md) | `/harness-platform:manage-pull-requests` | List, create, update, merge, review, and comment on Harness Code pull requests |
| [manage-supply-chain](skills/platform/manage-supply-chain/SKILL.md) | `/harness-platform:manage-supply-chain` | SBOM generation, artifact signing, and supply chain policy enforcement |

### Harness Security Testing & Supply Chain

Plugin `harness-security` (11 skills), folder `skills/security/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [approve-exempt](skills/security/approve-exempt/SKILL.md) | `/harness-security:approve-exempt` | Approve pending STO exemptions at current scope or elevate to Project, Org, or Account |
| [configure-agent-pr-attestation](skills/security/configure-agent-pr-attestation/SKILL.md) | `/harness-security:configure-agent-pr-attestation` | Install and configure the Claude Code PR attestation hook for signed in-toto attestations to the Harness Evidence Vault |
| [configure-container-scan](skills/security/configure-container-scan/SKILL.md) | `/harness-security:configure-container-scan` | Add container image scanning to pipelines using Harness STO scanners (Trivy, Grype, Snyk, and more) |
| [configure-dast-scan](skills/security/configure-dast-scan/SKILL.md) | `/harness-security:configure-dast-scan` | Add DAST scanning to pipelines for runtime application security testing (Traceable, Burp Suite, ZAP, Nikto, Nmap) |
| [configure-repo-scan](skills/security/configure-repo-scan/SKILL.md) | `/harness-security:configure-repo-scan` | Configure code scanning in pipelines with STO security scanners |
| [configure-secret-scan](skills/security/configure-secret-scan/SKILL.md) | `/harness-security:configure-secret-scan` | Add secret detection scanning to pipelines to find exposed credentials and API keys (Gitleaks, Semgrep, Snyk, and more) |
| [enforce-slsa](skills/security/enforce-slsa/SKILL.md) | `/harness-security:enforce-slsa` | Add SLSA Verification (verify attestation + OPA policy sets on provenance) to pipelines |
| [exempt-vuln](skills/security/exempt-vuln/SKILL.md) | `/harness-security:exempt-vuln` | Create STO vulnerability exemptions (waivers) scoped to Project, Pipeline, or Target |
| [generate-slsa](skills/security/generate-slsa/SKILL.md) | `/harness-security:generate-slsa` | Add SLSA Generation (provenance + optional Cosign attestation) to existing pipelines |
| [sign-artifact](skills/security/sign-artifact/SKILL.md) | `/harness-security:sign-artifact` | Add Artifact Signing (Cosign sign + optional .sig upload) to existing pipelines (SSCA) |
| [verify-sign](skills/security/verify-sign/SKILL.md) | `/harness-security:verify-sign` | Add Artifact Verification (verify Cosign signature) to existing pipelines (SSCA) |

### Harness Observability & Governance

Plugin `harness-observability-governance` (18 skills), folder `skills/observability-governance/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [ai-operations](skills/observability-governance/ai-operations/SKILL.md) | `/harness-observability-governance:ai-operations` | Predictive failure analysis and intelligent alert correlation (AIDA) |
| [analyze-costs](skills/observability-governance/analyze-costs/SKILL.md) | `/harness-observability-governance:analyze-costs` | Cloud cost analysis, recommendations, and anomaly detection |
| [audit-report](skills/observability-governance/audit-report/SKILL.md) | `/harness-observability-governance:audit-report` | Audit trails and compliance evidence (SOC2, GDPR, HIPAA) |
| [chaos-dr-test](skills/observability-governance/chaos-dr-test/SKILL.md) | `/harness-observability-governance:chaos-dr-test` | Create and edit DR Test pipelines with chaos steps |
| [chaos-experiment](skills/observability-governance/chaos-experiment/SKILL.md) | `/harness-observability-governance:chaos-experiment` | Create, edit, and reference chaos experiments (faults, probes, actions) |
| [create-policy](skills/observability-governance/create-policy/SKILL.md) | `/harness-observability-governance:create-policy` | Create OPA governance policies for supply chain security |
| [deployment-readiness](skills/observability-governance/deployment-readiness/SKILL.md) | `/harness-observability-governance:deployment-readiness` | Pre-deployment readiness checks, environment drift, and canary decisions |
| [dora-metrics](skills/observability-governance/dora-metrics/SKILL.md) | `/harness-observability-governance:dora-metrics` | DORA metrics and engineering performance reports |
| [gitops-status](skills/observability-governance/gitops-status/SKILL.md) | `/harness-observability-governance:gitops-status` | GitOps application health, sync status, and pod logs |
| [incident-response](skills/observability-governance/incident-response/SKILL.md) | `/harness-observability-governance:incident-response` | Deployment-incident correlation, blast radius analysis, and postmortems |
| [manage-idp](skills/observability-governance/manage-idp/SKILL.md) | `/harness-observability-governance:manage-idp` | Service catalog, self-service workflows, documentation, and developer onboarding (IDP) |
| [manage-slos](skills/observability-governance/manage-slos/SKILL.md) | `/harness-observability-governance:manage-slos` | SLO definition, error budgets, incident detection, and operational runbooks |
| [optimize-pipeline](skills/observability-governance/optimize-pipeline/SKILL.md) | `/harness-observability-governance:optimize-pipeline` | Pipeline speed optimization, parallel testing, caching, and monorepo builds |
| [pr-analysis](skills/observability-governance/pr-analysis/SKILL.md) | `/harness-observability-governance:pr-analysis` | PR pipeline impact, security review, and PR-to-production tracking |
| [scorecard-review](skills/observability-governance/scorecard-review/SKILL.md) | `/harness-observability-governance:scorecard-review` | IDP scorecards and service maturity review |
| [security-report](skills/observability-governance/security-report/SKILL.md) | `/harness-observability-governance:security-report` | Security vulnerabilities, SBOMs, and compliance reports |
| [sei-analytics](skills/observability-governance/sei-analytics/SKILL.md) | `/harness-observability-governance:sei-analytics` | Sprint analytics, investment allocation, capacity forecasting, and release readiness |
| [template-usage](skills/observability-governance/template-usage/SKILL.md) | `/harness-observability-governance:template-usage` | Template dependency tracking, impact analysis, and adoption |

### Harness AI Agents

Plugin `harness-agents` (2 skills), folder `skills/agents/`.

| Skill | Invoke in Claude Code | Description |
|-------|------------------------|-------------|
| [create-agent](skills/agents/create-agent/SKILL.md) | `/harness-agents:create-agent` | Create and update Harness AI agent instances for agentic pipeline workflows |
| [create-agent-template](skills/agents/create-agent-template/SKILL.md) | `/harness-agents:create-agent-template` | Generate AI agent templates (metadata.json, pipeline.yaml, wiki.MD) |

<!-- END GENERATED:skills -->

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
├── AGENTS.md                    # Canonical project rules (Codex, Cursor, etc.)
├── CLAUDE.md                    # Imports AGENTS.md for Claude Code
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
