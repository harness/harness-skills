# Creating a Chaos Experiment

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

## Creating a Chaos Experiment

This file drives creating a new chaos experiment from scratch. If the user's intent is to EDIT an existing experiment, stop and follow `references/edit.md` instead.

### Step Create: Creation path selection

Ask:
> How would you like to create the experiment?
> 1. **From scratch** — build a custom experiment by choosing faults, probes, and actions step by step
> 2. **From a template** — use a pre-built experiment template from a ChaosHub

Routing:

- **From scratch** -> proceed to **Step 1**.
- **From a template** -> STOP following this skill entirely. Call `harness_execute(resource_type="chaos_experiment_template", action="create_from_template", org_id="<org_id>", project_id="<project_id>", ...)` which has its own step-by-step workflow in its tool description. Call `harness_describe(resource_type="chaos_experiment_template")` first to see the full instructions, then follow them. Do NOT mix the template workflow with the from-scratch steps in this skill.

### Step 1: Select infrastructure type and environment

#### Step 1a: Choose chaos infrastructure type

Ask the user to select a chaos infrastructure type:

> What type of chaos infrastructure will this experiment target?
> 1. **Kubernetes**
> 2. **Linux**
> 3. **Windows**

Store the selection — it determines which MCP call to use in Step 2 and which YAML kind/fields to produce in Step 5.

#### Step 1b: List environments — user selects one

Call `harness_list(resource_type="chaos_environment", org_id="<org_id>", project_id="<project_id>")`, passing `org_id`/`project_id` using the active scope (see Scope Rules above).

Present the environment names and identifiers to the user and ask them to pick one. This call is the same regardless of infrastructure type.

### Step 2: List infrastructures — user selects one

The MCP call and validity rules differ by infrastructure type selected in Step 1a.

#### If Kubernetes

Call `harness_list(resource_type="chaos_k8s_infrastructure", org_id="<org_id>", project_id="<project_id>", filters={"environment_id": "<selected_env_id>"})`.

Only present infras where BOTH `status == "ACTIVE"` AND `isChaosEnabled == true`.

**Fields to capture from the selected infra** (used when building the YAML in Step 5 — do NOT hardcode any of these):

- `environmentID` + `infraID` -> `spec.infraId` (composite: `<environmentID>/<infraID>`, e.g., `demo/qaauto1`)
- `infraNamespace` -> `metadata.namespace` (e.g., `hce`). This is per-infra and NOT fixed.
- `serviceAccount` -> `spec.serviceAccountName` (e.g., `litmus`). May be empty; when empty, omit `spec.serviceAccountName` from the YAML.
- `infraType` is informational (`KUBERNETESV2`); the YAML's `spec.infraType` stays `KubernetesV2`.

Example response (only the fields this flow consumes — real response has more):

```json
{"infras":[{"identity":"qaauto1","name":"qa-auto-1","environmentID":"demo","infraID":"qaauto1","infraNamespace":"hce","serviceAccount":"litmus","status":"ACTIVE","isChaosEnabled":true}]}
```

> Note: Two fields on the chosen Kubernetes infra feed the ChaosExperiment YAML directly (see Step 5):
>
> - `infraNamespace` -> `metadata.namespace` (e.g., `hce`)
> - `serviceAccount`  -> `spec.serviceAccountName` (e.g., `litmus`)
>
> Never hardcode either value — always take them from the selected infra.

Filter rule: present only entries with `status == "ACTIVE"` AND `isChaosEnabled == true`. If none qualify, do not proceed.

User picks one valid infra (e.g., `qaauto1`) — capture `environmentID`, `infraID`, `infraNamespace`, and `serviceAccount` for Step 5.

#### If Linux or Windows

Call `harness_list(resource_type="chaos_infrastructure", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<Linux|Windows>", "environment_ids": "<selected_env_id>"})`.

Set `infra_type` to `"Linux"` or `"Windows"` matching the user's Step 1a choice.

Only present infras where `isActive == true`. Infras with `isActive == false` must be excluded.

**Fields to capture from the selected infra** (used when building the YAML in Step 5 — do NOT hardcode any of these):

- `infraID` -> `spec.infraId` (UUID alone, NOT a composite — different from Kubernetes which uses `<environmentID>/<infraID>`)
- `infraID` -> every component's `infraId` (in `faultRef`, `probeRef`, `actionRef`) — same UUID as `spec.infraId`
- Machine infras do NOT have `infraNamespace` or `serviceAccount` — omit `metadata.namespace` and `spec.serviceAccountName` from the YAML.
- `environmentID` is informational only and does NOT enter the YAML.

Example response (only the fields this flow consumes — real response has more):

```json
{"totalNoOfInfras":1,"infras":[{"infraID":"1b863a31-b3e9-4287-9dc9-b69763bdee80","name":"linux-agent-1","environmentID":"chaosuxtest","isActive":true,"status":"ACTIVE"}]}
```

Filter rule: present only entries with `isActive == true`. If none qualify, do not proceed.

**Empty-result fallback:** if the default call returns `total: 0`, retry once with `status: "All"` added to `filters` to surface inactive/pending infras for diagnosis:

`harness_list(resource_type="chaos_infrastructure", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<Linux|Windows>", "environment_ids": "<selected_env_id>", "status": "All"})`

If the retry returns entries, present them to the user as informational only (e.g., "Your infrastructure `test-3` is `PENDING` — please retry once it becomes ACTIVE") but do NOT allow selection of non-active entries. Do NOT proceed past Step 2 unless the user picks an entry where `isActive == true`. If the retry also returns nothing, tell the user no machine infrastructure exists for the selected environment and stop.

User picks one valid (active) infra (e.g., `linux-agent-1`) — capture `infraID` for Step 5. (`environmentID` is not used in the YAML for Linux/Windows.)

### Step 3: Ask user for experiment name

Prompt the user to provide a name for the experiment (e.g., `test-exp-007`).

**Name format rules:**
- Only lowercase letters (`a-z`), numbers (`0-9`), and dashes (`-`) are allowed
- No leading or trailing dashes
- Must not be empty

If the user provides a name that violates these rules, reject it, explain the constraint, and ask again. Do NOT proceed until the name is valid.

### Step 4: Generate experiment ID

Generate a fresh UUID v4 for `experimentId`. This is a unique identifier for the experiment, not derived from any other entity.

### Step 5: Produce initial experiment YAML

Assemble the YAML using fixed values, user selections, and the generated ID. The example below shows the Kubernetes shape; for Linux/Windows, apply the overrides listed below.

```yaml
apiVersion: litmuschaos.io/v1beta1
kind: ChaosExperiment
metadata:
  name: test-exp-007
  namespace: hce                # from selected infra's `infraNamespace`
spec:
  cleanupPolicy: delete
  experimentId: 073eea9a-3743-48c2-b600-c09d871054c7
  experimentRunId: ""
  infraId: demo/qaauto1         # <environmentID>/<infraID> from Steps 1+2
  infraType: KubernetesV2
  serviceAccountName: litmus    # from selected infra's `serviceAccount`
  vertices: []
  probeRef: []
  actionRef: []
  faultRef: []
```

**Linux/Windows overrides:** when the user picked Linux or Windows in Step 1a, modify the scaffold above as follows:

- OMIT `metadata.namespace`.
- OMIT `spec.serviceAccountName`.
- OMIT `spec.experimentRunId`.
- `spec.infraId` is the `infraID` UUID alone (e.g. `1b863a31-b3e9-4287-9dc9-b69763bdee80`), NOT `<environmentID>/<infraID>`.
- `spec.infraType` is `Linux` or `Windows` (matches Step 1a), not `KubernetesV2`.

All other fields are identical.

Field reference:

| Field | Source | Notes |
|---|---|---|
| `apiVersion` | Fixed | Always `litmuschaos.io/v1beta1` |
| `kind` | Fixed | Always `ChaosExperiment` |
| `metadata.name` | User input (Step 3) | Experiment name |
| `metadata.namespace` | Step 2 infra response | K8s only — from infra's `infraNamespace` (e.g. `hce`). Omit for Linux/Windows. |
| `spec.cleanupPolicy` | Fixed | Always `delete` |
| `spec.experimentId` | Generated (Step 4) | Fresh UUID v4 |
| `spec.experimentRunId` | Fixed | K8s: `""` initially. Omit for Linux/Windows. |
| `spec.infraId` | Steps 1+2 | K8s: `<environmentID>/<infraID>` composite (e.g. `demo/qaauto1`). Linux/Windows: `<infraID>` UUID alone. |
| `spec.infraType` | Step 1a | K8s: `KubernetesV2`. Linux/Windows: `Linux` or `Windows`. |
| `spec.serviceAccountName` | Step 2 infra response | K8s only — from infra's `serviceAccount` (e.g. `litmus`); omit if empty. Omit for Linux/Windows. |
| `spec.vertices` | Empty | Populated when faults/probes/actions are added |
| `spec.probeRef` | Empty | Populated when probes are added |
| `spec.actionRef` | Empty | Populated when actions are added |
| `spec.faultRef` | Empty | Populated when faults are added |

### Step 6: Choose component to add

Ask the user:

> What would you like to add to the experiment?
> - **Enterprise fault** — built-in fault from Harness
> - **Custom fault** — uploaded into your project
> - **Probe**
> - **Action**
>
> (You can also say **Done** or **Save** to save the experiment.)

**Routing:**

- Any of the four add options -> follow the component-add procedure in `references/components.md`. Pass the user's selection (enterprise fault | custom fault | probe | action) as the entry point. After the component is added to the working YAML and vertices are updated, return here.
- **Done / Save** -> proceed to Step 9 below.

Loop this Step 6 until the user says "Done" or "Save".

IMPORTANT: At least one fault MUST be present before saving. If the user says "Done" with zero faults in `faultRef`, block with: "An experiment must have at least one fault. Please add a fault first."

## Step 9: Save the Experiment

When the user says "Done", "Save", or indicates they are finished building the experiment, save it by calling the MCP endpoint.

### 9a. Prepare the manifest

The `manifest` body field must be a **JSON string** — not YAML, not a JSON object. Convert the working experiment YAML (scaffolded at Step 5, populated via component-add operations in `references/components.md`) as follows:

1. Parse the YAML into a JSON-compatible object
2. Serialize that object to a compact JSON string (no pretty-printing)

This JSON string is the value for the `manifest` field. Preserve value types: numeric values stay as JSON numbers (e.g., `"value":90`), string values stay as JSON strings (e.g., `"value":"<+input>"`).

### 9b. Ask the user for optional fields

Before building the request body, ask the user:

> Would you like to add a **description** or any **custom tags** for this experiment? (Press Enter to skip.)

- **Description** — free text. Default: empty string `""`.
- **Custom tags** — array of strings (e.g., `["tag:team-platform", "env:staging"]`). Default: none.

### 9c. Build the request body

Call `harness_describe(resource_type="chaos_experiment")` and read the `create` operation's `bodySchema` for the authoritative field names, required/optional markers, and validation rules. Then derive each field's value from the experiment state built through Steps 1-5 and the component additions in `references/components.md`:

- `id` — the experiment UUID from Step 4
- `name` — the experiment name from Step 3
- `identity` — auto-generate from the experiment name — lowercase, strip all characters except `a-z` and `0-9`, max 47 chars (e.g., `try-exp-creation-01` -> `tryexpcreation01`).
- `manifest` — the full experiment YAML converted to a JSON string (Step 9a)
- `infra_id` — the infrastructure reference from Steps 1–2: for Kubernetes, `<environmentId>/<infraId>` composite (e.g., `demo/qaauto1`); for Linux/Windows, the selected infrastructure's `infraID` UUID alone.
- `infra_type` — the infrastructure type from Step 1 (e.g., `KubernetesV2`, `Linux`, `Windows`)
- `description` — user input from Step 9b. Default: `""`.
- `tags` — combine auto-generated and user-provided tags:
  - One `"fault=<identity>"` per unique fault identity in `faultRef`
  - One `"probe=<identity>"` per unique probe identity in `probeRef`
  - Plus any custom tags the user provided in Step 9b
  - Deduplicate the final array
- `is_single_run_cron` — `false`. Omit unless scheduling a single-run cron.

Call the save operation with `org_id`/`project_id` passed top-level (using the active scope established per Scope Rules above), NOT inside `body`:

```text
harness_create(
  resource_type="chaos_experiment",
  org_id="<org_id>",
  project_id="<project_id>",
  body={
    "id": "<experiment_uuid>",
    "name": "<experiment_name>",
    "identity": "<experiment_identity>",
    "manifest": "<compact_json_string>",
    "infra_id": "<infra_reference>",
    "infra_type": "<KubernetesV2|Linux|Windows>",
    "description": "<description>",
    "tags": ["<tags>"]
  }
)
```

### 9d. Handle the response

- **Success** — the response contains `data.id` and `data.name`. Present the experiment name and confirm it was saved successfully.
- **Failure** — present the error message to the user and suggest they check the inputs (e.g., duplicate name/identity, invalid manifest, missing required fields) and retry.

---
For the detailed mechanics of any fault / probe / action add (variables, target workloads, secrets, vertices wiring, YAML validation rules), see `references/components.md`. For editing an existing experiment, see `references/edit.md`.
