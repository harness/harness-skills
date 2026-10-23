# Build-time analysis pattern

Ranks executions by how long they take. Entity-agnostic — fill the `{...}` placeholders from discovery (see SKILL.md "Placeholder convention").

## Contents

- Shape
- Template query
- Anti-patterns

## Shape

1. Pick the execution entity discovery surfaced (a pipeline execution, a CI build, a deployment). `{module}` may be any domain.
2. Filter to successful runs only (`{status} = 'SUCCEEDED'` or the entity's equivalent) — failed runs skew duration averages.
3. `group_by` the identity column.
4. Aggregate `{duration}` with `avg`, `p95`, `max`, plus `count`.
5. Window with a time filter; `order_by` the ranking metric `desc`.

Confirm `{duration}` / `{status}` / `{start_time}` names via `kg_type.get` — they differ across entities.

## Template query

```hql
find entity "{module}:{entity}" | filter {status} = 'SUCCEEDED' and {start_time} >= ago(7d) | select { {group_id}, avg({duration}) as avg_ms, p95({duration}) as p95_ms, max({duration}) as max_ms, count() as runs } | group_by {group_id} | order_by avg_ms desc | limit 50
```

Resolved example (IF discovery surfaced `pipeline:pipeline_execution` with `duration` + `status` + `start_ts`): `{module}:{entity}` = `pipeline:pipeline_execution`, `{status}` = `status`, `{start_time}` = `start_ts`, `{duration}` = `duration`, `{group_id}` = `pipeline_identifier`.

## Anti-patterns

- Do NOT assume the execution entity or its `{module}` — confirm via discovery.
- Do NOT omit the `{status}` filter — failed runs skew duration averages.
- Do NOT omit the time window — full-history averages hide recent regressions.
- Do NOT report a single `avg({duration})` alone — pair with `p95` + `max` + `count`.
