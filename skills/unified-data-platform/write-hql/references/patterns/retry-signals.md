# Retry-signals join patterns

Attributes retries down a join chain. Entity-agnostic — fill the `{...}` placeholders from discovery (see SKILL.md "Placeholder convention").

## Contents

- Join keys
- Template query
- Anti-patterns

## Join keys

Retry evidence usually lives on the leaf entity of an execution hierarchy. To attribute retries back up to parent + sub-unit, join on the keys `kg_related_type.get` declares:

- `{child}.{parent_key} = {parent}.{parent_key}`
- `{leaf}.{child_key} = {child}.{child_key}`
- Every join carries `{tenant_key}` in the ON clause.

## Template query — retries by parent + sub-unit + leaf

```hql
find entity "{module}:{parent}" p | join entity "{module}:{child}" c on c.{parent_key} = p.{parent_key} and c.{tenant_key} = p.{tenant_key} | join entity "{module}:{leaf}" l on l.{child_key} = c.{child_key} and l.{tenant_key} = c.{tenant_key} | filter p.{start_time} >= ago(7d) and l.{is_retried} = true | select { p.{group_id}, c.{sub_name}, l.{leaf_name}, count() as retry_count } | group_by p.{group_id}, c.{sub_name}, l.{leaf_name} | order_by retry_count desc | limit 50
```

Resolved example (IF discovery surfaced `pipeline:pipeline_execution → stage_execution → step_execution`): `{parent_key}` = `plan_execution_id`, `{child_key}` = `stage_execution_id`, `{tenant_key}` = `account_identifier`, `{is_retried}` = `is_retried`.

## Anti-patterns

- Do NOT count retries on the top-level execution — retries are leaf-level.
- Do NOT skip `{tenant_key}` in join predicates.
- Do NOT project a retry-chain list field for a group-by aggregate — inspect it on a specific leaf row.
