---
name: review-experiment-results
description: >-
  Explain Harness FME experiment results: winner determination, statistical
  significance, guardrail metric impact, and data-quality caveats (low sample
  size, missing data). Classifies each metric's outcome and produces
  plain-language readout by default, surfacing underlying stats (p-value, CI,
  sample size) on request. Use when asked to explain, review, or interpret
  experiment results; "did treatment X win"; "is this experiment significant";
  "what happened to metric Y in this experiment"; or "should we ship this
  experiment". Do NOT use for changing experiments (manage-experiments), choosing
  metrics (choose-metric), or diagnosing bias (SRM root cause, peeking,
  Simpson's paradox). Trigger phrases: experiment results, readout, winner,
  statistical significance, guardrail metric, ship this experiment.
metadata:
  author: Harness
  version: 2.1.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Review Experiment Results

Explain an FME experiment's outcome in plain language: whether there's a winner,
why or why not, how guardrail metrics were affected, and any data-quality
caveats - with underlying statistics available on request.

Related: [manage-experiments](../manage-experiments/SKILL.md) (experiment
changes), [choose-metric](../choose-metric/SKILL.md) (metric selection).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| **List experiments** | `harness_list` · `fme_experiment` · `filters: { parent_type, name?, status?: ["ACTIVE", "PAUSED", "COMPLETED", "ARCHIVED"], … }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG [--search <name>] --status ACTIVE`, then repeat with `--status PAUSED`, `--status COMPLETED`, `--status ARCHIVED` (CLI `--status` is single-value; API defaults to `ACTIVE` if omitted) |
| **Get experiment** | `harness_get` · `fme_experiment` · `params: { experiment_id }` | `harness get experiment <experiment-id>` |
| **Get settings** | `harness_get` · `fme_experiment_settings` · `params: { experiment_id }` | `harness get experiment:settings <experiment-id>` |
| **List results** | `harness_list` · `fme_experiment_result` · `filters: { experiment_id, comparisons? }` | `harness list experiment:results <experiment-id> --raw` |
| **Get/list metrics** | `harness_get` · `fme_metric` · `params.metric_id` (one call per id), or `harness_list` · `fme_metric` · `filters: { ids }` · `compact: false` | `harness get metric <id>` once per id, or `harness list metric --id <id>` once per id - the CLI's `--id` flag is repeatable but only the first value reaches the API (spec bug), so repeating `--id id1 --id id2` on one call silently drops `id2` |

## Instructions

### Phase 1: Establish scope
Follow [scope-establishment.md](../../references/scope-establishment.md).

### Step 1: Resolve the experiment

If the user gives an exact experiment ID, **Get experiment** directly - skip list. Otherwise **List experiments** for parent type FEATURE_FLAG (or AI_CONFIG if user specified), with name substring match if provided. Default parent type: FEATURE_FLAG.

If user didn't specify status, list ACTIVE, PAUSED, COMPLETED, **and ARCHIVED** - a finished or archived experiment is exactly the kind a results question is usually about, so never default to active-only here. More than one match or no name given → ask which experiment.

### Step 2: Fetch experiment definition

**Get experiment**. Key fields: `status`, `environment`, `startAt`/`endAt`, `baselineTreatment`, `comparisonTreatments[]`, `keyMetrics[]`, `supportingMetrics[]`.

`keyMetrics`/`supportingMetrics` are the only metric lists on the experiment. `GUARDRAIL` and `ALERT` metrics are workspace-wide categories applying to every experiment, so they never appear here - read role from each result's `category` (Step 4). Empty `keyMetrics` → no winner criterion; ask which metric(s) should drive verdict.

More than one `comparisonTreatments` and user didn't name one → report every treatment (one verdict each, see Output Format). If question presumes a single treatment ("did it win?") → ask which treatment or confirm per-treatment readout.

### Step 3: Fetch experiment settings

**Get settings**. Always returns applied settings (404 only if experiment doesn't exist). `source: "EXPERIMENT_OVERRIDE"` means experiment has its own override; other values mean it inherits org defaults.

Fields to carry forward: `significanceThreshold` (not always 0.05), `multipleComparisonCorrection` (`NONE` or `GROUPWISE_HOCHBERG`; applies only to KEY/SUPPORTING, never GUARDRAIL/ALERT), `minimumSampleSize` (per treatment), `statisticalTestType` (`FIXED_HORIZON`/`SEQUENTIAL`), `reviewPeriod` (ISO-8601 duration), `varianceReduction.method` (`NONE`/`CUPED`).

### Step 4: Fetch evaluated results

**List results** for the experiment, optionally narrowed to specific comparison treatments. List-only (no single-result get, no per-environment filter). Returns latest calculation run only, as one row per (metric, comparison treatment) pair, plus top-level `calculatedAt` (`null` if never calculated). If narrowing to specific treatments, filter the returned rows on each item's `comparison` (see [tool-map.md](../../references/fme/tool-map.md)).

Per-row fields: `category` (`KEY`, `SUPPORTING`, `GUARDRAIL`, or `ALERT`), `comparison` (comparison treatment this row is for), `metricId.id` / `metricId.name` (`name` can be `null`; resolve in Step 5), `metricResultState` (stats engine verdict; `null` if none yet), `pvalue`, `impactLower`/`impactUpper`, `value`, `errorMargin`, `baselineMean`/`comparisonMean` (each with `Lower`/`Upper`), `baselineSampleSize`/`comparisonSampleSize`, `varianceReduction`, `positive` (metric's configured `isPositive`, not observed outcome; non-null even when numeric fields are `null`).

No SRM field in response, so can't confirm traffic split matched configured split - Step 8 says so whenever it reports a winner. Report `metricResultState`/`pvalue` as given; never recompute significance or claim to correct for peeking.

**Reconcile before scoring.** The expected row set is the Cartesian product of every configured metric (`keyMetrics` ∪ `supportingMetrics` from Step 2) × every comparison treatment in scope (all of them, or the one(s) picked in Step 2); it must be non-empty, since Step 2 already stops on empty `keyMetrics`. Match returned rows against it:
- Two or more rows for the same (`metricId.id`, `comparison`) pair → duplicate/conflicting data; don't pick one arbitrarily - treat that combination as `needs_more_data` and note the conflict in Step 8.
- An expected (metric, comparison) combination has no row at all → treat as `needs_more_data`, same as a row with `metricResultState: null`; never treat a missing combination as "nothing to report."
- A row's `comparison` isn't in the experiment's current `comparisonTreatments` → drop it (stale data from a removed treatment).
- `calculatedAt` is `null`, or the whole result list is empty → no calculation has run; every KEY result is `needs_more_data`, so Step 7's verdict is `NEED_MORE_DATA` - never report `WINNER` from an empty or uncalculated result set.

GUARDRAIL/ALERT rows aren't part of the expected set (they're workspace-wide, not listed on the experiment) but must still flow through to Step 7's `DATA_QUALITY_CONCERN` modifier when present with no data - don't drop them while reconciling KEY/SUPPORTING coverage.

### Step 5: Resolve metric names and descriptions

Resolve every distinct metric ID from returned rows **and** configured metrics missing from those rows, so gaps can be named. MCP may **List metrics** by IDs; CLI must **Get metric** separately for each ID (or one single-ID list per call). Include returned GUARDRAIL/ALERT IDs too. Descriptions help judge severity: a 2% dip on "leading indicator, noisy" reads differently from same dip on "primary revenue guardrail".

### Step 6: Classify each result

Map each `metricResultState` to `desired`, `undesired`, `inconclusive`, or `needs_more_data` using [state-classification.md](./references/state-classification.md). For `needs_more_data` results, compare `baselineSampleSize`/`comparisonSampleSize` to `minimumSampleSize` so readout can say how far along collection is.

### Step 7: Determine the verdict

One verdict per selected comparison. **Completeness gate runs first:** empty/uncalculated results, missing or duplicate configured metric/comparison pairs, or mismatched expected categories force `NEED_MORE_DATA` + `DATA_QUALITY_CONCERN` for the affected comparison. Show observed regressions/guardrails separately; don't hide them. Only a non-empty reconciled set with every configured KEY and SUPPORTING pair present exactly once enters the table below. A missing workspace-wide guardrail inventory remains unverified, not evidence of no breaches.

Then evaluate top to bottom; first match wins:

| Verdict | Condition |
|---|---|
| `MIXED` | At least one KEY result is `desired` and at least one result of any category is `undesired` |
| `WINNER` | Completeness gate passed; at least one configured KEY result exists and every configured KEY result is `desired` |
| `REGRESSION` | At least one KEY result is `undesired` |
| `NEED_MORE_DATA` | At least one KEY result is `needs_more_data` (including missing or conflicting combinations caught by Step 4's reconciliation) |
| `NO_WINNER` | Otherwise (KEY results are `inconclusive`, or mix of `desired` and `inconclusive`) |

Modifiers (attach to any verdict):
- `GUARDRAIL_BREACH` - any `category: GUARDRAIL` result is `undesired`. An
  `undesired` SUPPORTING or ALERT result affects the verdict but is not a
  guardrail breach. By row order, `WINNER` never carries this modifier.
- `DATA_QUALITY_CONCERN` - more than half of KEY results are in a `NO_DATA_*`
  state; any result is `NO_DATA_SERVER_ERROR`/`FAILED_METRIC`; or any
  GUARDRAIL/ALERT result is in a `NO_DATA_*` state at all. A guardrail that
  never received data is a monitoring gap, not just a data point to omit.

### Step 8: Explain the results

Default to plain language. Link [concepts.md](../../references/fme/concepts.md#experiments-and-metrics) for SRM and peeking caveats. Lead with verdict, then why. Describe trade-offs, not business decision. `DATA_QUALITY_CONCERN`: say so plainly, and call out any duplicate/conflicting rows or missing metric×treatment combinations Step 4 found. `WINNER` or `MIXED`: add one line: SRM isn't exposed through API; check experiment's results page in Harness UI before acting. Fixed-horizon + before review period: say readout is preliminary - if the verdict is `WINNER`, report it as `WINNER (preliminary)` in the Output Format and don't call it actionable until the review period ends or the test type is `SEQUENTIAL`. Inconclusive but not significance-tested: say why (e.g. `ACROSS` metric). `calculatedAt` non-null: include timestamp. `pvalue` null (e.g. `WAITING_NORMALITY`): don't quote `value`/impact as confident. `GUARDRAIL_BREACH` + `MIXED`: lead with breach. Guardrail or supporting metrics with data (any category present in Step 4's reconciled rows) must appear in the Metric Impact table - never omit a row just because it isn't KEY. If `multipleComparisonCorrection` is `NONE` and the experiment has more than one key metric, add one line flagging the false-positive risk. Stats detail: add p-value, CI, sample sizes, `significanceThreshold`, `multipleComparisonCorrection`, settings `source` when question uses statistical terms or user asks. No stats detail: close with one-line note that stats available on request.

## Output Format

For a single comparison treatment:

```
## Experiment Readout
- Experiment: <name> (<status>)
- Comparing: <treatment> vs <baseline>
- Calculated: <calculatedAt>

## Verdict
**<VERDICT>** [+ `(preliminary)` if fixed-horizon and before the review period ends] [+ modifiers if any]
<2-4 sentence explanation>

## Metric Impact
| Metric | Role | Result |
|---|---|---|
| <name> | Key / Supporting / Guardrail / Alert | <desired/undesired/inconclusive/needs more data, in plain words> |

## Notes
<data-quality caveats, if any; otherwise omit>
```

For more than one comparison treatment, keep one shared experiment header and
Notes section, but repeat verdict + table block per treatment under its own
`### <treatment name>` subheading (independent verdict per treatment).

Add p-value/CI/sample-size columns to Metric Impact only when Step 8's stats
condition is met.

## Examples

- "Explain the results of checkout-redesign experiment" → resolve by name, Steps 2-8, plain-language output
- "Did treatment B win in exp_8f2a1c?" → resolve by ID, verdict for treatment B only
- "Is the signup-flow experiment statistically significant?" → statistical wording triggers stats detail
- "Should we ship the onboarding experiment?" → verdict + trade-offs; no ship/no-ship recommendation

## Performance Notes

- Resolve concrete experiment id before Step 4; never fetch results by name
- Fetch settings (Step 3) and metric names (Step 5) once per experiment, not per treatment
- Narrow Step 4 to specific comparison treatments once user picks a treatment instead of fetching every comparison

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| An experiment operation fails | Report error and stop |
| Step 2 404s but Steps 3/4 succeed | Without Step 2 there are no treatment or key-metric definitions; tell user full readout isn't possible for this experiment |
| Experiment still ACTIVE or PAUSED | If verdict is NEED_MORE_DATA or NO_WINNER, ask whether user wants preliminary readout (caveated) or would rather wait; use `endAt` (and `reviewPeriod`) to say how much longer it's configured to run |
| Unrecognized or null `metricResultState` | Treat as `needs_more_data`; don't guess a direction; see [state-classification.md](./references/state-classification.md) |
| Duplicate or conflicting rows for the same metric + comparison | Treat that combination as `needs_more_data`; note the conflict; never pick one row arbitrarily |
| Expected metric×treatment combination missing from results | Treat as `needs_more_data`; never report `WINNER` from partial coverage |
| Results are empty and experiment's `rule` is `default` or another label with no traffic | Results only count impressions whose label matches the experiment's `rule`; offer to update the experiment's `rule` to `"default rule"` via [manage-experiments](../manage-experiments/SKILL.md) |
| User asks about SRM | Results API exposes no SRM value; say so and point to experiment's results page in Harness UI; don't diagnose causes |
| User wants to change experiment | Route to [manage-experiments](../manage-experiments/SKILL.md) |
| User asks which metric to use | Route to [choose-metric](../choose-metric/SKILL.md) |
