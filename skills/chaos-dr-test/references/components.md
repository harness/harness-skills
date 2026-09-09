# DR Test Pipeline Step Components

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

## When to use this reference

This file is the canonical how-to for naming, wiring, and populating DR Test pipeline chaos steps (`ChaosFault`, `ChaosProbe`, `ChaosAction`, `Chaos`). Read it from the Choose Action hub in `references/create.md` or `references/edit.md`.

It assumes a DR Test pipeline YAML is already loaded as the working state (either just created with `steps: []`, or fetched from an existing pipeline). If you arrived here without a loaded pipeline:

- To create a new DR Test pipeline -> follow `references/create.md`.
- To edit an existing DR Test pipeline -> follow `references/edit.md`.

After completing a step-add operation, return to the calling flow's Choose Action hub (`references/create.md` or `references/edit.md`) so the user can add another step or save.

## Step Naming and Execution Order

Before generating steps YAML, the agent MUST collect the following from the user for every step they want to add:

1. **Unique name** — Each step must have a unique `name` and `identifier` within the stage. Ask the user to name every step. The `identifier` can be derived from the name (e.g., name `httpProbe1` -> identifier `httpProbe1`).
2. **Parallel vs series** — Ask the user which steps should run in parallel and which should run in series. Steps in parallel are wrapped in a `parallel:` block. Steps in series are listed sequentially in `steps:`.
3. **Order confirmation** — Confirm the execution order with the user before generating YAML. Incorrect ordering can cause the pipeline to fail.

### Example: Series + Parallel Steps (different infra per step)

In this example, `ChaosProbeHttp1` runs first (series), then three steps run in parallel — each targeting a DIFFERENT environment/infrastructure. Finally, a `Chaos` (experiment) step runs in series after the parallel block. Note all four step types are shown:

Example (shown as minified JSON for token brevity; emit as block-style YAML per `SKILL.md`'s YAML Output Conventions):

```json
{"steps":[{"step":{"type":"ChaosProbe","name":"ChaosProbeHttp1","identifier":"ChaosProbe_1","spec":{"identity":"new-http-probe-007","duration":"10s","infraReference":"demo/qaauto1"}}},{"parallel":[{"step":{"type":"ChaosProbe","name":"commandPromptTesting1","identifier":"commandPrompt","spec":{"identity":"new-cmd-probe-uuid-test","duration":"<+input>","infraReference":"demo/qaauto1"}}},{"step":{"type":"ChaosFault","name":"faultCheck1","identifier":"faultCheck1","spec":{"identity":"gcp-vm-service-kill","infraReference":"testdata/datadog1","tasks":[{"identifier":"gcp-vm-service-kill","values":[{"name":"TOTAL_CHAOS_DURATION","value":"<+input>"},{"name":"NODE_LABEL","value":"<+input>"},{"name":"VM_INSTANCE_NAME","value":"<+input>"},{"name":"LIB_IMAGE","value":"<+input>"},{"name":"SERVICE_NAME","value":"<+input>"},{"name":"MASK","value":"<+input>"},{"name":"VM_USERNAME","value":"<+input>"},{"name":"SUDO_ENABLED","value":"<+input>"},{"name":"ZONE","value":"<+input>"},{"name":"SET_HELPER_DATA","value":"<+input>"},{"name":"GCP_PROJECT_ID","value":"<+input>"},{"name":"RAMP_TIME","value":"<+input>"},{"name":"CLOUD_SECRET_NAME","value":"<+input>"}]}]}}},{"step":{"type":"ChaosAction","name":"ChaosActionCheck1","identifier":"ChaosActionCheck1","spec":{"identity":"test-action-008","duration":"<+input>","infraReference":"neeldev/neelchaosinfra","tasks":[{"identifier":"test-action-008","values":[{"name":"DURATION","value":"<+input>"},{"name":"VARIABLES_0_variable1","value":"<+input>"}]}]}}}]},{"step":{"type":"Chaos","name":"ChaosExperimentTest1","identifier":"ChaosExperimentTest1","spec":{"experimentRef":"a7c3e1f2-9b4d-4e8a-b6f0-2d5c8a3e7f19","expectedResilienceScore":89,"assertion":"optional assertion","tasks":[{"identifier":"gcp-vm-service-kill-29m","values":[{"name":"VM_INSTANCE_NAME","value":"<+input>"},{"name":"SERVICE_NAME","value":"<+input>"},{"name":"ZONE","value":"<+input>"},{"name":"GCP_PROJECT_ID","value":"<+input>"}]},{"identifier":"new-http-probe-00008-jjp","values":[{"name":"METHOD_GET_RESPONSECODE","value":""},{"name":"VARIABLES_0_testRuntime1","value":"<+input>"},{"name":"VARIABLES_1_testR2","value":""}]}]}}}]}
```

Key points:
- Steps inside `parallel:` run simultaneously
- Top-level items in `steps:` run sequentially (series)
- A `parallel:` block is itself one item in the `steps:` array, so it runs in sequence relative to the items before/after it
- Each step has its own `infraReference` — parallel steps do NOT need to share the same environment or infrastructure. The example above shows three different values: `demo/qaauto1`, `testdata/datadog1`, and `neeldev/neelchaosinfra`.
- `Chaos` (experiment) steps have NO `infraReference` — they use `experimentRef` instead (the experiment itself defines its infra).

---

## Step 1: Select environment and infrastructure

MANDATORY: Run this step EVERY TIME a new `ChaosProbe`, `ChaosFault`, or `ChaosAction` is being added. Skip only for `Chaos` / Chaos Experiment steps.

Do NOT reuse environment or infrastructure from a previously added step. Every pipeline step can run on a different environment and infrastructure — each step has its own `infraReference` and they are independent. You MUST call `harness_list(resource_type="chaos_environment", org_id="<org_id>", project_id="<project_id>")` again and ask the user to pick for THIS step.

1. **List environments** — call `harness_list(resource_type="chaos_environment", org_id="<org_id>", project_id="<project_id>")`, passing `org_id`/`project_id` using the active scope (see Scope Rules above). Present the environment names and identifiers to the user and ask them to pick one (e.g., `demo`).

2. **List infrastructures for the chosen environment** — call `harness_list(resource_type="chaos_k8s_infrastructure", org_id="<org_id>", project_id="<project_id>", filters={"environment_id": "<selected_env_id>"})`.

   Only present infras where BOTH conditions are true:
   - `status == "ACTIVE"`
   - `isChaosEnabled == true`

   Exclude any infra where `status != "ACTIVE"` OR `isChaosEnabled == false`. Do NOT let the user select an invalid infra — the pipeline will fail. If no valid infras exist, inform the user and do not proceed.

   User picks one valid infra (e.g., `qaauto1`). Capture `selected_infra_type = "KubernetesV2"` — DR Test infra listing only covers Kubernetes today (`chaos_k8s_infrastructure`), so this is currently always `KubernetesV2`, but Step 2F/2A below MUST use this captured value rather than a hardcoded literal.

3. **Compose `infraReference`** — the format is `<environmentId>/<infraId>`. Example: environment `demo` + infra `qaauto1` = `demo/qaauto1`.

---

## Step 2P: Select Probe

Ask the user which probe type they want, or All:

Choose a type and pass it as `entity_type` in the MCP call (omit for All): HTTP Probe (`httpProbe`), Command Probe (`cmdProbe`), Datadog Probe (`datadogProbe`), Dynatrace Probe (`dynatraceProbe`), K8S Probe (`k8sProbe`), Prometheus Probe (`promProbe`), SLO Probe (`sloProbe`), APM Probe (`apmProbe`), Container Probe (`containerProbe`).

If user picks a specific type: `harness_list(resource_type="chaos_probe", org_id="<org_id>", project_id="<project_id>", filters={"entity_type": "<value>"})`

If user picks All (or does not specify): `harness_list(resource_type="chaos_probe", org_id="<org_id>", project_id="<project_id>")`

Pass `org_id`/`project_id` using the active scope. User picks one probe from the results.

---

## Step 2F: Select Fault

Use the `is_enterprise` value captured during the Choose Action routing (defaults to `true` if the user said just "fault").

Call: `harness_list(resource_type="chaos_fault", org_id="<org_id>", project_id="<project_id>", filters={"is_enterprise": <true|false>, "infrastructure": "<selected_infra_type>"})` — use the `selected_infra_type` captured in Step 1 (currently always `KubernetesV2`). Pass `org_id`/`project_id` using the active scope.

Present the fault names, identities, and categories. **Always state which set this is** — e.g. "Here are the **enterprise** faults available. If you want a **custom** fault from your project instead, just say so." (Or vice versa when `is_enterprise=false`.) If the user asks to switch, re-run the call with the flipped value.

---

## Step 2A: Select Action

Actions are reusable steps (delay, custom script, container) that can be embedded in chaos experiment workflows.

### Filtering

Ask the user which action type they want, or All:

Choose a type and pass it as `entity_type` in the MCP call (omit for All): Delay (`delay`), Custom Script (`customScript`), Container (`container`).

Available filters for `harness_list(resource_type="chaos_action", filters={...})`:

| Filter | Description | Values |
|---|---|---|
| `infra_type` | Infrastructure type | `"Kubernetes"`, `"KubernetesV2"`, `"Linux"`, `"Windows"`, `"CloudFoundry"`, `"Container"` |
| `entity_type` | Action type | `"delay"`, `"customScript"`, `"container"` |
| `search` | Filter by action name (substring, case-insensitive) | any string |
| `hub_identity` | Filter by chaos hub identity | hub identity string |
| `include_all_scope` | Include actions across all orgs/projects in the account | `true` / `false` (default `false`) |

Use the `selected_infra_type` captured in Step 1 (currently always `KubernetesV2`) for `infra_type` in every call below — do not hardcode the literal.

If user picks a specific type: `harness_list(resource_type="chaos_action", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<selected_infra_type>", "entity_type": "<value>"})`

If user picks All (or does not specify): `harness_list(resource_type="chaos_action", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<selected_infra_type>"})`

To search by name: `harness_list(resource_type="chaos_action", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<selected_infra_type>", "search": "<name>"})`

Pass `org_id`/`project_id` using the active scope on all of the above.

### Response fields

The response shape is `{ items: [...], total: N }`. Each item contains:

| Field | Description |
|---|---|
| `identity` | Unique action identity (use this for step `spec.identity`) |
| `name` | Display name |
| `description` | Human-readable description |
| `type` | Action type: `delay`, `customScript`, or `container` |
| `infrastructureType` | Infrastructure type (e.g., `Kubernetes`) |
| `tags` | String array of tags |
| `variables` | Variable list for the action |
| `actionReferenceCount` | Number of experiments referencing this action |
| `createdAt` / `updatedAt` | Timestamps |

Present `identity`, `name`, `type`, `description`, and `infrastructureType` to the user and ask them to pick one.

If the user asks for additional operations (e.g., get details, get manifest), run `harness_describe(resource_type="chaos_action")` to discover what is available.

---

## Step 2E: Select Chaos Experiment

Call `harness_list(resource_type="chaos_experiment", org_id="<org_id>", project_id="<project_id>")`. To search by name: `harness_list(resource_type="chaos_experiment", org_id="<org_id>", project_id="<project_id>", filters={"experiment_name": "<name>"})`. Pass `org_id`/`project_id` using the active scope.

Present the experiment names, identities, and infrastructure IDs to the user and ask them to pick one.

To create or edit the standalone experiment itself (not this pipeline step), stop and use `chaos-experiment` instead.

---

## Step 3: Fetch Runtime Variables and Build Step YAML

After selecting a component in Step 2, fetch its runtime variables to populate the `tasks` field in the step YAML.

For **Probe**, **Fault**, and **Action** steps, use a single unified endpoint:

`harness_get(resource_type="chaos_component_variable", resource_id="<selected-component-identity>", org_id="<org_id>", project_id="<project_id>", params={"type": "<Probe|Fault|Action>"})`, passing `org_id`/`project_id` using the active scope.

Set `type` (inside `params`) to match the step being added:
- Adding a ChaosProbe -> `type="Probe"`
- Adding a ChaosFault -> `type="Fault"`
- Adding a ChaosAction -> `type="Action"`

The response (after MCP extraction) has shape: `{ name: "<component-identity>", variables: [...] }`

Handle the variables using the **Runtime Variables Workflow** below, then build the step YAML.

### `duration` field rules

- **ChaosProbe** and **ChaosAction** — `duration` is ALWAYS required at the step level. Always ask the user for it. Do not rely on the runtime variable API for this value. The user may give a fixed value matching `^\d+(\.\d+)?(ms|s|m|h)$` (e.g., `"10s"`, `"1m"`), or mark it as runtime by using the literal `<+input>` (exempt from the regex check). Validate before generating YAML.
- **ChaosFault** — does NOT have `duration` at the step level. Fault duration is controlled via task variables returned by the runtime variables API (e.g., `TOTAL_CHAOS_DURATION` or similar). Do not ask the user for a separate `duration` field for faults.

### `tasks` field rules

The `tasks` array holds runtime variable values for the step:

```yaml
tasks:
  - identifier: <component-identity>
    values:
      - name: VARIABLE_NAME
        value: "fixed-value-or-<+input>"
```

- `tasks[].identifier` = the component `identity` (same as `spec.identity`)
- `tasks[].values[]` = `{name, value}` pairs from the Runtime Variables Workflow
- `tasks` is **omitted entirely** when the API returns no variables

### Example — Full DRTest Pipeline with Probe, Fault, and Action

In this example, `ChaosFault_1` and `ChaosProbe_1` run in parallel first, then `ChaosAction_1` runs after both complete:

Pipeline manifest (minified JSON for brevity; emit as block-style YAML per `SKILL.md`'s YAML Output Conventions):

```json
{"pipeline":{"description":"","identifier":"priyanshu_dr_test_1_pipeline","name":"priyanshu_dr_test_1 Pipeline","orgIdentifier":"default","projectIdentifier":"ChaosDev1","stages":[{"stage":{"description":"optional desc","identifier":"priyanshu_dr_test_1","name":"priyanshu_dr_test_1","objective":"optional obj","spec":{"execution":{"steps":[{"parallel":[{"step":{"type":"ChaosFault","name":"ChaosFault_1","identifier":"ChaosFault_1","spec":{"identity":"gcp-vm-service-kill","infraReference":"demo/qaauto1","tasks":[{"identifier":"gcp-vm-service-kill","values":[{"name":"TOTAL_CHAOS_DURATION","value":10},{"name":"NODE_LABEL","value":"Node_123"},{"name":"VM_INSTANCE_NAME","value":"required_var_given_value"},{"name":"LIB_IMAGE","value":""},{"name":"SERVICE_NAME","value":"<+input>"},{"name":"MASK","value":""},{"name":"VM_USERNAME","value":"<+input>"},{"name":"SUDO_ENABLED","value":""},{"name":"ZONE","value":"<+input>"},{"name":"SET_HELPER_DATA","value":""},{"name":"GCP_PROJECT_ID","value":"<+input>"},{"name":"RAMP_TIME","value":""},{"name":"CLOUD_SECRET_NAME","value":""}]}]}}},{"step":{"type":"ChaosProbe","name":"ChaosProbe_1","identifier":"ChaosProbe_1","spec":{"identity":"new-http-probe-00008","duration":"10s","infraReference":"demo/qaauto1","tasks":[{"identifier":"new-http-probe-00008","values":[{"name":"METHOD_GET_RESPONSECODE","value":"200"},{"name":"VARIABLES_0_testRuntime1","value":"<+input>"},{"name":"VARIABLES_1_testR2","value":"random_value"}]}]}}}]},{"step":{"type":"ChaosAction","name":"ChaosAction_1","identifier":"ChaosAction_1","spec":{"identity":"test-action-008","duration":"<+input>","infraReference":"demo/qaauto1","tasks":[{"identifier":"test-action-008","values":[{"name":"DURATION","value":"<+input>"},{"name":"VARIABLES_0_variable1","value":"<+input>"}]}]}}}]},"environment":{"environmentRef":"demo","deployToAll":false,"infrastructureDefinitions":[{"identifier":"qaauto1"}]}},"tags":{"tag:op":""},"type":"DRTest"}}],"tags":{"module":"drtest"}}}
```

Key points shown in this example:
- **Parallel execution** — `ChaosFault_1` and `ChaosProbe_1` in a `parallel:` block
- **Series execution** — `ChaosAction_1` runs after the parallel block completes
- **ChaosFault** — no `duration` field; runtime variables include `TOTAL_CHAOS_DURATION`
- **ChaosProbe** — has `duration: 10s` at step level
- **ChaosAction** — has `duration: <+input>` (set as runtime by user)
- **`infraReference`** — each step has its own (all use `demo/qaauto1` here, but can differ)
- **`tasks`** — variable values: fixed, empty, or `<+input>` (runtime)
- **`environment` block** — present but not used by DRTest; preserve if fetched, do not ask user for it

---

### Step 3E: Fetch experiment runtime variables

For **Chaos** (Chaos Experiment) steps, use a different endpoint:

`harness_list(resource_type="chaos_experiment_variable", org_id="<org_id>", project_id="<project_id>", filters={"experiment_id": "<selected-experiment-id>"})`, passing `org_id`/`project_id` using the active scope.

The response has two sections:
- `experiment` — experiment-level variables (array of inputs); can be `null` if the experiment has no experiment-level variables
- `tasks` — map of component identity to array of inputs; each key becomes a `tasks[].identifier` in the step YAML

Each entry in `tasks` corresponds to a component (fault, probe, etc.) inside the experiment. Present ALL task groups and their variables to the user. Apply the same **Runtime Variables Workflow** rules below to each variable.

Additional fields to collect for the Chaos step:
- `experimentRef` — the experiment's UUID (not the human-readable identity). Use the `id` field from the experiment selected in Step 2E.
- `expectedResilienceScore` — ask the user. They can provide a fixed integer (0-100), set it as runtime (`<+input>`), or skip it (omit from YAML). This is the minimum resilience score for the step to pass.
- `assertion` — ask the user. They can provide a fixed value, set it as runtime (`<+input>`), or skip it (omit from YAML). This is an optional assertion condition for the experiment.

Chaos steps do NOT have `duration` or `infraReference` at the step level.

#### Chaos step YAML

Example Chaos step (minified JSON for brevity; emit as block-style YAML per `SKILL.md`'s YAML Output Conventions):

```json
[{"step":{"type":"Chaos","name":"Chaos_1","identifier":"Chaos_1","spec":{"experimentRef":"a7c3e1f2-9b4d-4e8a-b6f0-2d5c8a3e7f19","expectedResilienceScore":50,"assertion":"optional assertion field","tasks":[{"identifier":"gcp-vm-service-kill-29m","values":[{"name":"VM_INSTANCE_NAME","value":"req_field_has_fixed_value_set_by_user"},{"name":"SERVICE_NAME","value":"<+input>"},{"name":"ZONE","value":"<+input>"},{"name":"GCP_PROJECT_ID","value":"req_field_has_fixed_value_set_by_user"}]},{"identifier":"new-http-probe-00008-jjp","values":[{"name":"METHOD_GET_RESPONSECODE","value":"200"},{"name":"VARIABLES_0_testRuntime1","value":"<+input>"},{"name":"VARIABLES_1_testR2","value":"as_not_required_can_be_skipped_too"}]}]}}}]
```

Key differences from Probe/Fault/Action steps:
- Uses `experimentRef` (UUID) instead of `identity`
- Has `expectedResilienceScore` and `assertion` (both optional, can be fixed, runtime, or omitted)
- No `duration` or `infraReference`
- `tasks` can have **multiple entries** — one per component in the experiment (each key in the API response `tasks` map becomes a `tasks[].identifier`)
- `tasks` is omitted when the response `tasks` map is empty/null

---

### Runtime Variables Workflow

Applies to all step types that return variables (Probe, Fault, Action, and experiment-level/task-level variables for Chaos).

Each variable has:

| Field | Description |
|---|---|
| `name` | Variable name (e.g., `CRITERIA`, `VM_INSTANCE_NAME`, `DURATION`) |
| `value` | Current value; `"<+input>"` means unresolved runtime placeholder |
| `required` | If `true`, MUST provide a value; if `false`, optional |
| `allowedValues` | If non-null, value must be one of these options |
| `validator` | Regex the value must match (if non-empty) |
| `default` | Suggested value if user does not specify one |
| `type` | Data type: `String`, `Integer`, `Boolean`, `Number` |
| `category` | Grouping hint (e.g., `ActionProperties`, `Variables`) |

Present ALL variables to the user. For each:
- If `required: true` — user MUST supply a value. Do not accept empty.
- If `required: false` — user may leave it empty (use `default` or `""`).
- If `allowedValues` is non-null, value must be one of those options.
- If `validator` is non-empty, value must match that regex.

For each variable, ask the user whether to provide:
- A **fixed value** — an exact value used when the pipeline runs
- A **runtime variable** — assign `<+input>` as the value; the user provides the actual value each time the pipeline runs

Do NOT generate step YAML until all required variables have values.

**Required fields for ALL chaos steps** (except Chaos/experiment):
- `name` — user-provided (from Step Naming and Execution Order)
- `identifier` — derived from name
- `identity` — component identity from Step 2
- `infraReference` — `<environmentId>/<infraId>` from Step 1
- `duration` — **(ChaosProbe and ChaosAction ONLY)** MANDATORY. Must be asked from the user and included in the generated YAML. Must match `^\d+(\.\d+)?(ms|s|m|h)$` (e.g., `"10s"`, `"1m"`, `<+input>`). Do NOT omit this field — the pipeline will be invalid without it.

After the step YAML is built and added to the working pipeline YAML, return to the calling flow's Choose Action hub (`references/create.md` or `references/edit.md`).

---

## Step 4: Save DR Test

After generating the steps YAML, update the DR Test pipeline with these MCP calls in order:

1. **Fetch current pipeline YAML** — Always fetch first since the update is a full-replace PUT that overwrites the entire pipeline: `harness_get(resource_type="pipeline", resource_id="<pipeline_identifier>", org_id="<org_id>", project_id="<project_id>")`

   Check the response's `storeType` field. If `"REMOTE"` (git-backed pipeline), the update call in step 3 below MUST also include `store_type="REMOTE"` plus the git metadata from this same response (`connector_ref`, `repo_name`, `branch`, `file_path`, and `last_object_id`) — omitting them will fail or silently diverge from the linked git file. If `storeType` is `"INLINE"` (the default for DR Tests created via this skill), no extra fields are needed.

2. **Modify the YAML** — Insert the generated steps into the `steps: []` array of the DRTest stage. Do NOT omit any existing fields from the fetched YAML.

3. **Update the pipeline** — Send the full modified YAML back. The exact call depends on the `storeType` checked in step 1:

   - **INLINE** (`storeType` was `"INLINE"` or absent): `harness_update(resource_type="pipeline", resource_id="<pipeline_identifier>", org_id="<org_id>", project_id="<project_id>", body={"yamlPipeline": "<full updated YAML string>"})`

   - **REMOTE** (`storeType` was `"REMOTE"`): `harness_update(resource_type="pipeline", resource_id="<pipeline_identifier>", org_id="<org_id>", project_id="<project_id>", store_type="REMOTE", connector_ref="<connectorRef from step 1's fetch>", repo_name="<repoName from step 1's fetch>", branch="<branch from step 1's fetch>", file_path="<filePath from step 1's fetch>", last_object_id="<lastObjectId from step 1's fetch>", body={"yamlPipeline": "<full updated YAML string>"})` — also include `last_commit_id` if step 1's fetch response returned one.

Pass `org_id`/`project_id` using the active scope (see Scope Rules above) on both calls.

IMPORTANT: This is a full-replace PUT. Any field omitted from the YAML will be erased. Always start from the fetched YAML and apply only the user-requested changes.

### Common Mistakes

- When updating a pipeline that already has chaos steps, preserve all existing `identity`, `infraReference`, and `tasks` values exactly. Do NOT regenerate or guess these IDs.
- DR Test pipelines are tagged `module: drtest` at the pipeline level. Do NOT remove this tag when updating.
- `infraReference` must be `<environmentId>/<infraId>` format (e.g., `demo/qaauto1`). Do NOT use just the infra ID alone.
- Do NOT guess probe identities or infrastructure IDs. Always call `harness_list` with the appropriate `resource_type` to fetch the real values from the user's account.
- Every step `name` and `identifier` within a stage must be unique. Duplicate names cause validation failures.
- Always confirm step execution order (parallel vs series) with the user before generating YAML. Incorrect ordering can cause pipeline failures.

---
To create a new DR Test pipeline from scratch, see `references/create.md`. To modify an existing DR Test pipeline, see `references/edit.md`.
