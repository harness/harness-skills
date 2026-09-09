# Editing an Existing DR Test Pipeline

MANDATORY — Tool Result Verification:
- NEVER claim a tool call succeeded without an explicit success response from the tool.
- NEVER fabricate, assume, or pre-empt tool results. If you called a tool and did not receive a confirmed result, say so and retry.
- When a tool returns a review/elicitation prompt (e.g., "Waiting for user to review before update..."), the user's approval does NOT mean the operation completed. You MUST wait for the follow-up tool response confirming execution before reporting success.
- If the tool response is ambiguous or missing, tell the user honestly and offer to retry.

## Scope Rules

Follow [`references/scope-establishment.md`](../../../references/scope-establishment.md) for establishing org/project scope before calling `harness_list`, `harness_get`, `harness_create`, `harness_update`, or `harness_execute` in this skill:

- Parse `org` / `project` from the user's message or a pasted Harness UI URL first.
- Ask only for what is missing — do not re-ask for values already known.
- Restate the active scope before the first mutating call.
- Never invent a default org/project. If either is missing, ask the user to select it before calling a project-scoped resource; do not fall back to account scope silently.

## DR Test Pipeline Reminder

A DR Test pipeline has `module: drtest` in its top-level `tags` and one or more stages of `type: DRTest`, each containing chaos steps (`ChaosFault`, `ChaosProbe`, `ChaosAction`, `Chaos`) in `spec.execution.steps`. See `SKILL.md` for the full canonical scaffold.

## Editing an Existing DR Test Pipeline

This file drives editing an existing DR Test pipeline. If the user's intent is to CREATE a brand-new pipeline, stop and follow `references/create.md` instead.

IMPORTANT: The existing pipeline `identifier`, `orgIdentifier`, `projectIdentifier`, stage `identifier`, and every existing step's `identity` / `infraReference` / `tasks` MUST be preserved throughout the flow. Do NOT regenerate these — they are permanent keys. The update endpoint (`harness_update`) is a full-replace PUT — see `references/components.md`'s `Step 4: Save DR Test`.

### Step U1: Determine if user already has a pipeline identifier

The DR Test's stage identity/name and its backing pipeline identifier are DIFFERENT values (pipeline identifier = `<stage_identity>_pipeline` — see `SKILL.md`'s naming convention). Never `harness_get` a pipeline using the user's raw quoted value directly — always resolve the real `spec.pipeline.identity` via **Step U2** first.

If the user's original message already included a specific pipeline identifier, DR Test name, or stage identity, skip asking and go directly to **Step U2**, then match that value against each item's `name` / `identity` in the response.

Otherwise, ask:

> Do you already have the identifier or name for the DR Test pipeline you want to edit? If not, I can list all DR Tests in this project for you.

Either way, proceed to **Step U2** next — never skip straight to Step U3.

### Step U2: List DR Tests and let user select

Call `harness_list(resource_type="chaos_dr_test", org_id="<org_id>", project_id="<project_id>")`, passing `org_id`/`project_id` using the active scope (see Scope Rules above).

The response shape is `{ items: [...], total: N }`. Each item contains:

| Field | Description |
|---|---|
| `name` | DR Test display name |
| `identity` | DR Test stage identifier |
| `description` | Human-readable description |
| `objective` | DR goal statement |
| `tags` | Key-value metadata map |
| `spec.pipeline.name` | Backing pipeline display name |
| `spec.pipeline.identity` | Backing pipeline identifier (use this for fetching YAML) |
| `spec.pipeline.recentRuns` | Last execution statuses and timestamps |

Handle the results:

- **Zero results** — inform the user and offer to create a new DR Test:
  > No DR Tests found in this project. Would you like to create a new DR Test from scratch?

  If yes, switch to `references/create.md`.

- **User already supplied an identifier/name in Step U1** — first try to match it (case-insensitive) against each item's `name` or `identity`. If exactly one match is found, skip the numbered-list prompt below and proceed directly to **Step U3** using that item's `spec.pipeline.identity`. If no match or the match is ambiguous, fall back to the numbered-list flow below.

- **One or more results** — present them as a numbered list showing **name**, **identity**, **description**, **objective**, and **pipeline identifier** (`spec.pipeline.identity`) for each. Also include an option to create a new DR Test from scratch. Ask the user to pick one by number or choose to create new. If the user picks an existing DR Test, extract `spec.pipeline.identity` from the selected item and proceed to **Step U3**. If the user chooses to create new, switch to `references/create.md`.

### Step U3: Fetch pipeline YAML and show for confirmation

Fetch the full pipeline YAML:

`harness_get(resource_type="pipeline", resource_id="<pipeline_identifier>", org_id="<org_id>", project_id="<project_id>")`, passing `org_id`/`project_id` using the active scope (see Scope Rules above).

`<pipeline_identifier>` is always the `spec.pipeline.identity` resolved via Step U2 — never the raw stage identity/name the user typed in Step U1. If this call 404s, retry once with `<resolved_identity>_pipeline` before reporting an error to the user (defends against a DR Test whose pipeline identifier does not follow the standard convention).

The `yamlPipeline` field in the response contains the complete YAML — see `SKILL.md`'s `DRTest Pipeline — Created via MCP with Empty Steps` for the expected shape.

Present the pipeline details and YAML to the user:

> Found the DR Test pipeline:
> - **Name**: `<name>`
> - **Identifier**: `<identifier>`
> - **Org / Project**: `<orgIdentifier>` / `<projectIdentifier>`
> - **DRTest stage(s)**: `<stage names and identifiers>`
> - **Existing chaos steps**: `<list of step names + types in each DRTest stage>`
>
> Current pipeline YAML: (YAML content, pretty-printed)
>
> Do you want to proceed to edit this pipeline? (Yes / No)

- **No** — stop here; no changes made.
- **Yes** — load the fetched YAML as the working state and proceed to **Choose Action (edit mode)** below.

## Choose Action (edit mode)

This section is the action hub for the EDIT flow. After every completed action, loop back here and ask again until the user says "Done" or "Save". (The CREATE flow's initial hub, before any steps exist, is in `references/create.md`.)

Ask:

> What would you like to do?
> 1. **Add an enterprise fault / custom fault / probe / action / chaos experiment** — add new chaos steps to the pipeline
> 2. **Remove a step** — remove an existing chaos step
> 3. **Reorder steps** — change the execution order of existing steps
> 4. **Modify a step** — change a step's name, env/infra, runtime variables, or static values
> 5. **Update pipeline / stage details** — change name, description, objective, or tags
> 6. **Done / Save** — save all changes to the pipeline

IMPORTANT: You MUST present all 6 options above. Do NOT skip straight to the step-type sub-menu (Fault / Probe / Action / Experiment) — that is only for the CREATE flow's initial hub where the pipeline has no steps yet. Always let the user choose the top-level action first.

**Routing:**

- **Add fault / probe / action / chaos experiment** -> ask the user which step type, then follow the type-specific flow in `references/components.md`:
  - **Enterprise Fault** (`is_enterprise=true`) -> Step 1 -> Step 2F -> Step 3
  - **Custom Fault** (`is_enterprise=false`) -> Step 1 -> Step 2F -> Step 3
  - **Probe** -> Step 1 -> Step 2P -> Step 3
  - **Action** -> Step 1 -> Step 2A -> Step 3
  - **Chaos Experiment** -> Step 2E -> Step 3E (skip Step 1 — no infra needed)

  MANDATORY: Step 1 in `references/components.md` MUST be executed every time the user adds a new Fault, Probe, or Action — even if a previous step already selected an environment and infrastructure. Do NOT reuse, carry over, or assume the env/infra from any previously added step. This applies regardless of whether the new step runs in parallel or in series with existing steps — parallel placement does NOT imply shared env/infra. Each step's `infraReference` is independent. Always call `harness_list(resource_type="chaos_environment", org_id="<org_id>", project_id="<project_id>")` fresh for each new step, passing `org_id`/`project_id` using the active scope.

  After the new step is added to the working YAML, return to this hub.
- **Remove a step** -> present the existing steps numbered (name, type, identifier) and ask the user which to remove. Remove the selected step from the in-memory YAML and return to this hub.
- **Reorder steps** -> present the current step order and ask the user for the new order. Apply the reorder to the in-memory YAML and return to this hub.
- **Modify a step** -> present the existing steps numbered (name, type, identifier) and ask the user which to modify. Then ask what to change. The step's `identifier` and `identity` (component reference) are immutable — they cannot be changed.

  Allowed modifications:

  - **Change name** — update the step's `name` directly in the in-memory YAML. The `identifier` stays unchanged. Return to this hub.
  - **Change environment / infrastructure** — go to `references/components.md`'s `Step 1` to pick a new environment and infrastructure. Update the step's `infraReference` in the in-memory YAML. Return to this hub. (Not applicable for Chaos Experiment steps — they have no `infraReference`.)
  - **Change runtime variables** — re-fetch variables using the step's existing component identity:
    - For ChaosProbe / ChaosFault / ChaosAction -> go to `references/components.md`'s `Step 3` with the step's current `identity` and type
    - For Chaos (experiment) -> go to `references/components.md`'s `Step 3E` with the step's current `experimentRef`

    Present the variables to the user, let them update values, then update `tasks` in the in-memory YAML. Return to this hub.
  - **Change static values** — update these directly in the in-memory YAML without calling any MCP endpoint:
    - `duration` (ChaosProbe / ChaosAction only) — validate format: `^\d+(\.\d+)?(ms|s|m|h)$`
    - `expectedResilienceScore` (Chaos Experiment only) — fixed integer (0-100), runtime (`<+input>`), or omit
    - `assertion` (Chaos Experiment only) — fixed value, runtime (`<+input>`), or omit

    Return to this hub.
  - **Change the component itself** (e.g., swap one probe for a different probe, or change from a probe to an action) — this is NOT a modify operation. Inform the user that the component (`identity`) cannot be changed in-place. Offer to **remove** the current step and **add a new one** instead — return to this hub so the user can do both.

- **Update pipeline / stage details** -> show the current values of the editable fields and ask the user which to change:
  - `pipeline.name` — pipeline display name
  - `pipeline.description` — pipeline description
  - `stage.name` — stage display name
  - `stage.description` — stage description
  - `stage.objective` — DR goal statement
  - `stage.tags` — key-value metadata map

  Do NOT change `identifier`, `orgIdentifier`, or `projectIdentifier` — these are immutable. Apply the changes to the in-memory YAML and return to this hub.
- **Done / Save** -> proceed to `references/components.md`'s `Step 4: Save DR Test`.

After any chosen action completes and the working YAML is updated, **loop back to this hub** and ask again. Keep looping until the user says "Done", "Save", or otherwise indicates they are finished — then proceed to `Step 4: Save DR Test` in `references/components.md`.

IMPORTANT: At least one chaos step MUST remain in the pipeline before it can be saved. The pipeline will almost always already have steps, but do NOT allow saving if all steps have been removed.

---
For the detailed mechanics of naming, environment/infra selection, step-type selection, runtime variables, and saving, see `references/components.md`. To create a brand-new DR Test pipeline instead, see `references/create.md`.
