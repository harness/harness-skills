# Chaos Experiment Components

MANDATORY — Tool Result Verification:
- NEVER claim a tool call succeeded without an explicit success response from the tool.
- NEVER fabricate, assume, or pre-empt tool results. If you called a tool and did not receive a confirmed result, say so and retry.
- When a tool returns a review/elicitation prompt (e.g., "Waiting for user to review before update..."), the user's approval does NOT mean the operation completed. You MUST wait for the follow-up tool response confirming execution before reporting success.
- If the tool response is ambiguous or missing, tell the user honestly and offer to retry.

## Scope Rules

Follow [`references/scope-establishment.md`](../../../references/scope-establishment.md) for establishing org/project scope before calling `harness_list`, `harness_get`, `harness_create`, `harness_update`, or `harness_execute` in this skill:

- Parse `org` / `project` from the user's message or a pasted Harness UI URL first.
- Ask only for what is missing — do not re-ask for values already known.
- Restate the active scope before the first mutating call. Secret lookup below also supports `include_all_secrets_accessible_at_scope` for cross-scope secret discovery — that flag controls secret visibility specifically and still needs `org_id`/`project_id` set to the active scope alongside it.
- Never invent a default org/project. If either is missing, ask the user to select it before calling a project-scoped resource; do not fall back to account scope silently.

## Experiment Components

A chaos experiment combines three types of components in a workflow:

- **Faults** — the disruptions injected into the system. Each fault targets a specific resource (pod, node, VM, cloud service) and has tunables that control blast radius and behavior. Examples: pod-delete, pod-cpu-hog, node-drain, gcp-vm-service-kill, network-latency. **At least one fault is required** for a valid experiment.
- **Probes** — hypothesis validators that check whether the system survived correctly. They run during the experiment to assert expected behavior. Types: HTTP (check endpoint responses), CMD (run shell commands), Prometheus (query metrics), Kubernetes (check k8s resource state), Datadog (assert APM metrics). Probes are optional.
- **Actions** — operational steps beyond fault injection. Types: Delay (time delays between phases), Custom Script (run setup/validation/cleanup), Container (run commands in containers). Actions are optional.

An experiment can contain any number of faults, probes, and actions **in any order**. The user can keep adding components at any position in the workflow. The `vertices` array in the YAML defines the execution sequence.

## When to use this reference

This file is the canonical how-to for adding, configuring, and removing components inside a Chaos Experiment YAML manifest. Read it from Step 6 of `references/create.md` or `references/edit.md`.

It assumes the working YAML is already scaffolded with `spec.infraId`, `spec.infraType`, and (for K8s) `metadata.namespace` and `spec.serviceAccountName` set. If you arrived here without a scaffolded YAML:

- To create a new experiment -> follow `references/create.md`.
- To edit an existing experiment -> follow `references/edit.md`.
- For pure reference questions (fault tunables, vertices wiring, probe YAML) -> answer from this file.

After completing an add/remove operation, return to the calling flow's Step 6 hub (`references/create.md` or `references/edit.md`) so the user can add another component or save.

## Naming Conventions

When adding a fault, probe, or action to the experiment, generate a unique `name` by appending `-` plus a random 3-character lowercase string to the component's identity. Examples:
- Fault identity `gcp-vm-service-kill` -> name `gcp-vm-service-kill-anw`
- Probe identity `new-http-probe-0008` -> name `new-http-probe-0008-8t9`
- Action identity `test-action-008` -> name `test-action-008-16n`

Vertex names use `v-` prefix plus a random 3-character string (e.g., `v-ape`, `v-8vi`). The last vertex in the workflow is always named `v-end`.

## On MCP Tool Failure

If any `harness_list`, `harness_get`, or `harness_execute` call in this skill fails, report the error to the user verbatim (tool name + message) and stop. Do NOT invent fault / probe / action identities, variables, or infrastructures — every value must come from a successful MCP response or the user.

## YAML Validation Rules

Before presenting experiment YAML to the user, ALWAYS validate it against these rules. If any rule is violated, fix the YAML silently before showing it.

1. **No duplicate keys** — each of `faultRef`, `probeRef`, `actionRef`, `vertices`, `infraId`, `infraType`, `serviceAccountName`, `cleanupPolicy`, `experimentId`, `experimentRunId` must appear **exactly once** under `spec`. If a key appears more than once, merge the entries into a single key.
2. **Component ref arrays** — `faultRef`, `probeRef`, and `actionRef` can appear in any order under `spec`. Each must appear **exactly once** — as a populated array or as an empty array (`[]`). Never duplicate.
3. **Vertices last** — `vertices` should be the last key under `spec`, after all ref arrays and scalar fields.
4. **One vertex per connection** — each vertex name must be unique. The last vertex is always `v-end`.
5. **Component names match** — every name referenced in `vertices` (`start.faults`, `start.probes`, `start.actions`, `end.faults`, `end.probes`, `end.actions`) must correspond to exactly one entry in the matching ref array (`faultRef`, `probeRef`, `actionRef`), and vice versa.
6. **No orphan refs** — every entry in `faultRef`, `probeRef`, and `actionRef` must be wired into `vertices`. No component should exist in a ref array without appearing in the workflow.
7. **No blank lines** — the generated YAML must be compact with no empty lines anywhere. Do not add blank lines between top-level blocks (`metadata` and `spec`), between fields inside `spec`, between array items in `faultRef`/`probeRef`/`actionRef`/`vertices`, or anywhere else. Every line must contain YAML content or indentation-only continuation — never an empty line.
8. **Output style** — always emit block-style YAML (each key on its own line, list items on their own line with `-`, children indented). The reference examples throughout this skill are minified JSON purely for token efficiency — JSON parses identically to YAML, so the examples remain authoritative for field names and structure, but the manifest you work with and show the user MUST be block-style YAML matching the Step 5 scaffold. Only when calling `harness_create`/`harness_update` (Step 9a in `references/create.md` / `references/edit.md`) do you convert this YAML to a compact JSON string for the `manifest` request field — never send raw YAML or a pretty-printed JSON object as the request body.

## Adding a Fault to the Experiment

### Step 6F: List faults — user selects one

Set `is_enterprise` from the user's Step 6 choice:

- "**enterprise fault**" -> `true`
- "**custom fault**" -> `false`
- just "**fault**" (no qualifier) -> default to `true`

Store this boolean as `selected_is_enterprise` and reuse it for variable lookup and the final `faultRef` entry.

Call: `harness_list(resource_type="chaos_fault", org_id="<org_id>", project_id="<project_id>", filters={"is_enterprise": <true|false>, "infrastructure": "<KubernetesV2 | Linux | Windows>"})` where `infrastructure` matches the user's Step 1a choice (`Kubernetes` -> `KubernetesV2`, `Linux` -> `Linux`, `Windows` -> `Windows`). Pass `org_id`/`project_id` using the active scope established per Scope Rules above. Do NOT use the `infrastructure_type` filter — the upstream backend only honors `Kubernetes` for that field.

Present the fault names, identities, and categories. **Always state which set this is** — e.g. "Here are the **enterprise** faults available for `<infraType>`. If you want a **custom** fault from your project instead, just say so." (Or vice versa when `is_enterprise=false`.) If the user asks to switch, re-run the call with the flipped value.

### Step 7F: Fetch fault runtime variables — user fills required values

Call `harness_execute(resource_type="chaos_fault", action="get_variables", resource_id="<fault_identity>", org_id="<org_id>", project_id="<project_id>", params={"is_enterprise": <selected_is_enterprise>})`, passing `org_id`/`project_id` using the active scope established per Scope Rules above.

This maps to `GET /rest/faults/{faultId}/variables`. The response has THREE arrays the agent must handle:

- `inputs` — fault tunables (the rest of this step). Each variable has `name`, `description`, `required`, `default`, `allowedValues`, and `validator`.
- `faultTargets` — KubernetesV2-only target-application fields (`TARGET_WORKLOAD_KIND`, `TARGET_WORKLOAD_NAMESPACE`, `TARGET_WORKLOAD_NAMES`, `TARGET_WORKLOAD_LABELS`). Handled in **Step 7F.1** below. Skip 7F.1 entirely if `faultTargets` is empty or absent (true for all Linux/Windows faults and many K8sV2 faults).
- `faultAuthentication` — secret credentials required by the fault (e.g. Redis password, TLS file). Each entry carries the same metadata fields as `inputs` (`name`, `required`, `allowedValues`, `validator`, etc.) plus a `type` field of either `SecretText` or `SecretFile`. Handled in **Step 7F.2** below. Skip 7F.2 entirely if `faultAuthentication` is absent or empty.

For each variable, ask the user whether they want to provide:
- A **fixed value** — an exact value used when the experiment runs
- A **runtime variable** — assign `<+input>` as the value; the user will provide the actual value each time the experiment is run

Present ALL variables to the user. Rules:
- If `required: true` — user MUST either supply a fixed value or mark it as runtime (`<+input>`). Do not leave it unset.
- If `required: false` — user may leave it empty (use `default` or `""`).
- If `allowedValues` is non-null, value must be one of those options.
- If `validator` is non-empty, value must match that regex.

Do NOT proceed to Step 7F.1 / 7F.2 until all required `inputs` variables have values or are marked as runtime.

### Step 7F.1: Target Application — KubernetesV2 fault targets

**Trigger guard** — only run this substep when ALL are true:
- The user's Step 1a choice was `Kubernetes` (i.e. `infraType` is `KubernetesV2`).
- The Step 7F `get_variables` response contains a `faultTargets` array that is non-empty.

Otherwise, skip directly to Step 8F.

The four target fields are populated from a mix of a hardcoded list and two Service Discovery (SD) MCP calls. Use these inputs from earlier steps:

- `agent_identity` = the short `infraID` from Step 2 (e.g. `chaosinfra` or `qaauto1`), NOT the `<envId>/<infraId>` composite used at `spec.infraId`. The Service Discovery agent is created with the same identity as the chaos infra and is reachable at `/agents/{infraID}/...`.
- `environment_id` = the `environmentID` from Step 1b (e.g. `dev`, `demo`).

Both are required — SD endpoints return 404 if either is wrong.

#### Field handlers

For each entry in `faultTargets`, dispatch by `name`:

**`TARGET_WORKLOAD_KIND`** — hardcoded dropdown, no tool call. Present exactly these five values (lowercase, in this order): `deployment`, `statefulset`, `daemonset`, `deploymentconfig`, `rollout`.

**`TARGET_WORKLOAD_NAMESPACE`** — call:

`harness_list(resource_type="discovered_namespace", org_id="<org_id>", project_id="<project_id>", filters={"agent_identity": "<infraID>", "environment_id": "<environmentID>", "all": true})`, passing `org_id`/`project_id` using the active scope established per Scope Rules above.

Present `items[].name` as the dropdown.

**`TARGET_WORKLOAD_NAMES` and `TARGET_WORKLOAD_LABELS`** — these two fields are handled together. Defer until the user has picked `TARGET_WORKLOAD_NAMESPACE`, then make ONE call:

`harness_list(resource_type="discovered_service", org_id="<org_id>", project_id="<project_id>", filters={"agent_identity": "<infraID>", "environment_id": "<environmentID>", "namespace": "<chosen_namespace>", "all": true}, compact=false)`, passing `org_id`/`project_id` using the active scope established per Scope Rules above.

`compact=false` is **mandatory** — the workloads and labels live in `spec.kubernetes.*`, which the default compact mode silently strips.

Cache the full response for reuse.

**Ask the user how they want to identify the target workload:**

> How do you want to identify the target workload?
> 1. **By name only** — target an exact workload; no label selector
> 2. **By labels only** — match any workload carrying these labels; no name required
> 3. **By both** — target an exact workload AND confirm it carries specific labels (both values are derived from the same workload)
> 4. **Runtime** — I'll supply the values at run time (`<+input>`)
> 5. **Skip** — leave both fields empty *(only shown when both `TARGET_WORKLOAD_NAMES.required` and `TARGET_WORKLOAD_LABELS.required` are `false`)*

Handle each mode:

**Mode 1 — Name only:** Collect `item.spec.kubernetes.workloads[].identity.name` across all items; de-duplicate. Present as the `TARGET_WORKLOAD_NAMES` dropdown. Set `TARGET_WORKLOAD_LABELS` = `""`.

**Mode 2 — Labels only:** Collect every `<key>=<value>` pair from `item.spec.kubernetes.workloads[].labels` across all items; de-duplicate. Present as the `TARGET_WORKLOAD_LABELS` dropdown. Set `TARGET_WORKLOAD_NAMES` = `""`.

**Mode 3 — Both (name + consistent labels):** Build a combined dropdown: for every workload in the response emit one row per label as `<workload-name> & <key>=<value>`. Rows are grouped by workload — labels from workload A are never paired with the name of workload B. Present these combined rows to the user.

From the chosen row, split: the part before ` & ` becomes `TARGET_WORKLOAD_NAMES`; the part after becomes `TARGET_WORKLOAD_LABELS`. This ensures both values always describe the same workload and can never contradict at runtime.

Workloads that carry zero labels are excluded from Mode 3.

If two workloads share the same name across different kinds (e.g. a Deployment and a StatefulSet both named `chaos-exporter`), qualify each row with its kind: `chaos-exporter [Deployment] & app=chaos-exporter`. Picking such a row also pins `TARGET_WORKLOAD_KIND` to that kind if the user has not already set it.

**Mode 4 — Runtime:** Set `TARGET_WORKLOAD_NAMES` = `<+input>` and `TARGET_WORKLOAD_LABELS` = `<+input>`. Skip the dropdown entirely. The user may also choose runtime for just one of the two fields (e.g. name fixed, labels runtime) — accept that as a valid answer.

**Mode 5 — Skip:** Only offer this option when BOTH `TARGET_WORKLOAD_NAMES.required` and `TARGET_WORKLOAD_LABELS.required` are `false`. Set both to `""`. If only one of the two fields has `required: false`, the user may skip that individual field but must still supply a value for the required one — in that case only the required field gets a dropdown (Mode 1, 2, or 4 as appropriate).

Example `discovered_service` item (truncated to the relevant fields):

```json
{"name":"chaos-exporter","spec":{"kubernetes":{"workloads":[{"identity":{"kind":"Deployment","name":"chaos-exporter","namespace":"hce"},"labels":{"app":"chaos-exporter","release":"prometheus-stack"}}]}}}
```

For Mode 3 this item produces two rows:
- `chaos-exporter & app=chaos-exporter`
- `chaos-exporter & release=prometheus-stack`

#### Cascade reset

`KIND` is independent. The chain is `NAMESPACE -> (NAMES + LABELS)`.

- Change `TARGET_WORKLOAD_NAMESPACE` — re-issue the `discovered_service` call against the new namespace and clear `TARGET_WORKLOAD_NAMES` and `TARGET_WORKLOAD_LABELS` (unless either is `<+input>`). Re-ask the targeting-mode question.
- Change targeting mode (user switches from e.g. Mode 1 to Mode 3) — clear `TARGET_WORKLOAD_NAMES` and `TARGET_WORKLOAD_LABELS` and re-present the appropriate dropdown using the cached response.
- `TARGET_WORKLOAD_KIND` — no cascade. If KIND changes after Mode 3 labels are set, surface a warning that the kind may no longer match the chosen workload and offer to re-pick.

#### Fixed vs runtime

Same UX as Step 7F: for each target, the user may supply a fixed value, mark it as runtime (`<+input>`), or — only when `required: false` — leave empty. Apply the same `allowedValues` and `validator` rules as Step 7F.

#### Output

Append the chosen `{name, value}` pairs to the same `values` array that Step 7F builds. The combined array is consumed by Step 8F's `faultRef` entry. Example for a `pod-delete` fault on the `chaosinfra` infra, where the user chose Mode 3 and picked `chaos-exporter & release=prometheus-stack`:

```json
{"faultRef":[{"authEnabled":false,"identity":"pod-delete","infraId":"chaosinfra","isEnterprise":true,"name":"pod-delete-n38","values":[{"name":"TARGET_WORKLOAD_KIND","value":"deployment"},{"name":"TARGET_WORKLOAD_NAMESPACE","value":"hce"},{"name":"TARGET_WORKLOAD_NAMES","value":"chaos-exporter"},{"name":"TARGET_WORKLOAD_LABELS","value":"release=prometheus-stack"}]}]}
```

If the same fault also has `inputs` (e.g. `TOTAL_CHAOS_DURATION`), those entries are appended to the same `values` array, after the target entries.

Do NOT proceed to Step 8F until every required `faultTargets` entry has a fixed value or is marked as runtime.

### Step 7F.2: Fault Authentication — secrets for the fault

**Trigger guard** — only run this substep when `faultAuthentication` in the `get_variables` response is non-empty. Otherwise, skip directly to Step 8F.

For each entry in `faultAuthentication`, dispatch by `type`:

#### `SecretText`

Ask the user whether they want to use **Plain Text** or **Encrypted**:
- **Plain Text** — user types the value directly; stored verbatim. No MCP call.
- **Encrypted** — follow **Step 7F.2.S** below with `type="SecretText"`.

The user may also choose **Runtime** (`<+input>`) or **Skip** (only when `required: false`).

#### `SecretFile`

Follow **Step 7F.2.S** below with `type="SecretFile"`.

The user may also choose **Runtime** (`<+input>`) or **Skip** (only when `required: false`).

#### Step 7F.2.S: Fetch and select a secret

Call:

`harness_list(resource_type="secret", org_id="<org_id>", project_id="<project_id>", filters={"type": "<SecretText|SecretFile>", "include_all_secrets_accessible_at_scope": true})`, passing `org_id`/`project_id` using the active scope established per Scope Rules above.

Present the returned secrets (name + identifier) as a dropdown. Once the user selects one, derive the stored value from the secret object's scope fields:

| `orgIdentifier` present | `projectIdentifier` present | Stored value |
|---|---|---|
| No | No | `secrets.getValue("account.<identifier>")` |
| Yes | No | `secrets.getValue("org.<identifier>")` |
| Yes | Yes | `secrets.getValue("<identifier>")` |

#### Rules (same as Step 7F)

- `required: true` — user MUST supply a value or mark as runtime. Do not leave unset.
- `required: false` — user may leave empty.
- `allowedValues` non-null — value must be one of those options.
- `validator` non-empty — value must match that regex.

Do NOT proceed to Step 8F until all required `faultAuthentication` entries have a fixed value or are marked as runtime.

### Step 8F: Add fault to experiment YAML

Using the fault identity from Step 6F, generate a unique name (identity + random 3-char suffix), and add an entry to `faultRef` with the variable values from Step 7F.

Each `faultRef` entry has:
- `authEnabled` — `true` if the `faultAuthentication` array from Step 7F was non-empty (i.e. the `get_variables` response contained any `faultAuthentication` entries, regardless of whether they were filled or skipped as optional); `false` otherwise
- `identity` — fault identity from Step 6F
- `infraId` — for Kubernetes: the short infra ID (e.g., `qaauto1`), NOT the `<envId>/<infraId>` form used at `spec.infraId`. For Linux/Windows: the same UUID used at `spec.infraId`.
- `isEnterprise` — use `selected_is_enterprise` from Step 6F (`true` for enterprise faults, `false` for custom faults)
- `name` — fault identity + `-` + random 3 chars (e.g., `gcp-vm-service-kill-anw`)
- `values` — array of `{name, value}` pairs. Use `<+input>` for runtime variables, or the exact value for fixed variables. Build the array in this order:
  1. `TARGET_WORKLOAD_*` entries from Step 7F.1 (KubernetesV2 only, omit if `faultTargets` was empty/absent)
  2. `inputs` entries from Step 7F
  3. `faultAuthentication` entries from Step 7F.2 (omit if absent/empty)

Also update `vertices` to wire the fault into the workflow (see Vertices section below).

Updated enterprise-fault experiment manifest (continuing the `test-exp-007` example with `gcp-vm-service-kill`, user marked most variables as runtime, and gave `TOTAL_CHAOS_DURATION` a value of `10`). Shown as minified JSON for token brevity — emit as block-style YAML per Rule §8:

```json
{"apiVersion":"litmuschaos.io/v1beta1","kind":"ChaosExperiment","metadata":{"name":"test-exp-007","namespace":"hce"},"spec":{"cleanupPolicy":"delete","experimentId":"073eea9a-3743-48c2-b600-c09d871054c7","experimentRunId":"","faultRef":[{"authEnabled":false,"identity":"gcp-vm-service-kill","infraId":"qaauto1","isEnterprise":true,"name":"gcp-vm-service-kill-anw","values":[{"name":"VM_INSTANCE_NAME","value":"<+input>"},{"name":"SERVICE_NAME","value":"<+input>"},{"name":"VM_USERNAME","value":"<+input>"},{"name":"ZONE","value":"<+input>"},{"name":"GCP_PROJECT_ID","value":"<+input>"},{"name":"TOTAL_CHAOS_DURATION","value":10}]}],"infraId":"demo/qaauto1","infraType":"KubernetesV2","serviceAccountName":"litmus","vertices":[{"name":"v-ape","start":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}},{"name":"v-end","end":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}}],"probeRef":[],"actionRef":[]}}
```

Return to **Step 6** to add another component (fault, probe, or action) or finish the experiment.

After this step completes, return to the calling flow's Step 6 hub (`references/create.md` or `references/edit.md`) so the user can add another component or save.

## Adding a Probe to the Experiment

Probes validate that the system behaves correctly during and after fault injection. They are optional — an experiment can have zero or more probes.

Probe types: HTTP, CMD, Prometheus, K8S, Datadog, Dynatrace, SLO, APM, and Container. See Step 6P for the full list with `entity_type` filters.

### Step 6P: List probes — user selects one or more

Ask the user which probe type they want, or All:

Choose a type and pass it as `entity_type` in the MCP call (omit for All): HTTP Probe (`httpProbe`), Command Probe (`cmdProbe`), Datadog Probe (`datadogProbe`), Dynatrace Probe (`dynatraceProbe`), K8S Probe (`k8sProbe`), Prometheus Probe (`promProbe`), SLO Probe (`sloProbe`), APM Probe (`apmProbe`), Container Probe (`containerProbe`).

Set `infra_type` from the user's Step 1a choice (`Kubernetes` -> `KubernetesV2`, otherwise `Linux` or `Windows` literally).

If user picks a specific type: `harness_list(resource_type="chaos_probe", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<KubernetesV2 | Linux | Windows>", "entity_type": "<value>"})`

If user picks All (or does not specify): `harness_list(resource_type="chaos_probe", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<KubernetesV2 | Linux | Windows>"})`

Pass `org_id`/`project_id` using the active scope established per Scope Rules above. Only present probes where `isEnabled: true`. Present `identity`, `name`, and `type` to the user.

### Step 7P: Get probe variables — user fills required values

`harness_get(resource_type="chaos_probe", resource_id="<probe_identity>", org_id="<org_id>", project_id="<project_id>")`

This maps to `GET /rest/v2/probes/{probeId}`. The response contains two variable arrays:

- **`inputs`** — variables derived from probe properties that need user input (e.g., `METHOD_GET_RESPONSECODE`). Use their `name` field directly in the YAML `values` array.
- **`variables`** — user-defined custom variables added when the probe was created (e.g., `tempVar1`). In the YAML `values` array, use the naming convention `VARIABLES_<index>_<variableName>` (e.g., `VARIABLES_0_tempVar1`, `VARIABLES_1_testR2`).

For each variable, ask the user whether they want to provide:
- A **fixed value** — an exact value used when the experiment runs
- A **runtime variable** — assign `<+input>` as the value; the user will provide the actual value each time the experiment is run

Rules:
- If `required: true` — user MUST either supply a fixed value or mark it as runtime (`<+input>`). Do not leave it unset.
- If `required: false` — user may leave it empty (use `default` or `""`).

Also ask the user for two additional probe-level fields:
- **`duration`** — how long the probe runs. Default `30s`. Must match `^\d+(\.\d+)?(ms|s|m|h)$` (e.g., `10s`, `1m`, `500ms`). Cannot be a runtime variable. Validate before generating YAML.
- **`weightage`** — integer from 1 to 10. Default `10`. Cannot be a runtime variable.

Do NOT proceed to Step 8P until all required variables have values or are marked as runtime, and duration/weightage are valid.

### Step 8P: Add probe to experiment YAML

Using the probe identity from Step 6P, generate a unique name (identity + random 3-char suffix), and add an entry to `probeRef` with the variable values from Step 7P.

Each `probeRef` entry has:
- `duration` — string, default `"30s"`, validated against regex
- `identity` — probe identity from Step 6P
- `infraId` — for Kubernetes: the short infra ID (e.g., `qaauto1`), NOT the `<envId>/<infraId>` form used at `spec.infraId`. For Linux/Windows: the same UUID used at `spec.infraId`.
- `name` — probe identity + `-` + random 3 chars (e.g., `new-http-probe-0008-oqb`)
- `values` — array of `{name, value}` pairs merged from both sources:
  - From `inputs`: use `name` directly (e.g., `METHOD_GET_RESPONSECODE`)
  - From `variables`: use `VARIABLES_<index>_<variableName>` (e.g., `VARIABLES_0_tempVar1`)
- `weightage` — integer, default `10`, max `10`

Also update `vertices` to wire the probe into the workflow (see Vertices section below).

Updated experiment manifest (continuing the `test-exp-007` example, adding probe `new-http-probe-0008` after the existing fault, user marked `METHOD_GET_RESPONSECODE` as runtime). Shown as a diff from the §Step 8F manifest above; emit the final result as block-style YAML per Rule §8:

```text
Diff vs §Step 8F:
  + spec.probeRef[]: NEW entry for probe `new-http-probe-0008`
  ~ spec.vertices:   replaced — now [v-ape, v-8vi (NEW), v-end]; v-end's end-ref switched from fault to probe
  = unchanged: apiVersion, kind, metadata, spec.{cleanupPolicy, experimentId, experimentRunId, faultRef, infraId, infraType, serviceAccountName, actionRef}
```

```json
{"probeRef":[{"duration":"30s","identity":"new-http-probe-0008","infraId":"qaauto1","name":"new-http-probe-0008-oqb","weightage":10,"values":[{"name":"METHOD_GET_RESPONSECODE","value":"<+input>"}]}]}
```

```json
{"vertices":[{"name":"v-ape","start":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}},{"name":"v-8vi","end":{"faults":[{"name":"gcp-vm-service-kill-anw"}]},"start":{"probes":[{"name":"new-http-probe-0008-oqb"}]}},{"name":"v-end","end":{"probes":[{"name":"new-http-probe-0008-oqb"}]}}]}
```

Return to **Step 6** to add another component (fault, probe, or action) or finish the experiment.

After this step completes, return to the calling flow's Step 6 hub (`references/create.md` or `references/edit.md`) so the user can add another component or save.

## Adding an Action to the Experiment

Actions are operational steps beyond fault injection — delays, custom scripts, or container commands. They are optional.

Action types: Delay (`delay`), Custom Script (`customScript`), Container (`container`).

### Step 6A: List actions — user selects one

Ask the user which action type they want, or All:

Choose a type and pass it as `entity_type` in the MCP call (omit for All): Delay (`delay`), Custom Script (`customScript`), Container (`container`).

Set `infra_type` from the user's Step 1a choice (`Kubernetes` -> `KubernetesV2`, otherwise `Linux` or `Windows` literally).

If user picks a specific type: `harness_list(resource_type="chaos_action", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<KubernetesV2 | Linux | Windows>", "entity_type": "<value>"})`

If user picks All (or does not specify): `harness_list(resource_type="chaos_action", org_id="<org_id>", project_id="<project_id>", filters={"infra_type": "<KubernetesV2 | Linux | Windows>"})`

Pass `org_id`/`project_id` using the active scope established per Scope Rules above. Present `identity`, `name`, `type`, and `description` to the user and ask them to pick one.

### Step 7A: Get action variables — user fills required values

`harness_get(resource_type="chaos_action", resource_id="<action_identity>", org_id="<org_id>", project_id="<project_id>")`

This maps to `GET /rest/actions/{actionId}`. The response contains two variable arrays:

- **`inputs`** — variables derived from action properties and user-defined variables whose value is `<+input>`. Each has `name`, `value`, `path`, `category`, `description`, `required`, `allowedValues`, `default`, and `validator`. Use the `name` field directly in the YAML `values` array.
- **`variables`** — user-defined custom variables added when the action was created. Already represented in `inputs` as `VARIABLES_<index>_<name>`. Show `variables` for context/descriptions but use the `inputs` array names for YAML.

For each input, ask the user whether they want to provide:
- A **fixed value** — an exact value used when the experiment runs
- A **runtime variable** — assign `<+input>` as the value; the user will provide the actual value each time the experiment is run

Rules:
- If `required: true` — user MUST either supply a fixed value or mark it as runtime (`<+input>`). Do not leave it unset.
- If `required: false` — user may leave it empty (use `default` or `""`).
- If `allowedValues` is non-null, value must be one of those options.
- If `validator` is non-empty, value must match that regex.

Do NOT proceed to Step 8A until all required variables have values or are marked as runtime.

### Step 8A: Add action to experiment YAML

Using the action identity from Step 6A, generate a unique name (identity + random 3-char suffix), and add an entry to `actionRef` with the variable values from Step 7A.

Each `actionRef` entry has:
- `identity` — action identity from Step 6A
- `name` — action identity + `-` + random 3 chars (e.g., `test-action-008-16n`)
- `continueOnCompletion` — always `false`
- `values` — array of `{name, value}` pairs from `inputs` in Step 7A. Use `<+input>` for runtime variables, or the exact value for fixed variables.
- `infraId` — for Kubernetes: the short infra ID (e.g., `qaauto1`), NOT the `<envId>/<infraId>` form used at `spec.infraId`. For Linux/Windows: the same UUID used at `spec.infraId`.

Also update `vertices` to wire the action into the workflow (see Vertices section below).

Updated experiment manifest (continuing the `test-exp-007` example, adding action `test-action-008` after the existing fault and probe, user gave `DURATION` a fixed value of `10` and `VARIABLES_0_variable1` a fixed value of `20`). Shown as a diff from the §Step 8P manifest above; emit the final result as block-style YAML per Rule §8:

```text
Diff vs §Step 8P:
  + spec.actionRef[]: NEW entry for action `test-action-008`
  ~ spec.vertices:    replaced — now [v-ape, v-8vi, v-18p (NEW), v-end]; v-end's end-ref switched from probe to action
  = unchanged: apiVersion, kind, metadata, spec.{cleanupPolicy, experimentId, experimentRunId, faultRef, probeRef, infraId, infraType, serviceAccountName}
```

```json
{"actionRef":[{"identity":"test-action-008","name":"test-action-008-16n","continueOnCompletion":false,"infraId":"qaauto1","values":[{"name":"DURATION","value":"10"},{"name":"VARIABLES_0_variable1","value":"20"}]}]}
```

```json
{"vertices":[{"name":"v-ape","start":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}},{"name":"v-8vi","start":{"probes":[{"name":"new-http-probe-0008-oqb"}]},"end":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}},{"name":"v-18p","start":{"actions":[{"name":"test-action-008-16n"}]},"end":{"probes":[{"name":"new-http-probe-0008-oqb"}]}},{"name":"v-end","end":{"actions":[{"name":"test-action-008-16n"}]}}]}
```

Return to **Step 6** to add another component (fault, probe, or action) or finish the experiment.

After this step completes, return to the calling flow's Step 6 hub (`references/create.md` or `references/edit.md`) so the user can add another component or save.

## Removing a Component (Edit Mode Only)

List every component currently in the working YAML grouped by type:

> **Faults:**
> 1. `<name>` (identity: `<identity>`)
> 2. ...
>
> **Probes:**
> 1. `<name>` (identity: `<identity>`)
> 2. ...
>
> **Actions:**
> 1. `<name>` (identity: `<identity>`)
> 2. ...
>
> Which component would you like to remove?

After the user picks one:

1. Remove the entry from the corresponding ref array (`faultRef`, `probeRef`, or `actionRef`).
2. Find every vertex in `vertices` that references the removed component's `name` (in `start.faults`, `start.probes`, `start.actions`, `end.faults`, `end.probes`, or `end.actions`).
3. Remove the component's name from those vertex lists.
4. If a vertex's `start` and `end` lists are ALL empty after removal (i.e., it references no remaining components), remove the entire vertex and re-wire: connect the preceding vertex's output to the next vertex's input.
5. Validate the YAML against the rules in "YAML Validation Rules" (especially rule 5: component names match, and rule 6: no orphan refs).

**Guard: at least one fault must remain.** If the user tries to remove the last fault, block with: "An experiment must have at least one fault. To remove this fault, add a replacement first." (This enforces the existing rule in the "Step 6: Choose component to add/update" section.)

After removal, return to Step 6.

Return to `references/edit.md`'s Step 6 hub after the removal.

## Vertices — Wiring the Experiment Workflow

The `vertices` array defines execution order in the experiment. Each vertex represents a connection point (the `+` nodes in the visual workflow).

Components (faults, probes, actions) can be added **in any order** and at **any position** in the workflow. When adding a new component, insert new vertices at the desired position — it does not have to be appended at the end.

**Parallel vs series**: components sharing one vertex's `start` (or `end`) run **in parallel** — across types (`faults` + `probes`) and across multiple items under each type. Components in **different sequential vertices** run **in series**. Ask the user which they want before adding a new component.

Rules:
- Each vertex has a `name`: `v-<3-random-chars>` (e.g., `v-ape`, `v-8vi`)
- The **last** vertex is always named `v-end`
- `start` — references the fault/probe/action immediately **after** this vertex
- `end` — references the fault/probe/action immediately **before** this vertex
- The **first** vertex has only `start` (nothing before it)
- The **last** vertex (`v-end`) has only `end` (nothing after it)
- **Middle** vertices have both `end` and `start`
- A vertex's `start` or `end` can contain multiple keys (`faults`, `probes`, `actions`) and multiple items under each key — all run in parallel

### Examples

Both examples are shown as minified JSON for token efficiency. The manifest sent to the backend MUST be block-style YAML (Rule §8 in YAML Validation Rules).

#### V1 — Minimum: 1 component in series

Workflow: `[+] -> FAULT -> [+]`. First vertex has only `start`, last vertex (`v-end`) has only `end`, both reference the same component name. To extend in series, insert middle vertices carrying BOTH `start` (next component) and `end` (previous component).

```json
{"vertices":[{"name":"v-ape","start":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}},{"name":"v-end","end":{"faults":[{"name":"gcp-vm-service-kill-anw"}]}}]}
```

#### V2 — Mixed parallel and series

Workflow: `[+] -> (FAULT1 || (PROBE -> [+] -> ACTION)) -> [+] -> FAULT2 -> [+]`.

FAULT1 runs in parallel with a PROBE -> ACTION chain. When both branches complete, FAULT2 runs in series. The four vertices play these roles:

- **`v-r3p`** — parallel start: FAULT1 and PROBE begin at the same vertex (parallel within a vertex; multiple type keys under one `start`).
- **`v-18p`** — series inside the probe branch: PROBE ends, ACTION starts (`end` and `start` both populated, one component each).
- **`v-wk5`** — join + series-after-parallel: ACTION and FAULT1 both end here (multi-entry `end`), then FAULT2 starts.
- **`v-end`** — terminator: only `end` populated.

```json
{"vertices":[{"name":"v-r3p","start":{"faults":[{"name":"gcp-vm-service-kill-k7m"}],"probes":[{"name":"new-http-probe-0008-f4j"}]}},{"name":"v-18p","end":{"probes":[{"name":"new-http-probe-0008-f4j"}]},"start":{"actions":[{"name":"test-action-008-16n"}]}},{"name":"v-wk5","end":{"actions":[{"name":"test-action-008-16n"}],"faults":[{"name":"gcp-vm-service-kill-k7m"}]},"start":{"faults":[{"name":"node-cpu-hog-zp9-wi6"}]}},{"name":"v-end","end":{"faults":[{"name":"node-cpu-hog-zp9-wi6"}]}}]}
```

The `start`/`end` keys use `faults`, `probes`, or `actions` depending on the component type referenced. Multiple keys can appear under a single `start`/`end` (all run in parallel); multiple entries under one key are also parallel.

#### Pattern reference

| Pattern needed                                  | Where to look                                       |
|---|---|
| Pure series of N components (any types)         | V1, repeat the middle-vertex pattern                |
| Parallel of multiple types in one vertex        | V2, `v-r3p` (`faults` + `probes` together)          |
| Parallel of multiple items of the same type     | V2, `v-r3p` — add more entries to `faults: [...]`   |
| Series chain inside a parallel branch           | V2, `v-r3p` -> `v-18p` (probe -> action)            |
| Series after a parallel group (join)            | V2, `v-wk5` (joins ACTION + FAULT1, starts FAULT2)  |
| Terminator-only vertex                          | V2, `v-end` (also V1)                               |

---
To start a new experiment from scratch, see `references/create.md`. To modify an existing experiment, see `references/edit.md`.
