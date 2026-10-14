# `metricResultState` classification

Maps the per-row `metricResultState` from experiment results to the four buckets used by SKILL.md Step 6.

The value is passed through from the stats engine as a string. The public API
doesn't fix the value set yet and it can grow, so match prefixes as shown and
default anything unmatched to `needs_more_data`.

| `metricResultState` | Bucket | Meaning |
|---|---|---|
| `SUCCESS` | `desired` | Significant effect in metric's desired direction |
| `FAILURE` | `undesired` | Significant effect against metric's desired direction |
| `INCONCLUSIVE_PVALUE`, `INCONCLUSIVE_PVALUE_NA` | `inconclusive` | Minimum sample size reached, no significant effect |
| `ACROSS` | `inconclusive` | Not significance-tested: metric uses `spread: ACROSS` |
| `RULE_ANY` | `inconclusive` | Not significance-tested for this targeting-rule selection |
| `SINGLE_TREATMENT_*` | `inconclusive` | Not significance-tested: only one treatment has data |
| `NOT_POSSIBLE_VARIANCE_ZERO` | `inconclusive` | Not testable: zero variance |
| `WAITING_NORMALITY` | `needs_more_data` | Still accumulating data (seen only with `statisticalTestType: SEQUENTIAL`, which gates sequential test behind normality check) |
| `NO_DATA_*` (except `NO_DATA_SERVER_ERROR`) | `needs_more_data` | No usable data yet (no impressions, no filter-event data, etc.) - set `DATA_QUALITY_CONCERN` if result is GUARDRAIL or ALERT, since monitored metric with zero data is worth flagging |
| `NO_DATA_SERVER_ERROR`, `FAILED_METRIC` | `needs_more_data` | Calculation error - mention it and set `DATA_QUALITY_CONCERN` |
| `null` | `needs_more_data` | No verdict yet (`pvalue` also `null`) |
| anything else | `needs_more_data` | Unrecognized - don't guess |

For "not significance-tested" rows, say why in the readout instead of reporting
"no significant effect".

## Direction

`SUCCESS`/`FAILURE` already account for the metric's `isPositive`: a decrease on
a decrease-is-good metric (error rate, latency) is `SUCCESS`. Use the state,
never the raw sign of `impactLower`/`impactUpper` - that sign only says whether
the number went up or down. The row's `positive` field is the metric's
configured `isPositive`, not an observed outcome.
