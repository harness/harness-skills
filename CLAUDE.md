# Harness Skills

This repository contains Claude Code skills for working with Harness.io CI/CD platform. All skills use the Harness MCP v2 server's consolidated tool interface.

## MCP v2 Server

All skills use the [Harness MCP v2](https://github.com/thisrohangupta/harness-mcp-v2) server which provides 10 generic tools operating across 119+ resource types:

| Tool | Purpose |
|------|---------|
| `harness_list` | List resources with filters and pagination |
| `harness_get` | Get a single resource by ID |
| `harness_create` | Create a resource (requires confirmation) |
| `harness_update` | Update a resource (requires confirmation) |
| `harness_delete` | Delete a resource (requires confirmation) |
| `harness_execute` | Run, retry, sync, toggle, approve, reject, test_connection |
| `harness_search` | Cross-resource keyword search |
| `harness_describe` | Local metadata/schema lookup (no API call) |
| `harness_diagnose` | Pipeline failure analysis |
| `harness_status` | Project health overview |

Tools accept a `resource_type` parameter (e.g., `pipeline`, `secret`, `template`) to target specific Harness resources. Tools also support Harness UI URL auto-extraction for `org_id`, `project_id`, `resource_type`, and `resource_id`.

## Skill Directory

Skills live in `skills/<skill-name>/SKILL.md`. Each skill folder may contain `references/`, `scripts/`, and `assets/` subdirectories.

### Pipeline & Execution

| Skill | Description |
|-------|-------------|
| `/create-pipeline` | Generate v0 pipeline YAML (CI, CD, combined, approvals) |
| `/create-pipeline-v1` | Generate v1 simplified pipeline YAML |
| `/create-trigger` | Create webhook, scheduled, and artifact triggers |
| `/create-input-set` | Create input sets and overlay input sets for pipelines |
| `/create-template` | Create reusable step, stage, pipeline, and step group templates |
| `/run-pipeline` | Execute and monitor pipeline runs |
| `/debug-pipeline` | Diagnose pipeline execution failures |
| `/migrate-pipeline` | Convert v0 pipelines to v1 format |

### Infrastructure & Resources

| Skill | Description |
|-------|-------------|
| `/create-service` | Define services (Kubernetes, Helm, ECS) with artifact sources |
| `/create-environment` | Create environments (PreProduction, Production) with overrides |
| `/create-infrastructure` | Define infrastructure (K8s, ECS, Serverless) |
| `/create-connector` | Create connectors (GitHub, AWS, GCP, Azure, Docker, K8s) |
| `/create-secret` | Manage secrets (SecretText, SecretFile, SSHKey, WinRM) |

### Observability & Governance

| Skill | Description |
|-------|-------------|
| `/analyze-costs` | Cloud cost analysis, recommendations, and anomaly detection |
| `/security-report` | Security vulnerabilities, SBOMs, and compliance reports |
| `/dora-metrics` | DORA metrics and engineering performance reports |
| `/gitops-status` | GitOps application health, sync status, and pod logs |
| `/chaos-experiment` | Create and run chaos engineering experiments |
| `/scorecard-review` | IDP scorecards and service maturity review |
| `/audit-report` | Audit trails and compliance evidence (SOC2, GDPR, HIPAA) |
| `/manage-roles` | RBAC roles, assignments, permissions, and resource groups |
| `/template-usage` | Template dependency tracking, impact analysis, and adoption |

### Agents

| Skill | Description |
|-------|-------------|
| `/create-agent-template` | Generate AI agent templates (metadata.json, pipeline.yaml, wiki.MD) |

## Schema References

- **v0 Pipelines/Templates/Triggers**: https://github.com/harness/harness-schema/tree/main/v0
- **v1 Pipelines**: https://github.com/thisrohangupta/spec
- **Agent Templates**: https://github.com/thisrohangupta/agents
- **MCP v2 Server**: https://github.com/thisrohangupta/harness-mcp-v2
