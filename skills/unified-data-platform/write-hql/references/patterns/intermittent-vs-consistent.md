# Intermittent vs consistent failure pattern

Classifies units by their status distribution. Entity-agnostic — fill the `{...}` placeholders from discovery (see SKILL.md "Placeholder convention").

## Contents

- Heuristic
- Template query
- Interpretation
- Anti-patterns

## Heuristic

An **intermittent** unit has a mix of SUCCEEDED and non-SUCCEEDED runs in the window. A **consistent** failure has 100% non-SUCCEEDED runs. `group_by ({group_id}, {status})` and inspect the distribution. `{module}` may be any domain.

## Template query — status distribution per unit

```hql
find entity "{module}:{entity}" | filter {start_time} >= ago(7d) | select { {group_id}, {status}, count() as runs } | group_by {group_id}, {status} | order_by {group_id}, runs desc | limit 500
```

Resolved example (IF discovery surfaced `pipeline:pipeline_execution`): `{group_id}` = `pipeline_identifier`, `{status}` = `status`, `{start_time}` = `start_ts`.

## Interpretation

- Units appearing only with `{status} = 'FAILED'` (no SUCCEEDED row) = consistent failures.
- Units appearing with both SUCCEEDED and FAILED = intermittent — candidate for the flakiness deep-dive (`flakiness.md`).
- Units with only SUCCEEDED = healthy in the window.

Return the classified list; do not conflate the two categories.

## Anti-patterns

- Do NOT report all failing units as "flaky" — separate consistent from intermittent first.
- Do NOT drop the time window — cumulative history hides recent regressions.
- Do NOT use only `count({status}='FAILED')` — you also need the SUCCEEDED count for the same unit.
