# Bottleneck analysis pattern

Ranks the sub-units of some process by latency to find the slow ones. Entity-agnostic — fill the `{...}` placeholders from discovery (see SKILL.md "Placeholder convention").

## Contents

- Shape
- Template query
- Anti-patterns

## Shape

1. Pick the entity representing the sub-unit you rank (a pipeline stage, a CI step, a cost line item, a scan job — whatever discovery surfaced). The `{module}` may be any domain, not just `pipeline`.
2. `group_by` the identity columns of that sub-unit.
3. Aggregate its latency field with `avg`, `p95`, and `max` (not `avg` alone — a slow tail hides in `p95`/`max`).
4. Window with a time filter and `order_by` the ranking metric `desc`.

Confirm `{duration}` / `{start_time}` names and `field_type` via `kg_type.get` — sibling entities diverge. See `entity-reference/ci.md` for one such divergence.

## Template query

```hql
find entity "{module}:{entity}" | filter {start_time} >= ago(7d) | select { {group_id}, {sub_unit}, avg({duration}) as avg_ms, max({duration}) as max_ms, p95({duration}) as p95_ms, count() as runs } | group_by {group_id}, {sub_unit} | order_by avg_ms desc | limit 50
```

Resolved example (IF discovery surfaced `pipeline:stage_execution` with `duration` + `start_ts`): substitute `{module}:{entity}` = `pipeline:stage_execution`, `{start_time}` = `start_ts`, `{duration}` = `duration`, `{group_id}` = `pipeline_identifier`, `{sub_unit}` = `stage_name`.

## Anti-patterns

- Do NOT assume `{module}` is `pipeline` — a "bottleneck" question is not always about pipeline stages.
- Do NOT mix fields from two different entities in one query — they may live on different connectors.
- Do NOT omit the time window.
- Do NOT rank only by `avg` — a slow tail shows up in `p95` / `max` while `avg` looks fine.
