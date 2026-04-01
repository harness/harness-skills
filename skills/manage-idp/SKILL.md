---
name: manage-idp
description: >-
  Manage Harness Internal Developer Portal (IDP) resources via MCP. Create service catalog templates,
  configure self-service environment provisioning workflows, generate service documentation, create
  Architecture Decision Records (ADRs), and design developer onboarding workflows. Use when asked
  to set up a service catalog, create self-service workflows, generate service docs, write ADRs, or
  onboard new developers. Do NOT use for service scorecards (use scorecard-review instead). Trigger
  phrases: service catalog, self-service, developer portal, IDP, onboarding workflow, ADR,
  architecture decision, service documentation, catalog template, developer experience, backstage.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Manage IDP

Create service catalog templates, self-service workflows, documentation, ADRs, and developer onboarding flows in Harness Internal Developer Portal.

## Instructions

### Step 1: Establish Scope

Confirm the user's org and project context.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "project"
  org_id: "<organization>"
```

### Step 2: Identify the IDP Task

Determine which IDP workflow the user needs:

1. **Service Catalog Template** -- Standardized microservice template with scaffolding, CI/CD, and observability
2. **Self-Service Environment Provisioning** -- On-demand environment creation with IaC and RBAC controls
3. **Service Documentation** -- Generate catalog-info.yaml, API docs, and architecture overviews
4. **Architecture Decision Record (ADR)** -- Structured decision documentation
5. **Developer Onboarding** -- Automated Day 1 onboarding workflow

### Step 3: Create Service Catalog Template

Gather from the user:
- Technology stack (Node.js, Java, Python, Go, etc.)
- Service pattern (REST API, gRPC, event-driven, etc.)
- Container registry for Docker images
- Observability stack (Datadog, Prometheus, etc.)

Template components to generate:
1. Application scaffolding with standard dependencies
2. CI pipeline: build, test, security scan, Docker build and push
3. CD pipeline: deploy to dev, staging, production with approvals
4. Observability: health endpoints, metrics, structured logging, dashboards
5. catalog-info.yaml with ownership metadata and SLO links

```
Call MCP tool: harness_create
Parameters:
  resource_type: "template"
  org_id: "<organization>"
  project_id: "<project>"
  body:
    name: "<stack>-microservice-template"
    identifier: "<stack>_microservice_template"
    versionLabel: "1.0.0"
    type: "Pipeline"
    yaml: |
      template:
        name: <stack>-microservice-template
        identifier: <stack>_microservice_template
        versionLabel: "1.0.0"
        type: Pipeline
        spec:
          stages:
            - stage:
                name: Build
                type: CI
                spec:
                  # Build, test, scan, push
            - stage:
                name: Deploy Dev
                type: Deployment
                spec:
                  # Deploy to dev environment
```

### Step 4: Create Self-Service Environment Provisioning

Gather from the user:
- Environment type (dev, staging, QA, ephemeral)
- Cloud provider and IaC tool (Terraform, Pulumi, CloudFormation)
- Max concurrent environments per developer
- TTL for ephemeral environments

Design the workflow with:
- Pre-approved infrastructure modules
- Database provisioning with test data seeding
- Secret injection from Harness Secrets or Vault
- RBAC: developer can create/destroy own environments
- Cost controls: TTL-based auto-cleanup, budget caps

### Step 5: Generate Service Documentation

When asked to create documentation, gather:
- Service name, team, type (backend, frontend, data pipeline)
- Tech stack, repo URL, environments
- API endpoints and dependencies

Generate:
1. **catalog-info.yaml** -- Backstage-compatible service registration
2. **API documentation** -- Endpoint inventory with request/response schemas
3. **Architecture overview** -- Component diagram, data flow, dependencies
4. **Operational guide** -- Deployment, monitoring, incident response links

### Step 6: Create Architecture Decision Record (ADR)

Gather from the user:
- Decision title and context
- Options considered with pros/cons
- Decision made and rationale
- Consequences and follow-up actions

Format as standard ADR:
- Status (Proposed, Accepted, Deprecated, Superseded)
- Context, Decision, Consequences sections
- Link to related ADRs if applicable

### Step 7: Design Developer Onboarding Workflow

Gather from the user:
- New engineer's role, team, and tech stack
- Required access (repos, environments, tools)
- Mentorship and buddy program details

Design a self-service onboarding workflow with:
- Access provisioning (GitHub org, Harness project, cloud accounts)
- CDE setup with pre-configured workspace
- First task assignment with guided walkthrough
- Week 1 and Week 2 milestone checklists

## Examples

- "Create a microservice template for our Node.js services" -- Generate service catalog template with CI/CD, observability, and catalog-info.yaml
- "Set up self-service environments for developers" -- Create IDP workflow for on-demand environment provisioning
- "Generate documentation for the checkout-service" -- Create catalog-info.yaml, API docs, and architecture overview
- "Write an ADR for our migration from REST to gRPC" -- Create structured ADR with context, decision, and consequences
- "Design an onboarding workflow for new backend engineers" -- Create Day 1 self-service workflow with access, CDE, and milestones

## Performance Notes

- Service catalog templates should be tested end-to-end before publishing -- a broken template degrades developer trust.
- Self-service environments need cost guardrails (TTL, budget caps) to prevent cloud spend overruns.
- catalog-info.yaml must conform to Backstage entity schema -- validate before registering.
- ADRs should reference the IDP portal URL so they are discoverable alongside the service catalog.
- Onboarding workflows should be idempotent -- re-running should not create duplicate resources.

## Troubleshooting

### Template Not Appearing in Catalog
- Verify the template YAML is valid and the identifier matches the directory name
- Check that the template is published (not draft) and the version label is set
- Confirm the user has read access to the org/project where the template lives

### Self-Service Workflow Failing
- Check IaC module permissions -- the service account needs create/destroy access in the target cloud
- Verify secret references are resolvable in the target project scope
- Check TTL cleanup jobs are not conflicting with active environments

### Documentation Out of Date
- Regenerate catalog-info.yaml when ownership or dependencies change
- Link API docs to the CI pipeline so they auto-update on merge
