# FME scenario evaluation

`fixtures/scenarios.json` contains manual behavioral scenarios, not recorded live API responses. Each names a skill, synthetic inputs, required behavior and forbidden behavior.

## Run a scenario

1. Load `skills/<skill>/SKILL.md` and its linked references in a fresh agent session. Specify the available transport and operation schemas; use a sandbox or mocked tools, never production credentials.
2. Give the agent the scenario's description and inputs. Treat them as known state, adding only the minimum mock responses needed for the workflow. Do not fabricate a successful write or verification to fill a missing capability.
3. Check every required behavior and reject any forbidden behavior. If the agent needs clarification, provide a synthetic answer and continue through the relevant decision point; do not approve real resource mutations.
4. Record scenario ID, skill revision, model/tool versions, transport, observed steps, and pass/fail with the exact deviation. Repeat for CLI and MCP when applicable.

## What CI checks

Run `python3 -m unittest discover -s tests -v` from the repository root. It checks relative links/anchors, the creation entrypoint, selected CLI syntax contracts, blueprint ordering and fixture structure/coverage.

**No model evaluation, live CLI/MCP request, pipeline execution or SDK event ingestion runs in these tests.** Passing fixture validation means the evaluation cases are well formed, not that an agent followed them. The CLI assertions capture a reviewed source snapshot and must be updated when supported operations change.

Use `bash scripts/validate-skills.sh` separately for repository-wide skill standards. Both checks run in the skill-validation workflow.
