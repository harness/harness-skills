# Contributing to Harness Skills

Thank you for your interest in contributing to Harness Skills! This repository contains model-agnostic skills for the Harness.io CI/CD platform, packaged as plugins for Claude Code, Cursor, and Codex.

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

Each skill lives in its own directory under a category directory and follows this structure:

```
skills/
  categories.json           # Categories and Claude Code plugins (source of truth)
  <category>/
    <skill>/
      SKILL.md              # Skill definition (required)
      references/           # Skill-specific supporting files (optional)
        report-templates.md
        examples.md
      templates/            # Skill-specific output templates (optional)
```

The repo also contains shared assets at the root:

```
references/               # Shared playbooks reused across many skills
templates/                # Shared output contracts reused across many skills
template/                 # Copy-ready SKILL.md skeleton for new skills
```

The repo root must not contain a `.mcp.json`, `hooks/`, `commands/`, `agents/`, or other plugin component files: every plugin's `source` is `.`, so a root-level file like that would ship to and load for all nine plugins (a test enforces this).

### Categories

The nine categories are `pipelines`, `infrastructure`, `access-control`, `fme`, `database`, `platform`, `security`, `observability-governance`, and `agents`. Pick the category for a new skill from `skills/categories.json`; each category is one Claude Code plugin named `harness-<category>`.

To add a category, add one entry to `skills/categories.json` (`dir`, `plugin`, `title`, `description`, `category`, `keywords`). `plugin` must be `harness-<dir>`. This creates a new Claude Code plugin once you run `python3 scripts/generate_catalog.py`.

### SKILL.md Format

Every skill must have a `SKILL.md` file with YAML frontmatter and a markdown body. Copy `template/SKILL.md.template` to `skills/<category>/<skill>/SKILL.md` and fill it in; the template carries the frontmatter, the required sections, and short guidance comments.

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Kebab-case skill name matching the directory name, unique across all categories |
| `description` | Yes | WHAT + "Use when ..." request shapes, under 1024 chars |
| `metadata.author` | Yes | `Harness` for official skills |
| `metadata.version` | Yes | Semantic version (e.g., `1.0.0`) |
| `metadata.mcp-server` | Yes | MCP server dependency (`harness-mcp-v2`) |
| `metadata.summary` | Yes | One line, at most 120 characters, no pipe character; shown in the generated tables and `skills.json` |
| `license` | Yes | `Apache-2.0` |
| `compatibility` | Yes | Runtime requirements |

The only top-level keys allowed are `name`, `description`, `license`, `compatibility`, `metadata`, and `allowed-tools`. Any other key is a validator error.

### Required Body Sections

Every `SKILL.md` must include these top-level sections outside code fences:

- `## Instructions`
- `## Examples`
- `## Performance Notes`
- `## Troubleshooting` or `## Error Handling`

### Description Guidelines

- Start with what the skill does (verb phrase)
- Follow with "Use when ..." naming the request shapes that should route to the skill, especially ones an agent would otherwise attempt without it ("Trigger phrases" is accepted too; the validator errors if neither appears)
- Include when NOT to use it, pointing at the right skill
- Keep workflow steps out of the description; they belong in the body
- Stay under 1024 characters
- Do not use XML-style angle brackets (`<`, `>`) in the description field

### Size

Keep `SKILL.md` under 500 lines; the validator warns past that, and warns on bodies over 5000 words. Move long tables, lengthy examples, and reference data into `references/`.

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

Keep the main `SKILL.md` body focused on core instructions.

### Shared References

- Material used by exactly one skill lives in that skill's own `references/` (or `templates/`).
- Material used by two or more skills lives at the repo root under `references/` (or `templates/`).
- Link a shared file directly from `SKILL.md` with a relative path: `../../../references/<file>.md` from `skills/<category>/<skill>/SKILL.md`. Keep it one level deep: a `SKILL.md` links the shared file it needs; do not rely on a chain of shared files to reach it.
- Do not link into another skill's `references/`, `templates/`, `scripts/`, or `assets/`. If two skills need a file, move it to the root `references/` instead. A handoff link to another skill's `SKILL.md` is allowed as a workflow pointer, but it still breaks under `npx skills add` (which copies only the linking skill's folder). `scripts/check_links.py` warns on both kinds of cross-skill link; the existing reach-ins are known debt, not something to add to.
- Shared files under `references/` and `templates/` must not link into skill folders.
- Every skill under `skills/fme/` links `references/fme/tool-map.md` (validator error otherwise).

Tradeoff: plugin installs (Claude Code, Cursor, Codex) ship the whole repo, so shared links resolve. `npx skills add` copies only the skill folder, so shared links break there until bundling ships.

## Creating a New Skill

1. Pick the category from `skills/categories.json` and create the skill directory from the template:
   ```bash
   mkdir -p skills/<category>/my-new-skill
   cp template/SKILL.md.template skills/<category>/my-new-skill/SKILL.md
   ```

2. Fill in `SKILL.md`, including `metadata.summary`.

3. Add skill-local `references/` or `templates/` if needed, and link shared playbooks from the root `references/` and `templates/` (see Shared References).

4. If the skill introduces reusable behavior, add or update shared playbooks in root `references/` or `templates/`.

5. Run the four checks below and commit the regenerated files. The skill tables in `README.md`, `AGENTS.md`, `.cursor/rules/harness.mdc`, and `.github/copilot-instructions.md` are generated; do not add the skill to them by hand.

To try a change in Claude Code before the PR, add your checkout as a local marketplace (`/plugin marketplace add ./`) and install a plugin from it.

## Modifying an Existing Skill

- Bump the `metadata.version` when making changes
- Preserve existing trigger phrases while adding new ones
- Do not remove negative triggers (e.g., "Do NOT use for X")
- Test that the skill still triggers on its intended queries
- Prefer improving shared references/templates over duplicating the same guidance across many skills
- Re-run the four checks and commit the regenerated files; `metadata.summary` and `metadata.version` feed `skills.json`, and the summary feeds the generated tables

## Rules

- Never add `.claude-plugin/plugin.json`: it conflicts with the marketplace entries in `.claude-plugin/marketplace.json` and would also be read by Cursor and Codex.
- Never hand-edit generated files: `.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`, `.cursor-plugin/plugin.json`, `.agents/plugins/marketplace.json`, `.codex-plugin/plugin.json`, `skills.json`, and the blocks between `<!-- BEGIN GENERATED:skills -->` and `<!-- END GENERATED:skills -->` in `README.md`, `AGENTS.md`, `.cursor/rules/harness.mdc`, and `.github/copilot-instructions.md`. Edit `skills/categories.json` or the SKILL.md frontmatter and regenerate.
- Shared files under `references/` and `templates/` must not link into skill folders.

## Releasing

- **Claude Code**: plugins are versioned by git commit. Users get changes when they run `/plugin marketplace update harness-skills`.
- **Cursor and Codex**: they refresh an installed plugin only when its version changes, and the version is `version` in `skills/categories.json`. Bump it (semver) in the PR that ships user-visible skill changes and note the new version in the PR description.
- Bump each touched skill's `metadata.version` as well (see Modifying an Existing Skill).

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

## Checks

Run these four commands before submitting a PR:

```bash
scripts/validate-skills.sh
python3 scripts/generate_catalog.py
python3 scripts/check_links.py
python3 -m unittest discover -s tests -v
```

| Command | What it checks |
|---------|----------------|
| `scripts/validate-skills.sh` | Layout against `skills/categories.json`, frontmatter (allowed keys, required fields, `metadata.summary`, semver), `name` matches the directory and is unique, description rules (under 1024 chars, no angle brackets, contains "Use when" or "Trigger phrases"), FME skills link `references/fme/tool-map.md`, no README.md inside skill folders. Warns (does not fail) on a missing H1 heading or required section (`## Instructions`, `## Examples`, `## Performance Notes`, `## Troubleshooting`/`## Error Handling`) outside code fences, or a SKILL.md over 500 lines or 5000 words |
| `python3 scripts/generate_catalog.py` | Regenerates the plugin manifests, `skills.json`, and the skill tables. Commit the generated files. Add `--check` to verify without writing |
| `python3 scripts/check_links.py` | Markdown links and backticked path mentions (`references/...`, `templates/...`, `skills/...`, `../...md`), including anchors. A path from one skill into a different skill's folder is a warning |
| `python3 -m unittest discover -s tests -v` | Plugin manifest and link-checker tests |

CI (`.github/workflows/validate-skills.yml`) runs on every pull request and on pushes to `main`:

- **Skill Standards** (Ubuntu and macOS): the four checks above, with `generate_catalog.py --check`, so a PR with stale generated files fails.
- **Plugin Install** (Ubuntu): skills CLI discovery of all skills, a blocking `claude plugin validate`, and a Claude Code install smoke test that checks the shared files are present in the plugin cache.

## Pull Request Process

1. Run the four checks above and fix any errors
2. Commit the regenerated files (CI fails on stale generated files)
3. Update shared `references/` or `templates/` when reusable behavior changes
4. Bump `version` in `skills/categories.json` if the PR ships user-visible changes to Cursor and Codex users, and say so in the description
5. Write a clear PR description explaining what the skill does and which workflow it fits into
6. Reference any related issues

## Reporting Issues

- Use [GitHub Issues](https://github.com/harness/harness-skills/issues) to report bugs or request new skills
- Include the skill name and the query that triggered unexpected behavior
- For MCP-related issues, also check [harness-mcp-v2](https://github.com/thisrohangupta/harness-mcp-v2/issues)

## License

By contributing to this project, you agree that your contributions will be licensed under the [Apache License 2.0](LICENSE).
