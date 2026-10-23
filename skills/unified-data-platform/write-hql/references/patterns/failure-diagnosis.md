# Failure diagnosis pattern

Drills from a failed top-level run down to the leaf that actually failed. Entity-agnostic — fill the `{...}` placeholders from discovery (see SKILL.md "Placeholder convention").

## Contents

- Shape
- Template query
- Anti-patterns

## Shape

1. Identify the execution hierarchy for the domain from discovery (e.g. execution → stage → step, or scan → finding). `kg_related_type.get` reveals the join paths and keys. `{module}` may be any domain.
2. Join down the hierarchy on the declared join keys; carry the tenant/account key in every join predicate.
3. Filter to the failing leaf (`{status} = 'FAILED'` or the entity's equivalent) — the top-level row alone rarely carries the actionable detail.
4. Select the diagnostic fields off the leaf.

## Template query

```hql
find entity "{module}:{parent}" p | join entity "{module}:{child}" c on c.{parent_key} = p.{parent_key} and c.{tenant_key} = p.{tenant_key} | join entity "{module}:{leaf}" l on l.{child_key} = c.{child_key} and l.{tenant_key} = c.{tenant_key} | filter p.{group_id} = 'my_target' and l.{status} = 'FAILED' and p.{start_time} >= ago(30d) | select { c.{sub_name}, l.{leaf_name}, l.{leaf_type}, l.{failure_code}, l.{failure_message} } | limit 100
```

Resolved example (IF discovery surfaced the `pipeline:pipeline_execution → pipeline:stage_execution → pipeline:step_execution` hierarchy): `{parent_key}` = `plan_execution_id`, `{child_key}` = `stage_execution_id`, `{tenant_key}` = `account_identifier`, `{start_time}` = `start_ts`, and the selected fields = `stage_name`, `step_name`, `step_type`, `failure_code`, `failure_message`.

## Anti-patterns

- Do NOT assume the hierarchy, `{module}`, or join keys — confirm via `kg_related_type.get`.
- Do NOT synthesize failure detail from top-level status alone — the useful data lives on the leaf.
- Do NOT drop the tenant/account predicate from join clauses.
