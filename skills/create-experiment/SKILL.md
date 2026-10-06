---
name: create-experiment
description: >-
  Thin compatibility entrypoint for creating a new Harness FME experiment.
  Invokes manage-experiments' Create experiment flow directly - same scope,
  parent/environment resolution, hypothesis, metrics, treatments, window, and
  rule - and returns the created experiment id plus verification. Use when
  asked to create an experiment, set up an A/B test, or design a new
  experiment. Do NOT use for updating, pausing, resuming, completing,
  archiving, or deleting an experiment (manage-experiments), or for
  explaining results (review-experiment-results). Trigger phrases: create
  experiment, set up an A/B test, design an experiment, launch a test,
  new experiment for X.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Create Experiment

Compatibility entrypoint kept for direct `/create-experiment` invocation. This
skill does not duplicate any workflow - it hands the entire creation flow to
[manage-experiments](../manage-experiments/SKILL.md)'s **Create experiment**
section and returns once that flow completes.

## Instructions

### Step 1: Delegate

Read [manage-experiments/SKILL.md](../manage-experiments/SKILL.md) and follow
its **Phase 1: Establish scope** and **Create experiment** section (Steps 1-8)
exactly as written, using the current request's scope (org/project), parent
flag + environment, hypothesis, metrics, treatments, window
(`startAt`/`endAt`), and `rule`. Do not re-derive or re-interpret any of that
section's logic here - this skill has no independent instructions for
resolving treatments, choosing metrics, or drafting the payload; it only
exists so `/create-experiment` remains a valid invocation.

If the tool interface you're running under can't follow a markdown link to
load another skill's file on demand, read
`skills/manage-experiments/SKILL.md` directly (same repo, relative path) and
proceed the same way.

### Step 2: Return the result

Once manage-experiments' Step 8 (Verify) completes, report the created
experiment's `id`, `status`, and the verified fields (baseline/comparison
treatments, key/supporting metrics, rule) back to the user. Don't add a
second verification pass - manage-experiments' Step 8 is authoritative.

## Examples

- "Create an experiment on the new-checkout flag" → delegate to
  manage-experiments Create flow, return created id
- "Set up an A/B test for the pricing page" → same delegation
- "Pause experiment pricing_test_2" → not this skill; route to
  [manage-experiments](../manage-experiments/SKILL.md) (Update)
- "Did the checkout experiment win?" → not this skill; route to
  [review-experiment-results](../review-experiment-results/SKILL.md)

## Performance Notes

- No independent tool calls: every MCP/CLI operation happens inside the
  delegated manage-experiments flow, so there's no duplicate scope
  resolution or double-verification to optimize away here.

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| User asks to update/pause/resume/complete/archive/delete an existing experiment | Route to [manage-experiments](../manage-experiments/SKILL.md) (Update/Delete), not this skill |
| User asks about results, winner, or significance | Route to [review-experiment-results](../review-experiment-results/SKILL.md) |
| manage-experiments' Create flow stops on a missing decision (hypothesis, treatments, metrics) | Surface that stop to the user here too - don't guess on its behalf |
| Delegated flow fails partway (e.g. 404 on parent, 409 duplicate name) | Report the error as manage-experiments' Troubleshooting table describes; don't retry with invented values |
