# Batch HQL execution pattern

## Contents

- Rule
- Batch sizes
- Worked flow
- Anti-patterns

## Rule

Group independent HQL queries into batches using the `queries=[...]` param on `harness_execute`. Never issue more than 3 sequential `harness_execute(resource_type='hql_query', action='run')` calls when the queries could batch. Evidence: QA trace `13f99615` ran 50 sequential HQL executes and hit the 300s timeout.

## Batch sizes

| Action | Max per call | Purpose |
|---|---|---|
| `validate` (queries param) | 20 | Lint pass — batch aggressively. |
| `run` (queries param) | 10 | Execute pass — smaller batches cap tail-latency. |

## Worked flow — 3 independent queries in one call

```
harness_execute(resource_type='hql_query', action='validate', queries=[{query_string: q1}, {query_string: q2}, {query_string: q3}])
    on all green: harness_execute(resource_type='hql_query', action='run', queries=[{query_string: q1}, {query_string: q2}, {query_string: q3}])
```

## Anti-patterns

- Do NOT loop `harness_execute(hql_query, run)` N times when the queries have no dependency between them.
- Do NOT exceed 10 per `run` batch — the service caps at 10.
- Do NOT batch dependent queries — if query B needs query A's rows to build its filter, run them sequentially.
