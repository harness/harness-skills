---
name: create-input-set
description: >-
  Generate Harness Input Set YAML and create input sets via MCP v2 tools. Input sets provide
  pre-configured runtime values for pipeline execution, supporting environment-specific configs,
  artifact versions, and overlay combinations. Use when asked to create an input set, configure
  runtime inputs, set up environment-specific pipeline values, create overlay input sets, or
  manage pipeline execution parameters. Trigger phrases: create input set, input set, runtime
  inputs, pipeline inputs, overlay input set, execution parameters, environment config.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create Input Set Skill

Generate Harness Input Set YAML and manage input sets via MCP v2 tools.

## MCP v2 Tools Used

| Tool | Resource Type | Purpose |
|------|--------------|---------|
| `harness_list` | `input_set` | List input sets for a pipeline |
| `harness_get` | `input_set` | Get input set details and YAML |
| `harness_create` | `input_set` | Create a new input set |
| `harness_describe` | `input_set` | Discover input set schema |
| `harness_list` | `pipeline` | List pipelines to find target pipeline |
| `harness_get` | `pipeline` | Get pipeline details to see runtime inputs |

## Input Set Types

| Type | Purpose |
|------|---------|
| `InputSet` | Standalone set of runtime input values for a pipeline |
| `OverlayInputSet` | Combines multiple input sets in a defined order |

## YAML Structure

### Basic Input Set

```yaml
inputSet:
  identifier: dev_inputs
  name: Development Inputs
  description: Input values for development deployments
  orgIdentifier: <org_id>
  projectIdentifier: <project_id>
  tags:
    environment: development
  pipeline:
    identifier: <pipeline_identifier>
    variables:
      - name: environment
        type: String
        value: dev
      - name: replicas
        type: Number
        value: 1
```

Identifier must match pattern: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`

For CD, CI, and overlay input set examples and the layered input set strategy, consult references/input-set-examples.md.

## Instructions

### Step 1: Identify the Target Pipeline

```
harness_list(
  resource_type="pipeline",
  org_id="<org>",
  project_id="<project>",
  search_term="<pipeline_name>"
)
```

### Step 2: Get Pipeline Runtime Inputs

```
harness_get(
  resource_type="pipeline",
  resource_id="<pipeline_id>",
  org_id="<org>",
  project_id="<project>"
)
```

Review the pipeline YAML to identify all runtime inputs (fields marked as `<+input>` or runtime variables).

### Step 3: List Existing Input Sets

```
harness_list(
  resource_type="input_set",
  org_id="<org>",
  project_id="<project>"
)
```

### Step 4: Generate Input Set YAML

Create the YAML matching the pipeline's runtime input structure. Every stage identifier, variable name, and type must match the pipeline exactly.

### Step 5: Create via MCP

```
harness_create(
  resource_type="input_set",
  org_id="<org>",
  project_id="<project>",
  body={
    "input_set_yaml": "<yaml_string>"
  }
)
```

## Naming Conventions

| Category | Pattern | Example |
|----------|---------|---------|
| Environment | `{env}_inputs` | `prod_inputs` |
| Release | `release_{version}` | `release_v2_0_0` |
| Feature | `feature_{name}` | `feature_canary` |
| Branch | `ci_{branch}` | `ci_main_branch` |
| Overlay | `{env}_{feature}` | `staging_canary` |

## Examples

### Create a staging input set

```
/create-input-set
Create an input set for the deploy-pipeline that targets the staging environment
with 2 replicas and the k8s-staging infrastructure
```

### Create environment-specific overlay

```
/create-input-set
Create overlay input sets for dev, staging, and prod environments for my deploy-pipeline.
Base config should set log_level=info and monitoring=true.
```

### Create a release input set

```
/create-input-set
Create an input set for v3.0.0 release of the api-service through deploy-pipeline
```

### List existing input sets

```
/create-input-set
Show me all input sets for the build-and-deploy pipeline
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Pipeline not found | Wrong pipeline identifier | Verify pipeline exists with `harness_list(resource_type="pipeline")` |
| Invalid input set YAML | Structure does not match pipeline | Align stage identifiers, variable names, and types with the pipeline |
| Duplicate identifier | Input set with same ID exists | Use a unique identifier or update the existing input set |
| Missing required inputs | Pipeline has required inputs not provided | Get pipeline details and ensure all `<+input>` fields are covered |

## Troubleshooting

### Input Set Not Applying During Execution

1. Verify the input set's `pipeline.identifier` matches the target pipeline exactly
2. Check that stage identifiers in the input set match the pipeline's stage identifiers
3. Confirm variable names and types match (case-sensitive)

### Overlay Input Set Conflicts

1. Later references override earlier ones -- check the order of `inputSetReferences`
2. All referenced input sets must belong to the same pipeline
3. Verify all referenced input sets exist (`harness_list` to confirm)

### Input Set Validation Fails

1. Get the pipeline YAML (`harness_get`) and compare structure
2. Only include fields that are runtime inputs -- do not include fixed fields
3. Variable types must match: `String`, `Number`, `Secret`
