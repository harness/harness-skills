# Editing an Existing Chaos Experiment

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

## Experiment Components

A chaos experiment combines three types of components in a workflow:

- **Faults** — the disruptions injected into the system. Each fault targets a specific resource (pod, node, VM, cloud service) and has tunables that control blast radius and behavior. Examples: pod-delete, pod-cpu-hog, node-drain, gcp-vm-service-kill, network-latency. **At least one fault is required** for a valid experiment.
- **Probes** — hypothesis validators that check whether the system survived correctly. They run during the experiment to assert expected behavior. Types: HTTP (check endpoint responses), CMD (run shell commands), Prometheus (query metrics), Kubernetes (check k8s resource state), Datadog (assert APM metrics). Probes are optional.
- **Actions** — operational steps beyond fault injection. Types: Delay (time delays between phases), Custom Script (run setup/validation/cleanup), Container (run commands in containers). Actions are optional.

An experiment can contain any number of faults, probes, and actions **in any order**. The user can keep adding components at any position in the workflow. The `vertices` array in the YAML defines the execution sequence.

## Editing an Existing Chaos Experiment

This file drives editing an existing chaos experiment. If the user's intent is to CREATE a new experiment, stop and follow `references/create.md` instead.

**IMMUTABLE KEYS** — The existing `experimentId` (UUID) AND `identity` (slug) from the fetched experiment MUST be preserved throughout the flow. Do NOT regenerate either — both are permanent keys. Step 9's save endpoint is an upsert; sending the same id updates the experiment in place.

### Step Update: Load existing experiment

#### Step U1: Ask user for experiment name or UUID

If the user's original message already included a specific experiment name or UUID, skip asking and use it directly. Otherwise, ask:

> Which experiment would you like to edit? Please provide either its **name** (e.g., `test-exp-007`) or its **UUID** (e.g., `218b1053-e0d6-40d6-bf00-1fecc0fc0faf`).

Detect the input type: if the value matches a UUID v4 pattern (`^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$`), treat it as a UUID; otherwise treat it as a name.

#### Step U2: Look up the experiment

Call the appropriate MCP list based on input type:

- **By name** — `harness_list(resource_type="chaos_experiment", org_id="<org_id>", project_id="<project_id>", filters={"experiment_name": "<name>"})` (case-insensitive contains/regex match)
- **By UUID** — `harness_list(resource_type="chaos_experiment", org_id="<org_id>", project_id="<project_id>", filters={"experiment_ids": "<uuid>"})` (exact match; comma-separate multiple UUIDs)

Pass `org_id`/`project_id` using the active scope (see Scope Rules above).

The list response already includes each experiment's full details plus the `manifest` (YAML string). Do NOT make an additional `harness_get` call — everything needed is in the list response.

Handle the results:

- **Zero results** — tell the user no experiment matched that name/UUID and offer two options:
  > No experiment found with that name/UUID. Would you like to:
  > 1. Try a different name or UUID?
  > 2. Create a new experiment with this name instead?

  If option 1, loop back to Step U1. If option 2, STOP this skill and tell the user: "I'll create a new experiment named `<name>`." Then follow the procedure in `references/create.md` starting at Step 1 — when you reach that skill's Step 3 (ask for name), use the already-known `<name>` rather than re-asking.
- **One result** — proceed to Step U3 with that experiment.
- **Multiple results** — present them numbered (name, identity, infraId, description) and ask the user to pick one. Then proceed to Step U3 with the selection.

#### Step U3: Show details and confirm

Present the selected experiment's details and YAML manifest:

> Found the experiment:
> - **Name**: `<name>`
> - **Identity**: `<identity>`
> - **UUID**: `<experimentId>`
> - **Infrastructure**: `<infraId>`
> - **Description**: `<description>`
> - **Tags**: `<tags>`
>
> Current manifest: (YAML manifest content, pretty-printed)
>
> Do you want to proceed to edit this experiment? (Yes / No)

- **No** — stop here; no changes made.
- **Yes** — load the fetched manifest as the working YAML state. Also initialize `current_description` and `current_tags` from the fetched experiment. Preserve `spec.experimentId`, `metadata.name`, `spec.infraId`, and the original `identity`, then jump to **Step 6**.

### Step 6: Modification hub (edit mode)

Loaded manifest is the working YAML state from Step U3. Ask the user:

> What would you like to do?
> 1. **Add an enterprise fault** to the experiment
> 2. **Add a custom fault** to the experiment
> 3. **Add a probe** to the experiment
> 4. **Add an action** to the experiment
> 5. **Remove a fault / probe / action** from the experiment
> 6. **Change name** — rename the experiment
> 7. **Change environment / infrastructure** — retarget to a different infra
> 8. **Change description / tags**
> 9. **Done / Save** — save the changes

**Routing:**

- Options 1-4 (add a component) -> follow the component-add procedure in `references/components.md`. After the new entry is in the appropriate ref array and vertices are updated, return here.
- Option 5 (remove) -> follow `## Removing a Component` in `references/components.md`. Return here.
- Option 6 (change name) -> follow `### Step 3: Ask user for experiment name` in `references/create.md` to get a valid new name (format rules: lowercase letters `a-z`, numbers `0-9`, dashes `-` only; no leading/trailing dashes; non-empty). Then update `metadata.name` in the working YAML. Do NOT regenerate `experimentId` or `identity`. Return here.
- Option 7 (change env/infra) -> follow `### Step 1: Select infrastructure type and environment` and `### Step 2: List infrastructures` in `references/create.md` to pick a new env + infra.

  Before applying the selection, store the existing `spec.infraType` as `old_infra_type` and the selected type as `new_infra_type`.

  Refresh the manifest:
  - Set `spec.infraId` to `<environmentID>/<infraID>` for Kubernetes or the infrastructure UUID for Linux/Windows.
  - Set `spec.infraType` to `new_infra_type`.
  - Set every existing fault/probe/action ref's `infraId` to the selected short infra ID/UUID.
  - For `KubernetesV2`: set `metadata.namespace` from `infraNamespace`; set `spec.serviceAccountName` from `serviceAccount` when non-empty, otherwise remove that key; ensure `spec.experimentRunId` exists, using `""` when absent.
  - For `Linux` or `Windows`: remove `metadata.namespace`, `spec.serviceAccountName`, and `spec.experimentRunId`.

  If `old_infra_type != new_infra_type`, revalidate every existing component before allowing save:
  - List enterprise and custom faults for `new_infra_type` and verify every `faultRef.identity` is in the matching enterprise/custom set.
  - List probes with `infra_type=new_infra_type` and verify every `probeRef.identity`.
  - List actions with `infra_type=new_infra_type` and verify every `actionRef.identity`.
  - Present incompatible components and require the user to replace or remove them. Do not save while any incompatible component remains.

  Run the YAML Validation Rules in `references/components.md`, then return here.
- Option 8 (change description/tags) -> show `current_description` and `current_tags`. For each field let the user **keep**, **replace**, or **clear** it. Update the corresponding current value; clearing means `current_description = ""` or `current_tags = []`. Record that metadata was handled, then return here.
- Option 9 (Done / Save) -> proceed to Step 9 below.

Loop this Step 6 until the user says "Done" / "Save".

IMPORTANT: At least one fault MUST remain in `faultRef`. If the user tries to remove the last fault, block with: "An experiment must have at least one fault. To remove this fault, add a replacement first."

## Step 9: Save the Experiment

> **Edit flow note:** Step 9 works unchanged for edits. The `POST /rest/v2/experiment` endpoint is an upsert — when the body's `id` matches an existing experiment's UUID, the backend treats it as an update (auditAction becomes "UPDATE").
>
> IMMUTABLE fields for edits (NEVER change these):
> - `id` / `experimentId` (UUID) — permanent primary key
> - `identity` (slug) — permanent secondary key
>
> Both must be preserved EXACTLY as returned from Step U2, even if the user renamed the experiment via Step 6. Regenerating either would break associations (run history, input sets, schedules, etc.) and create a new experiment instead of updating the existing one.

When the user says "Done", "Save", or indicates they are finished building the experiment, save it by calling the MCP endpoint.

### 9a. Prepare the manifest

The `manifest` body field must be a **JSON string** — not YAML, not a JSON object. Convert the working experiment YAML (loaded at Step U2 and modified through Step 6) as follows:

1. Parse the YAML into a JSON-compatible object
2. Serialize that object to a compact JSON string (no pretty-printing)

This JSON string is the value for the `manifest` field. Preserve value types: numeric values stay as JSON numbers (e.g., `"value":90`), string values stay as JSON strings (e.g., `"value":"<+input>"`).

### 9b. Preserve or update optional fields

If option 8 was already completed, reuse `current_description` and `current_tags` without asking again.

Otherwise show their current values and ask:

> Keep the existing **description** and **custom tags**, or would you like to change or clear either one?

Default to **keep**. Only replace or clear a value when the user explicitly requests it.

### 9c. Build the request body

Call `harness_describe(resource_type="chaos_experiment")` and read the `create` operation's `bodySchema` for the authoritative field names, required/optional markers, and validation rules. Then derive each field's value from the loaded experiment (Step U2) plus any modifications made via Step 6:

- `id` — the existing UUID from Step U2 — NEVER regenerate (per the IMMUTABLE KEYS rule above)
- `name` — the existing name from Step U2, or the new name if the user renamed via Step 6 option 6
- `identity` — use the EXISTING identity from Step U2 — do NOT regenerate it, even if the user renamed the experiment. The identity is a permanent key.
- `manifest` — the full experiment YAML converted to a JSON string (Step 9a)
- `infra_id` — the infrastructure reference from Step U2 (or refreshed if the user changed infrastructure via Step 6 option 7): `<environmentId>/<infraId>` composite for Kubernetes, or the infrastructure UUID alone for Linux/Windows
- `infra_type` — the infrastructure type from Step U2 (e.g., `KubernetesV2`, `Linux`, `Windows`), or refreshed via Step 6 option 7 if the user changed infrastructure
- `description` — `current_description`; preserve the fetched value unless the user explicitly replaced or cleared it
- `tags` — build the final array as follows:
  - Keep every entry from `current_tags` that does not start with `fault=` or `probe=`
  - Add one `"fault=<identity>"` per unique final `faultRef` identity
  - Add one `"probe=<identity>"` per unique final `probeRef` identity
  - Deduplicate the final array
- `is_single_run_cron` — `false`. Omit unless scheduling a single-run cron.

Call the upsert with `org_id`/`project_id` passed top-level (using the active scope established per Scope Rules above), NOT inside `body`. Preserve the existing `id` and `identity` exactly; only the mutable fields below may change:

```text
harness_create(
  resource_type="chaos_experiment",
  org_id="<org_id>",
  project_id="<project_id>",
  body={
    "id": "<existing_uuid>",
    "name": "<existing_or_updated_name>",
    "identity": "<existing_identity>",
    "manifest": "<updated_compact_json_string>",
    "infra_id": "<current_infra_reference>",
    "infra_type": "<current_infra_type>",
    "description": "<description>",
    "tags": ["<tags>"]
  }
)
```

### 9d. Handle the response

- **Success** — the response contains `data.id` and `data.name`. Present the experiment name and confirm it was saved successfully.
- **Failure** — present the error message to the user and suggest they check the inputs (e.g., duplicate name/identity, invalid manifest, missing required fields) and retry.

---
For the detailed mechanics of any fault / probe / action add or remove, see `references/components.md`. For creating a new experiment from scratch, see `references/create.md`.
