---
name: review-experiment-results
description: >-
  Explain Harness FME (Split.io) experiment results: winner determination,
  statistical significance, guardrail metric impact, and data-quality caveats
  (low sample size, missing data). Fetches the experiment definition and
  evaluated results via MCP, classifies each metric's outcome, and produces a
  plain-language readout by default, surfacing underlying stats (p-value,
  confidence interval, sample size) on request. Use when asked to explain,
  review, or interpret experiment results; "did treatment X win"; "is this
  experiment significant"; "what happened to metric Y in this experiment";
  or "should we ship this experiment". Do NOT use for diagnosing why results
  look wrong or biased (SRM root cause, peeking, Simpson's paradox). Trigger
  phrases: experiment results, readout, winner, statistical significance,
  guardrail metric, ship this experiment, experiment summary.
metadata:
  author: Harness
  version: 1.0.1
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 server (harness-mcp-v2) with fme_experiment,
  fme_experiment_settings, fme_experiment_result, and fme_metric. All are
  Harness-native only (org_id + project_id); no workspace_id support.
  fme_experiment, fme_experiment_settings, and fme_experiment_result are
  not registered in the MCP server yet - this skill is written against the
  contract proposed for them and cannot run until they ship. fme_metric is
  available today.
---

# Review Experiment Results

Explain an FME experiment's outcome in plain language: whether there's a
winner, why or why not, how guardrail metrics were affected, and any
data-quality caveats - with the underlying statistics available on request.

## Prerequisites

Establish `org_id` + `project_id` before any call (all four resource types
are Harness-native only; there is no `workspace_id` fallback).

## Instructions

### Step 1: Resolve the experiment

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_experiment"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters:
    parent_type: "FEATURE_FLAG"
    name: "<experiment name, if given>"
    match_type: "contains"
```

- `parent_type` is required: `FEATURE_FLAG` or `AI_CONFIG` (`CONFIG` 404s).
  If the user didn't say what the experiment runs on, use `FEATURE_FLAG`
  and say you assumed it if nothing turns up.
- `status` defaults to `[ACTIVE]` - pass it explicitly if the experiment
  might be `PAUSED`/`ARCHIVED`/`COMPLETED`.
- Filters must go inside `filters`; top-level they're silently ignored.

**Stop condition:** if more than one experiment matches, or the user gave
neither a name nor an ID, ask which experiment they mean.

### Step 2: Fetch the experiment definition

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_experiment"
  org_id: "<org_id>"
  project_id: "<project_id>"
  resource_id: "<experiment_id>"
```

Key fields: `status`, `environment`, `startAt`/`endAt`,
`baselineTreatment`, `comparisonTreatments[]`, `keyMetrics[]`,
`supportingMetrics[]`.

`keyMetrics`/`supportingMetrics` are the only metric lists on the
experiment. `GUARDRAIL` and `ALERT` metrics are workspace-wide metric
categories that apply to every experiment, so they never appear here -
read role membership from each result's `category` (Step 4), not from these
lists.

**Stop condition:** if `keyMetrics` is empty, a winner is undefined. Ask
which metric(s) should drive the verdict; don't substitute
`supportingMetrics`.

**Stop condition:** if `comparisonTreatments` has more than one entry and
the user didn't specify one, stop before Step 3 and ask which treatment(s)
to compare - reporting every treatment is a valid answer, but it must be an
answer, not a default you fall into because Step 4 would return every row
anyway.

### Step 3: Fetch experiment settings

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_experiment_settings"
  org_id: "<org_id>"
  project_id: "<project_id>"
  resource_id: "<experiment_id>"
```

Always returns the applied settings (404s only if the experiment doesn't
exist). `source: "EXPERIMENT_OVERRIDE"` means the experiment has its own
override; any other value means it inherits org defaults (the backend
returns `DEFAULT`, while the API spec names it `ORGANIZATION_DEFAULT` - don't
match on either string exactly).

Fields to carry forward:
- `significanceThreshold` - not always 0.05; read it.
- `multipleComparisonCorrection` - `NONE` or `GROUPWISE_HOCHBERG`. Applies
  only to `KEY`/`SUPPORTING` results; `GUARDRAIL`/`ALERT` results are never
  corrected.
- `minimumSampleSize` - per treatment.
- `statisticalTestType` (`FIXED_HORIZON`/`SEQUENTIAL`), `reviewPeriod`
  (ISO-8601 duration, e.g. `"PT336H"` = 14 days), `varianceReduction.method`
  (`NONE`/`CUPED`).

### Step 4: Fetch evaluated results

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_experiment_result"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters:
    experiment_id: "<experiment_id>"
    comparisons: "<treatment(s) chosen in Step 2, if narrowing>"
```

List-only (no `get`, no `environment_id` filter - the experiment has one
environment). Returns the latest calculation run only, as one row per
(metric, comparison treatment) pair, plus top-level `calculatedAt` (`null`
if never calculated). `comparisons` defaults to all comparison treatments;
`comparisons`/`metric_ids` filters change which rows come back, never the
multiple-comparison correction.

Per-row fields:
- `category` - `KEY`, `SUPPORTING`, `GUARDRAIL`, or `ALERT`; the role
  classification. Categories are disjoint with precedence KEY > SUPPORTING >
  GUARDRAIL > ALERT, so a workspace guardrail metric that is also attached
  as supporting shows as `SUPPORTING`.
- `comparison` - the comparison treatment this row is for.
- `metricId.id` / `metricId.name` - `name` can be `null`; resolve names in
  Step 5.
- `metricResultState` - the stats engine's verdict; `null` if none yet.
- `pvalue`, `impactLower`/`impactUpper`, `value`, `errorMargin`,
  `baselineMean`/`comparisonMean` (each with `Lower`/`Upper`),
  `baselineSampleSize`/`comparisonSampleSize`, `varianceReduction`.
- `positive` - the metric's configured `isPositive`, not an observed
  outcome; it's non-null even when every numeric field is `null`.

The response has no SRM field.

Report `metricResultState`/`pvalue` as given - never recompute
significance or claim to correct for peeking.

### Step 5: Resolve metric names and descriptions

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_metric"
  org_id: "<org_id>"
  project_id: "<project_id>"
  filters:
    ids: "<every distinct metricId.id from Step 4>"
```

Use the Step 4 ids, not `keyMetrics`/`supportingMetrics`, so
`GUARDRAIL`/`ALERT` metrics get names too. Descriptions help judge
severity: a 2% dip on a metric described as "leading indicator, noisy"
reads differently from the same dip on "primary revenue guardrail".

### Step 6: Classify each result

Map each `metricResultState` to `desired`, `undesired`, `inconclusive`, or
`needs_more_data` using `references/state-classification.md`. For
`needs_more_data` results, compare `baselineSampleSize`/
`comparisonSampleSize` to `minimumSampleSize` so the readout can say how far
along collection is.

### Step 7: Determine the verdict

One verdict per comparison treatment. Evaluate top to bottom; first match
wins:

| Verdict | Condition |
|---|---|
| `MIXED` | At least one `KEY` result is `desired` and at least one result of any category is `undesired` |
| `WINNER` | Every `KEY` result is `desired` |
| `REGRESSION` | At least one `KEY` result is `undesired` |
| `NEED_MORE_DATA` | At least one `KEY` result is `needs_more_data` |
| `NO_WINNER` | Otherwise (`KEY` results are `inconclusive`, or a mix of `desired` and `inconclusive`) |

Modifiers (attach to any verdict):
- `GUARDRAIL_BREACH` - any `category: GUARDRAIL` result is `undesired`. An
  `undesired` `SUPPORTING` or `ALERT` result affects the verdict above but
  is not a guardrail breach. By the row order, `WINNER` never carries this
  modifier; never state a winner when a guardrail regressed.
- `DATA_QUALITY_CONCERN` - more than half of the `KEY` results are in a
  `NO_DATA_*` state; any result is `NO_DATA_SERVER_ERROR`/`FAILED_METRIC`;
  or any `GUARDRAIL`/`ALERT` result is in a `NO_DATA_*` state at all. A
  guardrail that never received data is a monitoring gap worth surfacing on
  its own, not just a data point to omit - don't let it disappear into a
  `WINNER` verdict unremarked.

### Step 8: Explain the results

Default to plain language:
- Verdict first, then why, in a warm direct tone - no p-values, CIs, or
  sample sizes in the main explanation, and use the data's actual treatment
  names.
- Describe trade-offs rather than prescribing a business decision
  ("Treatment B improved conversion but reduced average order value", not
  "you should ship Treatment B").
- If `DATA_QUALITY_CONCERN` is set, say so plainly without diagnosing root
  cause.
- For an `inconclusive` result that isn't significance-tested (see the
  reference file), say why (e.g. an `ACROSS` metric) rather than "no
  significant effect".
- Include `calculatedAt` when non-null. If it's `null` but results have
  terminal states (real p-values), say the readout reflects the latest run
  without a timestamp instead of printing "Calculated: null".
- `NO_WINNER` covers both "all `KEY` results flat" and "some desired, some
  merely inconclusive" - say which; don't undersell a metric with a strong
  desired effect as "nothing happened" just because another metric kept it
  short of `WINNER`.
- Don't quote `value`/impact numbers as confident when `pvalue` is `null`
  (e.g. `WAITING_NORMALITY`) - it's a raw sample mean, not yet a
  statistically backed estimate.
- If `GUARDRAIL_BREACH` co-occurs with `MIXED`, lead with the breach, not
  the key-metric lift - it's why this isn't a clean win, not a footnote to
  one.

Add the stats detail (p-value, confidence interval, sample sizes,
`significanceThreshold`, `multipleComparisonCorrection`, settings `source`)
when the question uses statistical terms (p-value, significance, confidence
interval, sample size) or the user asks for detail. State the experiment's
own threshold next to any p-value, and if `multipleComparisonCorrection` is
`NONE` with more than one `KEY`/`SUPPORTING` metric, say no correction was
applied. Otherwise close with a one-line note that stats are available on
request.

## Output Format

For a single comparison treatment:

```
## Experiment Readout
- Experiment: <name> (<status>)
- Comparing: <treatment> vs <baseline>
- Calculated: <calculatedAt>

## Verdict
**<VERDICT>** [+ modifiers if any]
<2-4 sentence explanation>

## Metric Impact
| Metric | Role | Result |
|---|---|---|
| <name> | Key / Supporting / Guardrail / Alert | <desired/undesired/inconclusive/needs more data, in plain words> |

## Notes
<data-quality caveats, if any; otherwise omit this section>
```

For more than one comparison treatment (only after the user has answered
Step 2's stop condition), keep one shared experiment header and Notes
section, but repeat the verdict + table block per treatment under its own
`### <treatment name>` subheading in place of the single `## Verdict` /
`## Metric Impact` headings - each treatment gets an independent verdict,
never one merged table or verdict line.

Add p-value/CI/sample-size columns to Metric Impact only when Step 8's
stats condition is met.

## Examples

- "Explain the results of the checkout-redesign experiment" - resolve by
  name, run Steps 2-8, plain-language output.
- "Is the signup-flow experiment statistically significant?" - statistical
  wording triggers the stats detail, including threshold and correction
  method.
- "Should we ship the onboarding experiment?" - verdict + trade-offs; no
  ship/no-ship recommendation.

## Performance Notes

- Fetch settings (Step 3) and metric names (Step 5) once per experiment, not
  per treatment.
- Narrow Step 4 with `comparisons` once the user picks a treatment instead
  of fetching every comparison.

## Troubleshooting

### An `fme_experiment*` call fails
Report the error and stop; don't call the underlying REST API directly.

### Step 2 404s but Steps 3/4 succeed for the same ID
`fme_experiment` get returns 404 for warehouse-native and `CONFIG`
experiments. Without Step 2 there are no treatment or key-metric
definitions, so tell the user a full readout isn't possible for this
experiment through the MCP server rather than guessing them.

### Experiment is still `ACTIVE` or `PAUSED`
If the verdict is `NEED_MORE_DATA` or `NO_WINNER`, ask whether the user
wants a preliminary readout (caveated) or would rather wait. Use `endAt`
(and `reviewPeriod`) to say how much longer it's configured to run.

### Unrecognized or `null` `metricResultState`
Treat as `needs_more_data`; don't guess a direction. See
`references/state-classification.md`.

### User asks about SRM
The results API exposes no SRM value. Say so, and point the user to the
experiment's results page in the Harness UI. Don't diagnose causes
(targeting bugs, exposure-logging gaps) - out of scope for this skill.
