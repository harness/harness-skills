---
name: create-environment
description: >-
  Generate Harness Environment YAML for deployment targets and create via MCP. Supports PreProduction and
  Production types with environment variables, manifest overrides, and multi-environment setup (dev,
  staging, prod). Use when asked to create an environment, set up staging, configure production, define
  deployment targets, or manage environment overrides. Trigger phrases: create environment, deployment
  environment, setup dev, setup staging, setup production, environment variables, environment overrides.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Environment

Generate Harness Environment YAML and push to Harness via MCP.

## Instructions

1. **Determine environment type** - `PreProduction` for dev/staging/QA, `Production` for live environments
2. **Define variables and overrides** - Environment-specific config values and manifest overrides
3. **Generate YAML** using the structure below
4. **Create via MCP** using `harness_create` with resource_type `environment`

## Environment Structure

```yaml
environment:
  name: Staging
  identifier: staging
  orgIdentifier: default
  projectIdentifier: my_project
  type: PreProduction       # PreProduction or Production
  tags:
    tier: staging
  variables:
    - name: domain
      type: String
      value: staging.myapp.com
    - name: replicas
      type: String
      value: "2"
  overrides:
    manifests:
      - manifest:
          identifier: values_override
          type: Values
          spec:
            store:
              type: Github
              spec:
                connectorRef: github
                repoName: config
                branch: main
                paths: [values-staging.yaml]
```

## Environment Types

- `PreProduction` - Dev, QA, staging, integration environments
- `Production` - Live production environments (enables additional safeguards)

## Multi-Environment Setup

Create dev, staging, and prod:

```yaml
# Dev
environment:
  name: Development
  identifier: dev
  type: PreProduction
  variables:
    - name: domain
      type: String
      value: dev.myapp.com

# Staging
environment:
  name: Staging
  identifier: staging
  type: PreProduction
  variables:
    - name: domain
      type: String
      value: staging.myapp.com

# Production
environment:
  name: Production
  identifier: prod
  type: Production
  variables:
    - name: domain
      type: String
      value: myapp.com
```

## Creating via MCP

```
Call MCP tool: harness_create
Parameters:
  resource_type: "environment"
  org_id: "<organization>"
  project_id: "<project>"
  body: <environment YAML>
```

List environments:
```
Call MCP tool: harness_list
Parameters:
  resource_type: "environment"
  org_id: "<organization>"
  project_id: "<project>"
```

## Examples

- "Create dev, staging, and prod environments" - Generate 3 environments with appropriate types
- "Set up a production environment with overrides" - Production type with manifest overrides

## Performance Notes

- When creating multiple environments (dev/staging/prod), ensure variable values are distinct per environment.
- Verify that manifest override paths exist in the referenced repository before creating.
- Use Production type only for live environments — it enables additional safeguards like deployment freezes.

## Troubleshooting

- `DUPLICATE_IDENTIFIER` - Environment exists; use `harness_update`
- Production type enables deployment freeze and approval guardrails
