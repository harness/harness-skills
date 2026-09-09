# Creating a DR Test Pipeline

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

## Creating a New DR Test Pipeline

This file drives creating a brand-new DR Test pipeline from scratch. If the user's original message referenced an existing pipeline by name or identifier (e.g. "add steps to `my_dr_test`"), that is EDIT intent — stop and follow `references/edit.md` instead of creating a duplicate.

### Step Create

1. If the user did not already provide a name in their original message, ask:
   > What should I name the new DR Test pipeline?

   Derive the `identifier` automatically from the name: lowercase, replace spaces with underscores, strip characters not matching `[a-zA-Z0-9_$]`. Example: name `Payment DB Failover` -> identifier `payment_db_failover`. Do NOT ask the user to confirm the identifier.

   After deriving, validate the result against `^[a-zA-Z_][a-zA-Z0-9_$]{0,127}$`:
   - If it starts with a digit, prepend `_`.
   - If it is empty (e.g., the name had no valid characters), ask the user to provide an explicit identifier instead of auto-deriving.

   The MCP also accepts optional fields — use them if the user provided them, but do not prompt for them:

   | Field | Required | Notes |
   |---|---|---|
   | `name` | yes | Display name. Becomes stage name; pipeline name = `<name> Pipeline` |
   | `identifier` | yes | Auto-derived from name. Must match `^[a-zA-Z_][a-zA-Z0-9_$]{0,127}$`. Becomes stageIdentifier; pipelineIdentifier = `<identifier>_pipeline` |
   | `description` | no | Human-readable description of the DR Test scenario |
   | `objective` | no | DR goal statement, e.g. "Validate failover to secondary region within 30s" |
   | `tags` | no | Key-value metadata map, e.g. `{"team": "infra", "env": "prod"}` |

2. Call `harness_create(resource_type="chaos_dr_test", org_id="<org_id>", project_id="<project_id>", body={"name": "<name>", "identifier": "<identifier>", ...})`, passing `org_id`/`project_id` using the active scope (see Scope Rules above). This creates a pipeline skeleton with one empty DRTest stage (`steps: []`). The create response returns metadata only, NOT the full pipeline YAML.

3. Fetch the full pipeline YAML: `harness_get(resource_type="pipeline", resource_id="<identifier>_pipeline", org_id="<org_id>", project_id="<project_id>")`. The `yamlPipeline` field in the response contains the complete YAML — see `SKILL.md`'s `DRTest Pipeline — Created via MCP with Empty Steps` for the expected shape.

4. Load the fetched YAML as the working state, then proceed to **Choose Action (create mode)** below.

## Choose Action (create mode)

This section is the entry point for the CREATE flow's action hub. After every completed action, loop back here and ask again until the user says "Done" or "Save". (The EDIT flow has its own fuller hub with additional options — see `references/edit.md`.)

Ask:

> What would you like to add to the DR Test pipeline? **Enterprise Fault**, **Custom Fault**, **Probe**, **Action**, or **Chaos Experiment**? (You can also say **Done** or **Save** to save the pipeline.)

**Routing:**

- **Add fault / probe / action / chaos experiment** -> ask the user which step type, then follow the type-specific flow in `references/components.md`:
  - **Enterprise Fault** (`is_enterprise=true`) -> Step 1 -> Step 2F -> Step 3
  - **Custom Fault** (`is_enterprise=false`) -> Step 1 -> Step 2F -> Step 3
  - **Probe** -> Step 1 -> Step 2P -> Step 3
  - **Action** -> Step 1 -> Step 2A -> Step 3
  - **Chaos Experiment** -> Step 2E -> Step 3E (skip Step 1 — no infra needed)

  MANDATORY: Step 1 in `references/components.md` MUST be executed every time the user adds a new Fault, Probe, or Action — even if a previous step already selected an environment and infrastructure. Do NOT reuse, carry over, or assume the env/infra from any previously added step. This applies regardless of whether the new step runs in parallel or in series with existing steps — parallel placement does NOT imply shared env/infra. Each step's `infraReference` is independent. Always call `harness_list(resource_type="chaos_environment", org_id="<org_id>", project_id="<project_id>")` fresh for each new step, passing `org_id`/`project_id` using the active scope.

  After the new step is added to the working YAML, return to this hub.
- **Done / Save** -> proceed to `references/components.md`'s `Step 4: Save DR Test`.

After any chosen action completes and the working YAML is updated, **loop back to this hub** and ask again. Keep looping until the user says "Done", "Save", or otherwise indicates they are finished — then proceed to `Step 4: Save DR Test` in `references/components.md`.

IMPORTANT: At least one chaos step MUST be present in the pipeline before it can be saved. If the user says "Done" with zero steps, block with a request to add at least one step first.

---
For the detailed mechanics of naming, environment/infra selection, step-type selection, runtime variables, and saving, see `references/components.md`. To edit an existing DR Test pipeline instead, see `references/edit.md`.
