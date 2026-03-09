---
name: migrate-pipeline
description: >-
  Migrate Harness pipelines from v0 to v1 simplified format via MCP tools. Converts expressions from
  angle-bracket to ${{ }} syntax, lowercases type names, simplifies structure, and preserves variables,
  failure strategies, and conditional logic. Use when asked to migrate a pipeline, convert v0 to v1,
  upgrade pipeline format, modernize pipeline syntax, or compare v0 vs v1. Trigger phrases: migrate
  pipeline, convert to v1, upgrade pipeline, v0 to v1, modernize pipeline, simplified format.
metadata:
  author: Harness
  version: 2.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Migrate Pipeline

Convert Harness pipelines from v0 to v1 simplified format via MCP.

## Instructions

### Step 1: Fetch Current v0 Pipeline

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
```

### Step 2: Convert v0 to v1

Apply these transformations:

### Expression Mapping

| v0 Expression | v1 Expression |
|--------------|---------------|
| `<+pipeline.variables.x>` | `${{ pipeline.variables.x }}` |
| `<+stage.variables.x>` | `${{ stage.variables.x }}` |
| `<+steps.id.output.outputVariables.x>` | `${{ steps.id.output.x }}` |
| `<+trigger.branch>` | `${{ trigger.branch }}` |
| `<+secrets.getValue("x")>` | `${{ secrets.x }}` |
| `<+pipeline.sequenceId>` | `${{ pipeline.sequenceId }}` |
| `<+input>` | `${{ input }}` |

### Structure Changes

**v0 CI Stage:**
```yaml
stages:
  - stage:
      identifier: build
      type: CI
      spec:
        cloneCodebase: true
        platform:
          os: Linux
          arch: Amd64
        runtime:
          type: Cloud
          spec: {}
        execution:
          steps:
            - step:
                identifier: run
                type: Run
                spec:
                  shell: Bash
                  command: npm test
```

**v1 Equivalent:**
```yaml
stages:
  - name: build
    type: ci
    spec:
      steps:
        - name: run
          type: run
          spec:
            shell: bash
            run: npm test
```

**Key v1 differences:**
- Stage/step types are lowercase: `ci`, `run`, `deployment`
- `command` becomes `run` in Run steps
- `execution.steps` simplifies to `spec.steps`
- Platform/runtime is simplified or implicit
- `identifier` becomes `name` (or `id`)

### Step 3: Show Converted Pipeline

Present both v0 and v1 side-by-side for review.

### Step 4: Update in Harness (Optional)

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: <v1 pipeline YAML>
```

## Migration Checklist

- [ ] Expressions converted from `<+...>` to `${{ ... }}`
- [ ] Stage types lowercased
- [ ] Step types mapped correctly
- [ ] Platform/runtime configuration simplified
- [ ] Variables and inputs preserved
- [ ] Failure strategies maintained
- [ ] Notification rules preserved
- [ ] Conditional execution logic preserved

## Examples

- "Migrate the build-and-deploy pipeline to v1" - Fetch, convert, show diff
- "Show me what ci-pipeline would look like in v1" - Fetch, convert, display only
- "Convert all pipelines in the project" - List all, convert each

## Performance Notes

- Read the complete v0 pipeline before starting migration. Missing stages or steps will produce an incomplete v1 pipeline.
- Verify all expressions are converted from `<+...>` to `${{ }}` format.
- Compare the v0 and v1 outputs to confirm no functionality was lost in translation.

## Troubleshooting

### Unsupported v0 Features
- Some v0-specific step types may not have v1 equivalents yet
- Complex failure strategies may need manual adjustment
- Custom stage types require careful mapping

### Validation Errors After Migration
- Re-validate expression syntax
- Check all resource references still resolve
- Verify variable types are compatible
