---
name: create-experiment
description: >-
  Guide the design and creation of a new FME experiment (fme_experiment):
  inventories existing metrics and event health, hands off gap-filling to
  create-metric/instrument-metric and primary/secondary selection to
  choose-metric, defines control vs. variant treatments against the flag's
  live definition, drafts a hypothesis, then creates the experiment. Doesn't
  explain an experiment already running or its results - see
  review-experiment-results. Doesn't create the underlying flag or its
  treatments - see manage-feature-flags. Use when asked to design or set up
  an A/B test. Trigger phrases: create an experiment, set up an A/B test,
  design an experiment, launch a test on this flag, new experiment for X.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 server (harness-mcp-v2) with fme_experiment
  (create/get), fme_feature_flag / fme_feature_flag_definition,
  fme_environment, fme_metric, and fme_event_type. fme_experiment is
  Harness-native only (org_id + project_id) - there is no legacy
  workspace_id support, unlike fme_feature_flag. create requires
  environment_id as a param; the parent (Feature Flag or AI Config) must
  already exist in that environment. fme_experiment is not registered in
  the MCP server yet - this skill is written against the contract proposed
  for it and cannot create an experiment until it ships. The flag, metric,
  event-type, and environment lookups it depends on work today.
---

# Create Experiment

Guide a user through designing a well-formed FME experiment end to end -
metrics, control vs. variant, hypothesis - then create it. This skill
orchestrates the decisions; it delegates the decisions other skills already
own rather than re-deriving them.

At every step marked **Stop condition**, present the real options found (or
point to the skill that owns the decision) and wait for a pick.

## Prerequisites

Establish `org_id` + `project_id`. Resolve which environment the experiment
runs in before anything else - `fme_experiment` create needs `environment_id`
as a param, and the flag's treatments (Step 2) are also read per environment:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_environment"
  org_id: "<org_id>"
  project_id: "<project_id>"
```

**Stop condition** if the user hasn't said which environment, ask - don't
default to the first one returned or to production.

## Instructions

### Step 1: Resolve the parent (flag or AI Config)

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { name: "<flag name>" }
```

An experiment's `parent` is `{type: "FEATURE_FLAG"|"AI_CONFIG", id?, name?}` -
`CONFIG` parents 404 on this endpoint. Default to `FEATURE_FLAG` unless the
user says AI Config. If the flag doesn't exist yet, this skill doesn't create
it - point to `/manage-feature-flags` first, then come back.

### Step 2: Confirm control vs. variant against the flag's live treatments

The experiment's `baselineTreatment`/`comparisonTreatments` must be real
treatment names already configured on the flag in the chosen environment, not
invented labels like "control"/"treatment":

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_feature_flag_definition"
  org_id: "<org_id>"
  project_id: "<project_id>"
  params: { feature_flag_name: "<flag_name>", environment_id: "<environment_id>" }
```

Read `treatments[].name`. A 404 here means the flag has no definition in
that environment; if every environment 404s, the flag was created but never
configured anywhere, so there are no treatments to compare and this skill
can't proceed - say so and point to `/manage-feature-flags` to configure the
flag first. If the definition already has a `baselineTreatment`
set, treat it as the default answer for control, but still confirm - the
experiment's own `baselineTreatment` is a separate field and can disagree with
the definition's.

**Stop condition** if there are fewer than two treatments, or it's unclear
which existing treatment is control vs. the variant under test - list the
real `treatments[].name` values and ask. Never invent names like
"control"/"treatment_a". A definition with one real treatment (plus a
hardcoded "off") has nothing to compare against: say so and stop. This skill
does not add treatments to a flag; that's a flag-definition change outside
its scope.

### Step 3: Write the hypothesis

Get a hypothesis in the same form `/choose-metric` requires before
recommending a primary metric: *"if [change], then [metric] will
increase/decrease because [reasoning]"*. `hypothesis` is a free-text field on
`fme_experiment` (max 500 chars) - store the causal reasoning here, not just
the metric name.

**Stop condition** if the hypothesis is missing, or states an outcome
without a causal reason ("conversion will go up" with no "because") - ask for
the missing half. Don't infer it from the flag's name or description.

### Step 4: Inventory metrics and event health

Get a shallow read on whether the hypothesis is already covered before
deciding anything:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_metric"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { name: "<keyword from the hypothesis, substring>", limit: 20 }
```

Always pass a `name` keyword and a `limit` here - this step is only meant to
establish whether a gap exists, and an unnarrowed `fme_metric` list returns
up to 100 full definitions.

For each candidate worth considering, check its event is actually flowing
(same technique `/choose-metric` Step 4 uses - don't re-derive the logic,
just run it):

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_event_type"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters: { name: "<eventTypeId from the metric's baseEventTypes>" }
```

Absent from the last-30-days event list = **at-risk** (never fired, renamed,
or idle); present = **healthy**. This step only establishes whether a gap
exists - it does not decide primary vs. secondary.

- **Healthy candidates cover the hypothesis** - hand off to `/choose-metric`
  to decide which is primary and which are guardrail/counter/supporting; this
  skill doesn't re-run that selection logic.
- **No metric exists for the hypothesis** - hand off to `/create-metric`
  (and `/instrument-metric` first if the event itself doesn't exist).
- **A metric exists but its event is at-risk** - hand off to
  `/instrument-metric` to re-verify or re-wire tracking before relying on it.

Come back to this skill with the resulting metric IDs once those skills
finish; don't block Step 5 draft on that handoff being literally executed in
the same turn if the user wants to finish the design conversation first.

**Stop condition** for primary-vs-secondary assignment - that's
`/choose-metric`'s decision, even when the inventory surfaces a single
obvious-looking candidate. State that a decision is needed and point there.

### Step 5: Decide the experiment window

`startAt`/`endAt` are required ISO-8601 timestamps. Ask for both explicitly -
there's no default duration exposed by this resource type (that's a project-
or org-level `fme_experiment_settings.reviewPeriod` default, which this skill
doesn't read or assume).

### Step 6: Draft and confirm

Present the full payload before calling anything:

```
parent: { type: "FEATURE_FLAG", name: <flag_name> }
name: <experiment_name>
description: <optional>
hypothesis: <hypothesis text>
startAt: <ISO-8601>
endAt: <ISO-8601>
baselineTreatment: <control treatment name>
comparisonTreatments: [<variant treatment name(s)>]
keyMetrics: [<primary metric id(s) from Step 4's handoff>]
supportingMetrics: [<secondary metric ids from Step 4's handoff>]
```

`name` must start with a letter, contain only letters/digits/`-`/`_`, and be
2-250 chars, unique within the project. Do not send `assignmentSource` - the
backend infers/creates it and 400s if present.

**STOP HERE. Do not call `harness_create` yet.** Wait for the user to
explicitly confirm the draft.

### Step 7: Create

```
Call MCP tool: harness_create
Parameters:
  resource_type: "fme_experiment"
  org_id: "<org_id>"
  project_id: "<project_id>"
  params: { environment_id: "<environment_id>" }
  body: { ...confirmed payload }
```

- 409 = duplicate experiment name in the project - revise `name` and retry,
  same as `/create-metric`'s 409 handling; don't silently rename without
  telling the user what changed.
- 404 = the parent doesn't exist in this environment - go back to Step 1/2,
  don't retry the same payload.

### Step 8: Verify

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_experiment"
  org_id: "<org_id>"
  project_id: "<project_id>"
  resource_id: "<id from create response>"
```

Confirm `baselineTreatment`, `comparisonTreatments`, `keyMetrics`, and
`supportingMetrics` match what was drafted. Report the resulting `status`
(created experiments start `ACTIVE` unless the API says otherwise - read it
back rather than assuming).

### Step 9: Hand off

Creating the experiment starts it collecting data; it doesn't explain
results. Once it's run long enough to have data, point to
`/review-experiment-results` for the readout - don't attempt to read
`fme_experiment_result` from this skill.

## Examples

- "Set up an A/B test on the new-checkout flag" - Steps 1-2 resolve the flag
  and its treatments, Step 3 gets the hypothesis, Step 4 checks for an
  existing conversion metric before handing to `/choose-metric` or
  `/create-metric`, Steps 5-8 draft/confirm/create/verify.
- "I want to test dark mode against the current default, does that metric
  already exist?" - Step 4's inventory check answers the metric-existence
  question inline; only hand off to `/create-metric` if it doesn't.
- "Create an experiment called pricing_test_2 with metric abc-123 as
  primary" - metric ID already given, skip Step 4's handoff, still confirm
  Steps 1-3 and 5-6 before creating.
- "Launch the beta-onboarding experiment for 2 weeks starting Monday" -
  Step 5's window is stated; compute `startAt`/`endAt` and confirm the exact
  dates back to the user before drafting.

## Performance Notes

- Resolve `environment_id` and the flag's treatments once (Steps 1-2), not
  per metric or per treatment considered.
- Step 4's inventory check is intentionally shallow - it exists to route to
  the right handoff skill, not to duplicate `/choose-metric`'s full
  health-check-and-recommend flow.
- Don't blind-retry an identical payload after a 400/409 - revise it first
  (Step 7).

## Troubleshooting

### 404 on create even though the flag definitely exists
The parent must exist **in the chosen environment**, not just in the
project. Re-check Step 2's `fme_feature_flag_definition` get for that exact
`environment_id` before retrying.

### User wants to change treatments mid-design
This skill reads the flag's existing treatments; it doesn't add or rename
them. Point to the flag/definition owner (or `/manage-feature-flags` if it
covers the needed operation) to add the treatment first, then restart Step 2.

### Experiment needs to attach a workspace-wide guardrail metric
Guardrail and alert metrics apply to every experiment automatically and are
never set via `keyMetrics`/`supportingMetrics` - see `/choose-metric` and
`/review-experiment-results` for how those surface in results. Don't try to
add them to this draft.

### Metric handoff (`/create-metric`, `/instrument-metric`, `/choose-metric`)
didn't happen before the user wants to create the experiment
Creating an experiment with an empty `keyMetrics` is allowed by the backend,
but leaves the experiment with no winner criterion - warn explicitly and
confirm the user wants to proceed before Step 6's draft, rather than silently
omitting metrics.
