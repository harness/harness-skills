---
name: template-usage
description: >-
  Track Harness template dependencies, usage, and adoption via MCP v2 tools. Find which pipelines
  or other templates reference a given template, analyze update impact, identify unused templates,
  and compare version adoption. Use when asked about template usage, template references, template
  dependencies, impact analysis before updating a template, finding unused templates, or tracking
  template adoption across projects. Trigger phrases: template usage, who uses template, template
  references, template dependencies, template impact, unused templates, template adoption. Do NOT use
  for creating or updating templates (use create-template instead).
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Template Usage Skill

Track template dependencies and usage across Harness via MCP v2 tools.

## MCP v2 Tools Used

| Tool | Resource Type | Purpose |
|------|--------------|---------|
| `harness_search` | `template` | Find templates by keyword across orgs/projects |
| `harness_list` | `template` | List templates, filter by scope |
| `harness_get` | `template` | Get template details, versions, and usage references |
| `harness_describe` | `template` | Discover template resource schema and fields |

Templates are managed via `harness_list` and `harness_get` only. For creating or updating templates, use the `/create-template` skill.

## Template Types

| Type | Description |
|------|-------------|
| `Step` | Single step definition (build, test, deploy actions) |
| `Stage` | Complete stage with steps (CI stage, CD stage, approval) |
| `Pipeline` | Full pipeline definition |
| `StepGroup` | Group of related steps bundled together |

## Template Scopes

| Scope | Visibility | Query Parameters |
|-------|-----------|-----------------|
| Account | All orgs and projects | No org_id, no project_id |
| Organization | All projects in the org | org_id only |
| Project | Only within the project | org_id + project_id |

## Instructions

### Step 1: Find the Template

Search by name or keyword:

```
harness_search(
  query="docker-build-push",
  resource_types=["template"],
  max_per_type=10,
  compact=true
)
```

Or list templates in a specific scope:

```
harness_list(
  resource_type="template",
  org_id="<org>",
  project_id="<project>",
  search_term="docker"
)
```

### Step 2: Get Template Details

```
harness_get(
  resource_type="template",
  resource_id="<template_identifier>",
  org_id="<org>",
  project_id="<project>"
)
```

This returns the template definition, version history, and metadata.

### Step 3: Check Usage References

```
harness_get(
  resource_type="template",
  resource_id="<template_identifier>",
  org_id="<org>",
  project_id="<project>"
)
```

Parse the response for `referredEntities` or usage data. The response includes which pipelines and other templates reference this template.

### Step 4: Analyze and Present

Organize findings into a report.

For report templates (Usage Report, Impact Analysis, Unused Templates), consult references/report-templates.md.

## Examples

### Check who uses a template

```
/template-usage
Which pipelines are using the docker-build-push template?
```

### Impact analysis before update

```
/template-usage
I want to make a breaking change to the k8s-deploy template. Show me what will be affected.
```

### Find unused templates

```
/template-usage
Which templates in our account have no references? I want to clean up.
```

### Track version adoption

```
/template-usage
Which version of the ci-stage template are different projects using?
```

### Cross-project usage

```
/template-usage
Show me all usages of account-level templates across all projects
```

### Dependency chain

```
/template-usage
Show me the full dependency chain for the release-pipeline template --
what does it reference and what references it?
```

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| Template not found | Wrong identifier or scope | Verify identifier and use correct org_id/project_id for the template's scope |
| No usage data | Template genuinely unused or scope mismatch | Search at broader scope; account templates may be used in any project |
| Empty search results | No templates match query | Try broader search terms or list all templates |

## Troubleshooting

### No Usage Data Returned

1. Template may genuinely have no references
2. Query scope must match template scope -- an account-level template needs no org_id/project_id
3. Use `harness_search` with broader terms to find the template first

### Incomplete Usage List

1. Paginate through results -- increment `page` until all results are retrieved
2. Account-level templates can be referenced from any org/project -- check all scopes
3. Check for both pipeline and template references (templates can nest)

### Template Not Found

1. Verify the exact identifier (case-sensitive, underscores not hyphens)
2. Identifiers must match pattern: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
3. Check the correct scope -- project templates require org_id + project_id
