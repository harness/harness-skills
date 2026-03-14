# Contributing to Harness Skills

Thank you for your interest in contributing to Harness Skills! This repository contains Claude Code skills for the Harness.io CI/CD platform.

## Getting Started

1. Fork the repository
2. Clone your fork:
   ```bash
   git clone https://github.com/<your-username>/harness-skills.git
   cd harness-skills
   ```
3. Create a feature branch:
   ```bash
   git checkout -b feature/my-new-skill
   ```

## Skill Structure

Each skill lives in its own directory under `skills/` and follows this structure:

```
skills/
  my-skill/
    SKILL.md              # Skill definition (required)
    references/           # Supporting reference files (optional)
      report-templates.md
      examples.md
    templates/            # Skill-specific output templates (optional)
```

The repo also contains shared assets at the root:

```
references/               # Shared playbooks reused across many skills
templates/                # Shared output contracts reused across many skills
```

### SKILL.md Format

Every skill must have a `SKILL.md` file with YAML frontmatter and a markdown body:

```yaml
---
name: my-skill
description: >-
  Clear description of WHAT the skill does, WHEN to use it, and trigger phrases.
  Keep under 1024 characters. Avoid XML angle brackets (< >).
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# My Skill

Brief summary of what this skill does.

## Instructions

Phase-based instructions for Claude to follow.

## Examples

Real invocation examples showing how users trigger this skill.

## Performance Notes

Validation checks, tradeoffs, or speed/accuracy guidance.

## Troubleshooting

Common errors and their solutions.
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Kebab-case skill name matching the directory name |
| `description` | Yes | WHAT + WHEN + trigger phrases, under 1024 chars |
| `metadata.author` | Yes | `Harness` for official skills |
| `metadata.version` | Yes | Semantic version (e.g., `1.0.0`) |
| `metadata.mcp-server` | Yes | MCP server dependency (`harness-mcp-v2`) |
| `license` | Yes | `Apache-2.0` |
| `compatibility` | Yes | Runtime requirements |

### Required Body Sections

Every `SKILL.md` must include these top-level sections outside code fences:

- `## Instructions`
- `## Examples`
- `## Performance Notes`
- `## Troubleshooting` or `## Error Handling`

### Description Guidelines

- Start with what the skill does (verb phrase)
- Include when to use it and when NOT to use it
- Add trigger phrases that users might say
- Stay under 1024 characters
- Do not use XML-style angle brackets (`<`, `>`) in the description field

### Authoring Standards

The best Harness skills behave like workflows, not prose documents. Use these rules when writing or updating a skill:

1. **Use phases, not vibes**  
   Prefer ordered steps such as scope -> dependency verification -> schema discovery -> draft -> validate -> create/update -> summarize.

2. **Be explicit about stop conditions**  
   Call out when Claude must ask the user before proceeding, especially when scope, prerequisites, or destructive actions are unclear.

3. **Lead with a recommendation for meaningful decisions**  
   When the user must choose between options, recommend one path first and explain the tradeoff.

4. **Treat scope as mandatory context**  
   For create/update/delete workflows, establish account/org/project scope before API calls. Reuse the shared playbook in `references/scope-establishment.md`.

5. **Verify dependencies before generating dependents**  
   If a pipeline depends on connectors, secrets, services, environments, or infrastructure, confirm those resources exist first. Reuse `references/dependency-check-playbook.md`.

6. **Use schema discovery and validation loops**  
   Prefer `harness_describe` and API validation feedback over guessed payloads. Reuse `references/schema-validation-loop.md`.

7. **Define the output contract**  
   Complex skills should tell Claude what the final response must contain. Reuse or adapt `templates/operation-summary.md` for consistent summaries.

### Reference Files

Use `references/` for supplementary material that Claude loads on demand:

- Report templates
- Built-in role/resource tables
- Extended examples
- Schema details

Keep the main `SKILL.md` body focused on core instructions. Move large tables, lengthy examples, and reference data into `references/`.

Use root-level `references/` and `templates/` when the material should be shared across many skills. Use skill-local `references/` or `templates/` when the content is specific to one skill's domain.

## Creating a New Skill

1. Create a directory under `skills/`:
   ```bash
   mkdir skills/my-new-skill
   ```

2. Create `SKILL.md` following the format above.

3. Add reference files if needed:
   ```bash
   mkdir skills/my-new-skill/references
   ```

4. Add skill-local templates if needed:
   ```bash
   mkdir skills/my-new-skill/templates
   ```

5. Add the skill to `CLAUDE.md` so it appears in the project's skill index.

6. Add the skill to `README.md` under the appropriate category.

7. If the skill introduces reusable behavior, add or update shared playbooks in root `references/` or `templates/`.

## Modifying an Existing Skill

- Bump the `version` in metadata when making changes
- Preserve existing trigger phrases while adding new ones
- Do not remove negative triggers (e.g., "Do NOT use for X")
- Test that the skill still triggers on its intended queries
- Prefer improving shared references/templates over duplicating the same guidance across many skills

## MCP Tools

Most skills use the Harness MCP v2 server which provides these generic tools:

| Tool | Purpose |
|------|---------|
| `harness_list` | List resources by type |
| `harness_get` | Get resource details |
| `harness_create` | Create a resource |
| `harness_update` | Update a resource |
| `harness_delete` | Delete a resource |
| `harness_execute` | Execute an action |
| `harness_search` | Search across resources |
| `harness_describe` | Get resource schema |
| `harness_diagnose` | Diagnose issues |
| `harness_status` | Check system status |

All tools use a `resource_type` parameter to dispatch to the correct Harness API.

## Code Style

- Use consistent YAML indentation (2 spaces)
- Use kebab-case for skill names and directory names
- Use snake_case for identifiers in YAML examples
- Wrap long description values with `>-` (folded block scalar, strip trailing newline)

## Validation

Run the validation script before submitting a PR:

```bash
./scripts/validate-skills.sh
```

This checks all skills against the [Anthropic Skills Guide](https://docs.anthropic.com) standards and this repo's structural conventions:

- Frontmatter boundaries and required fields (name, description, metadata, license, compatibility)
- Nested metadata fields (`author`, `version`, `mcp-server`)
- Top-level H1 heading
- Skill folder naming (kebab-case, no underscores/spaces/capitals)
- Description quality (under 1024 chars, includes trigger phrases, no XML brackets, valid semver in metadata)
- Required sections (Instructions, Examples, Performance Notes, Troubleshooting/Error Handling)
- Section checks that ignore fenced code blocks so examples do not satisfy the validator accidentally
- Word count (SKILL.md body under 5000 words)
- No README.md inside skill folders

The same checks run automatically via GitHub Actions on every PR to `main`.

## Pull Request Process

1. Run `./scripts/validate-skills.sh` and fix any errors
2. Verify the SKILL.md frontmatter is valid YAML
3. Update `CLAUDE.md` and `README.md` if adding a new skill
4. Update shared `references/` or `templates/` when reusable behavior changes
5. Write a clear PR description explaining what the skill does and which workflow it fits into
6. Reference any related issues

## Reporting Issues

- Use [GitHub Issues](https://github.com/harness/harness-skills/issues) to report bugs or request new skills
- Include the skill name and the query that triggered unexpected behavior
- For MCP-related issues, also check [harness-mcp-v2](https://github.com/thisrohangupta/harness-mcp-v2/issues)

## License

By contributing to this project, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
