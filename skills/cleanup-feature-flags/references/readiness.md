# Flag removal readiness

Use Harness MCP plus local code search. Scope with `org_id` + `project_id`.

## Usage signal

Per-environment **`lastImpressionAt`** on flag definitions is the usage signal. Read it from each definition returned by:

```
harness_list(resource_type="fme_feature_flag_definition", compact=false, params={feature_flag_name: "..."})
```

Compare `lastImpressionAt` against the code-change deploy date per critical environment. Default stale threshold: **no impressions in any critical env since the cleanup code deployed** (ask before using a fixed day count such as 30 days).

Missing `lastImpressionAt` → **caution**, not proof of zero traffic.

## What to check

For each **critical environment**:

- Flag is not archived (or, if archived, only report — do not auto-remove from FME)
- Definition exists — if **no definition** in a critical env, the SDK returns **control**; do not assume the winning treatment applies there
- Same forward treatment across all critical envs (see Forward treatment below)
- No active targeting rules, individual targets, or segments still in play
- `trafficAllocation` is 100% on the winning treatment (excluded traffic still gets `defaultTreatment`)
- `lastImpressionAt` shows no recent impressions since deploy (or user accepts the risk)
- Rollout status: permanent or “do not remove” → **blocked** or **caution**

**Active experiment** on the flag → **blocked**:

```
harness_list(resource_type="fme_experiment", filters={parent_type: "FEATURE_FLAG", parent_name: "<flag>", status: "ACTIVE"})
```

**Dependent flags** — flag-dependency matchers in other flags' rules or in rule-based segments. There is no direct lookup. Either scan other flag definitions for the key or report as **caution** / **blocked** and ask the user.

Also grep the application repo for the flag key (and flag-set APIs — see sdk-patterns.md) before **labeling** a flag **safe**.

## Verdicts

| Verdict | When |
|---------|------|
| **blocked** | Critical envs disagree; prod-like env still targeted; active experiment; dependent flags confirmed; clearly permanent rollout |
| **caution** | Missing or recent `lastImpressionAt`; young flag; partial rollout (`trafficAllocation` < 100); no code refs in this repo; flag-set-only usage; critical env has no definition |
| **safe** | All critical envs agree on one forward treatment with no targeting left; `trafficAllocation` 100%; stale `lastImpressionAt` since deploy; code refs found and removable here |

## Forward treatment

FME definitions are the source of truth — never the SDK default in code.

1. **Killed everywhere** — hardcode the shared `defaultTreatment` (killing removes the new path; the default is what production receives).
2. **Every critical env** has a definition, is not killed, `trafficAllocation` is 100%, no rules or individual targets remain, and all envs agree on one treatment — use that treatment.
3. **Treatment configs** — if the app uses `getTreatmentWithConfig` / `getTreatmentsWithConfig`, read the config payload from the definition and hardcode the config value, not just the treatment name.
4. **Otherwise** — **not safe**; stop and ask the user to align targeting or narrow critical envs.

## Audit ranking

1. Prefer **ACTIVE** flags; also surface **ARCHIVED** flags that still have code refs
2. Prefer **safe** with code refs (remove-from-code candidates)
3. **Caution** with reasons — do not auto-remove
4. **Blocked** last

## Pre-archive re-check

Immediately before `harness_execute` archive, re-run the checks above. Impressions, experiments, or targeting may have changed since the user confirmed the plan.
