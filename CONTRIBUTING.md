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

Step-by-step instructions for Claude to follow.

## Examples

Real invocation examples showing how users trigger this skill.

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

### Description Guidelines

- Start with what the skill does (verb phrase)
- Include when to use it and when NOT to use it
- Add trigger phrases that users might say
- Stay under 1024 characters
- Do not use XML-style angle brackets (`<`, `>`) in the description field

### Reference Files

Use `references/` for supplementary material that Claude loads on demand:

- Report templates
- Built-in role/resource tables
- Extended examples
- Schema details

Keep the main `SKILL.md` body focused on core instructions. Move large tables, lengthy examples, and reference data into `references/`.

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

4. Add the skill to `CLAUDE.md` so it appears in the project's skill index.

5. Add the skill to `README.md` under the appropriate category.

## Modifying an Existing Skill

- Bump the `version` in metadata when making changes
- Preserve existing trigger phrases while adding new ones
- Do not remove negative triggers (e.g., "Do NOT use for X")
- Test that the skill still triggers on its intended queries

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

## Pull Request Process

1. Ensure your skill follows the structure and guidelines above
2. Verify the SKILL.md frontmatter is valid YAML
3. Update `CLAUDE.md` and `README.md` if adding a new skill
4. Write a clear PR description explaining what the skill does
5. Reference any related issues

## Reporting Issues

- Use [GitHub Issues](https://github.com/harness/harness-skills/issues) to report bugs or request new skills
- Include the skill name and the query that triggered unexpected behavior
- For MCP-related issues, also check [harness-mcp-v2](https://github.com/thisrohangupta/harness-mcp-v2/issues)

## License

By contributing to this project, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
