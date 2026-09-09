---
name: chaos-experiment
description: >-
  Use when the user asks to create, edit, update, design, or configure a Harness Chaos
  Experiment — including faults, probes, actions, experiment YAML, fault injection,
  pod-delete, or resilience tests. Do not use for Chaos steps inside a pipeline or a
  DRTest stage; use chaos-dr-test for those. Do not use to run an experiment, list past
  runs, or inspect run results — call the Chaos MCP tools directly for those (see
  Performance Notes). Trigger phrases: chaos experiment, chaos engineering, resilience
  test, fault injection, pod-delete, chaos hub template.
metadata:
  author: Harness
  version: 3.0.0
  mcp-server: harness-mcp-v2
  module: CHAOS
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Chaos Experiment

Create, edit, and answer reference questions about Harness Chaos Experiments — faults,
probes, actions, and the underlying `ChaosExperiment` manifest — via MCP.

MANDATORY — Tool Result Verification:
- NEVER claim a tool call succeeded without an explicit success response from the tool.
- NEVER fabricate, assume, or pre-empt tool results. If you called a tool and did not receive a confirmed result, say so and retry.
- When a tool returns a review/elicitation prompt (e.g., "Waiting for user to review before update..."), the user's approval does NOT mean the operation completed. You MUST wait for the follow-up tool response confirming execution before reporting success.
- If the tool response is ambiguous or missing, tell the user honestly and offer to retry.

## Instructions

### Step 1: Establish scope

Before any `harness_list`, `harness_get`, `harness_create`, `harness_update`, or
`harness_execute` call in this skill, establish org/project scope using the repo-wide
playbook at [`references/scope-establishment.md`](../../references/scope-establishment.md):

- Parse `org` / `project` from the user's message or a pasted Harness UI URL first.
- Ask only for what is missing — do not re-ask for values already known.
- Restate the active scope (e.g. `org=default, project=payments`) before the first
  mutating call.
- Never assume a default org/project unless the user explicitly confirms it.

### Step 2: Route before acting

Choose the first matching entry route below. Read that entry file first; it may direct
you to read additional shared references later.

- **Reference question** — the user asks how a fault, probe, action, target workload, tunable, vertex, manifest field, or YAML structure works, without asking to create or modify an experiment: Read `references/components.md`. No scaffolded YAML is required for a reference-only answer.
- **Existing experiment** — the user explicitly asks to edit, update, modify, change, rename, fix, remove from, or add to an existing experiment, says the experiment already exists, or provides an existing experiment UUID: Read `references/edit.md`. Preserve `experimentId` and `identity`. Do not generate a new UUID. Saving an edit reuses `harness_create` as an upsert — `chaos_experiment` has no separate update operation; do not call `harness_update` for this resource type.
- **New experiment** — the user asks to create, build, set up, make, design, or launch a new experiment: Read `references/create.md`. This route still applies when the user supplies the desired name for the new experiment. Generate a new UUID; do not load an existing experiment.
- **Unsure** — ask: "Would you like to **create** a new chaos experiment, **edit** an existing one, or ask a **reference question** about experiment YAML/components?"

Fault / probe / action add-remove mechanics live in `references/components.md`. Create and edit flows read it after working YAML exists; reference-only questions may read it directly.

For ChaosFault / ChaosProbe / ChaosAction / Chaos steps in a pipeline or DRTest stage, stop and use `chaos-dr-test` instead.

## Examples

- "Create a pod-delete chaos experiment on my checkout-service" -> route to `references/create.md`
- "Add an HTTP probe to my `test-exp-007` experiment" -> route to `references/edit.md`
- "Edit the experiment with UUID `218b1053-...`, remove the CPU hog fault" -> route to `references/edit.md`
- "What does the `vertices` array in a ChaosExperiment manifest mean?" -> route to `references/components.md` (reference-only, no YAML changes)
- "How do I target a workload by labels instead of name?" -> route to `references/components.md`

## Performance Notes

- Do not guess fault, probe, or action identities, infrastructure IDs, or runtime variable names. Always call the matching `harness_list` / `harness_get` / `harness_execute(action="get_variables")` and use the returned values.
- Validate the manifest against the YAML Validation Rules in `references/components.md` before presenting it or saving — no duplicate keys, no orphan `vertices` references, no blank lines.
- Wait for the tool's confirmed save response before reporting success; a review/elicitation prompt is not a completed save.
- **Not covered by this skill:** running an experiment, listing existing experiments, or inspecting run results. Use the Chaos MCP tools directly — `harness_execute(resource_type="chaos_experiment", action="run", resource_id="<experiment_id>", ...)`, `harness_list(resource_type="chaos_experiment_run", ...)`, `harness_get(resource_type="chaos_experiment_run", resource_id="<run_id>", ...)`.

## Troubleshooting

- **Experiment fails to save / validation error** — call `harness_describe(resource_type="chaos_experiment")` to check the authoritative `create` body schema, fix the offending field, and retry.
- **No enterprise or custom faults returned** — confirm the selected infrastructure type (`Kubernetes` -> `KubernetesV2`, `Linux`, `Windows`) matches the fault's supported infrastructure; re-run `harness_list(resource_type="chaos_fault", ...)` with the corrected `infrastructure` filter.
- **Target workload discovery returns empty** — the chaos infrastructure's Service Discovery agent may not have scanned the namespace yet; ask the user to verify the infrastructure is `ACTIVE` and `isChaosEnabled: true` before retrying `discovered_service` / `discovered_namespace` calls.
- **Ambiguous create vs. edit intent** — if the user's request could mean either, ask explicitly per Step 2 above rather than guessing; creating a duplicate experiment is harder to undo than asking one clarifying question.
