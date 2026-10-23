# CI-native entity field discipline

## Contents

- Field-name differences vs pipeline:*
- Cheat sheet
- Worked query
- Anti-patterns

## Field-name differences vs pipeline:*

CI-native entities (prefix `ci:`) use different field names than the module-agnostic `pipeline:*` entities. Mixing them silently returns wrong results.

| Concept | `pipeline:*` field | `ci:*` field |
|---|---|---|
| Duration | `duration` | `stage_build_time` (stage-level), `build_time` (execution-level) |
| Start time | `start_ts` | `start_timestamp` |
| Test result | (none — see `pipeline:step_execution`) | `result` |
| Test class | (none) | `class_name` |
| Flaky marker | (none) | `flaky_status` on `ci:test_marking` |

## Cheat sheet — which entity to reach for

- "how long do CI builds take" → `ci:stage_execution` + `stage_build_time` + `start_timestamp`.
- "which tests are flaky" → `ci:test_execution.result` (FAIL-then-PASS) OR `ci:test_marking.flaky_status`.
- "which tests failed in last N days" → `ci:test_execution` with `result = 'FAIL'` + `start_timestamp >= ago(7d)`.

For pipeline-level (multi-module) analysis, use `pipeline:*` entities and their fields.

## Worked query — CI stage bottleneck ranking

```hql
find entity "ci:stage_execution" | filter start_timestamp >= ago(7d) | select { pipeline_identifier, stage_name, avg(stage_build_time) as avg_build_ms, max(stage_build_time) as max_build_ms } | group_by pipeline_identifier, stage_name | order_by avg_build_ms desc | limit 50
```

## Anti-patterns

- Do NOT use `duration` on `ci:stage_execution` — the field is `stage_build_time`.
- Do NOT use `start_ts` on `ci:*` entities — the field is `start_timestamp`.
- Do NOT join `ci:*` and `pipeline:*` blindly — verify `connectorId` before joining.
