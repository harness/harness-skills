---
name: chaos-dr-test
description: >-
  Use when working with Chaos Engineering steps inside a Harness pipeline. Covers
  ChaosFault, ChaosProbe, ChaosAction steps (DRTest stages), the Chaos step (CD
  stages), and DRTest stage/pipeline structure. Use when the user asks to add,
  modify, or create chaos steps, fault injection, probes, or disaster recovery
  test pipelines. Do not use for standalone Chaos Experiment create or edit;
  use chaos-experiment for those. Trigger phrases: DR test, DRTest pipeline,
  disaster recovery test, chaos step, ChaosFault step, ChaosProbe step,
  ChaosAction step.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  module: CHAOS
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Chaos DR Test

Create and edit Harness DR Test pipelines — pipelines with a `DRTest` stage
containing `ChaosFault`, `ChaosProbe`, `ChaosAction`, and `Chaos` steps — via MCP.

MANDATORY — Tool Result Verification:
- NEVER claim a tool call succeeded without an explicit success response from the tool.
- NEVER fabricate, assume, or pre-empt tool results. If you called a tool and did not receive a confirmed result, say so and retry.
- When a tool returns a review/elicitation prompt (e.g., "Waiting for user to review before update..."), the user's approval does NOT mean the operation completed. You MUST wait for the follow-up tool response confirming execution before reporting success.
- If the tool response is ambiguous or missing, tell the user honestly and offer to retry.

## Scope Rules

Follow [`references/scope-establishment.md`](../../references/scope-establishment.md) for establishing org/project scope before calling `harness_list`, `harness_get`, `harness_create`, `harness_update`, or `harness_execute` in this skill:

- Parse `org` / `project` from the user's message or a pasted Harness UI URL first.
- Ask only for what is missing — do not re-ask for values already known.
- Restate the active scope before the first mutating call.
- Never invent a default org/project. If either is missing, ask the user to select it before calling a project-scoped resource; do not fall back to account scope silently.

## Instructions

### YAML Output Conventions

**Output style** — always emit block-style YAML for pipeline manifests (each key on its own line, list items on their own line with `-`, children indented). The YAML examples shown in `references/components.md` (Series + Parallel Steps, Full DRTest Pipeline, Chaos step) appear as minified JSON purely for token efficiency — JSON parses identically to YAML, so the examples remain authoritative for field names and structure, but the pipeline YAML you produce MUST be block-style matching the canonical scaffold below. Never put JSON in the request body for `harness_create` or `harness_update` pipeline YAML.

### DR Test Pipeline Rules

#### Identifying a DR Test Pipeline

Two ways to verify a pipeline is a DR Test:

1. **Check pipeline tags** — DR Test pipelines have `module: drtest` in their top-level `tags`. Additionally, stages within the pipeline have `type: DRTest`.
2. **List via MCP** — Call `harness_list(resource_type="chaos_dr_test", org_id="<org_id>", project_id="<project_id>")` to get all DR Test pipelines in the project. If the pipeline appears in this list, it is a DR Test. Pass `org_id`/`project_id` using the active scope (see Scope Rules above).

#### DRTest Stage and Steps

Chaos-related steps (`ChaosFault`, `ChaosProbe`, `ChaosAction`, `Chaos`) can ONLY be added to a stage with `type: DRTest`. They are not valid in any other stage type.

#### DRTest Pipeline — Created via MCP with Empty Steps

When a user creates a DR Test via `harness_create(resource_type="chaos_dr_test", org_id="<org_id>", project_id="<project_id>", body={"name": "...", "identifier": "..."})`, the pipeline is generated with `steps: []`. The create response returns metadata only — fetch the full YAML with `harness_get(resource_type="pipeline", resource_id="<identifier>_pipeline", org_id="<org_id>", project_id="<project_id>")` (pass `org_id`/`project_id` using the active scope on both calls):

```yaml
pipeline:
  description: ""                          # optional, user can update later
  identifier: test_new_dr_test_pipeline    # auto: <identifier>_pipeline, does NOT change
  name: test new dr test pipeline          # auto: <name> Pipeline, user can update
  orgIdentifier: default                   # from account context, does NOT change
  projectIdentifier: ChaosDev1             # from account context, does NOT change
  stages:
    - stage:
        description: Optional Description  # optional, user can set at create or update later
        identifier: test_new_dr_test       # auto-derived from name, does NOT change
        name: test new dr test             # user-provided name, user can update
        objective: Optional Objective      # optional, user can set at create or update later
        spec:
          execution:
            steps: []                      # EMPTY — agent must populate with chaos steps
        tags:
          someTag: value                   # optional, user can add at create or update later
        type: DRTest                       # fixed, set at stage creation — do NOT remove
  tags:
    module: drtest                         # fixed, auto-set by MCP — do NOT remove
```

**Note:** The example above shows the minimal structure. A real pipeline may contain additional fields (e.g., `allowStageExecutions`, `notificationRules`, `flowControl`, `timeout`, etc.) — preserve any extra fields present in the fetched YAML as-is. Do not remove or overwrite them.

The stage-level `environment` block is NOT used by DRTest pipelines. It may appear in fetched YAML but is ignored by the backend:

    environment: environmentRef: demo deployToAll: false infrastructureDefinitions:
        - identifier: qaauto1

Do not ask the user to provide stage-level environment or infrastructure — each chaos step has its own `infraReference` field instead (see `references/components.md` Step 1). If this block already exists in fetched YAML, preserve it as-is — do not remove it.

The agent's job is to populate `steps: []` with chaos steps (`ChaosFault`, `ChaosProbe`, `ChaosAction`, `Chaos`) using the workflow described in `references/components.md`. Only these chaos step types are valid inside a `DRTest` stage.

**Naming convention:** if user creates a DR Test with name `test new dr test` (identifier auto-derived as `test_new_dr_test`):
- Pipeline identifier = `test_new_dr_test_pipeline` (auto: `<identifier>_pipeline`)
- Pipeline name = `test new dr test pipeline` (auto: `<name> Pipeline`)
- Stage identifier = `test_new_dr_test` (auto-derived from name)
- Stage name = `test new dr test` (= the name provided by the user)

Optional stage fields: `description`, `objective`, `tags`, `runMode`, `variables`, `delegateSelectors`, `failureStrategies`, `when`, `timeout`.

### Intent Routing

#### Step 0: Detect intent — Create or Edit

Parse the user's ORIGINAL message (the one that triggered this skill) to determine their intent. Do NOT ask them "create or edit?" again — their original message already tells you.

**Intent signals:**

| Intent | Keywords in the user's original message |
|---|---|
| **Create** | create, build, set up, set-up, new, make, add (a new DR Test / new step), launch |
| **Edit** | edit, update, modify, change, fix, adjust, rename, tweak, remove, delete, add to an existing |
| **Ambiguous** | "DR Test" or "chaos step" alone with no verb |

**Routing:**

- **Create intent detected** -> read `references/create.md` — creates a brand-new DR Test pipeline, then proceeds to the Choose Action hub.
- **Edit intent detected** -> read `references/edit.md` — looks up an existing pipeline by name/identifier, confirms, then proceeds to the Choose Action hub.
- **Ambiguous** -> ask the user:
  > Would you like to **create** a new DR Test (or add new chaos steps) or **edit** an existing DR Test pipeline?

Once the path is determined, do NOT ask again.

Step-building mechanics (naming, environment/infra selection, fault/probe/action/experiment selection, runtime variables, saving) live in `references/components.md` and are shared by both the create and edit flows.

For standalone Chaos Experiment YAML (not a pipeline step), stop and use `chaos-experiment` instead.

## Examples

- "Create a new DR Test pipeline called payment-db-failover with a pod-delete fault" -> route to `references/create.md`
- "Add a probe step to my existing `test_new_dr_test` DR Test" -> route to `references/edit.md`
- "Remove the ChaosAction_1 step from the DR test pipeline" -> route to `references/edit.md`
- "What steps can go inside a DRTest stage?" -> answered directly from this file (`DRTest Stage and Steps`)

## Performance Notes

- Step 1 (environment/infrastructure selection) MUST be re-run for every new `ChaosProbe` / `ChaosFault` / `ChaosAction` step, even when adding steps in parallel — never reuse a prior step's `infraReference`.
- Do not guess probe/fault/action identities or infrastructure IDs. Always call the matching `harness_list` and use the returned values.
- The pipeline update call (`harness_update`) is a full-replace PUT — always fetch the current YAML first and apply only the requested changes, preserving every existing field.
- Wait for the tool's confirmed response before reporting success; a review/elicitation prompt is not a completed save.

## Troubleshooting

- **Pipeline update erased existing steps/fields** — the update endpoint is a full-replace PUT; always `harness_get` the current YAML immediately before modifying and re-sending it, per `references/components.md` Step 4.
- **Chaos step rejected outside a DRTest stage** — `ChaosFault` / `ChaosProbe` / `ChaosAction` / `Chaos` steps are only valid inside a stage with `type: DRTest`; verify the target stage type before adding steps.
- **Duplicate step name/identifier error** — every step `name` and `identifier` must be unique within the stage; check existing steps before naming a new one.
- **Ambiguous create vs. edit intent** — if Step 0's keyword signals do not clearly resolve, ask explicitly per Step 0 rather than guessing; creating a duplicate pipeline is harder to undo than asking one clarifying question.
