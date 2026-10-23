# Flakiness patterns

Combines retry, FAIL-then-PASS, and marked-flake signals. Entity-agnostic — fill the `{...}` placeholders from discovery (see SKILL.md "Placeholder convention"). The signals below are the *kinds* of evidence to seek; the exact entity/field carrying each comes from discovery.

## Contents

- Signal kinds
- Template query — retry-based detection
- Template query — test FAIL-then-PASS
- Template query — marked-flake
- Anti-patterns

## Signal kinds

Never infer flakiness from raw top-level pass/fail counts. Seek up to four kinds of evidence, on whatever entities discovery surfaced expose them:

| Signal kind | What it tells you | Typical carrier (confirm via discovery) |
|---|---|---|
| Retry evidence (bool) | The unit was retried within one execution | a step/execution entity's `is_retried` |
| Retry chain (list) | Which prior executions were the retries | `retry_ids` on the same entity |
| Test-level flake | FAIL-then-PASS across executions = flaky test | a test-execution entity's `result` |
| Marked flake | Test Intelligence-marked status | a test-marking entity's `flaky_status` |

## Template query — retry-based detection

```hql
find entity "{module}:{parent}" p | join entity "{module}:{child}" c on c.{parent_key} = p.{parent_key} and c.{tenant_key} = p.{tenant_key} | join entity "{module}:{leaf}" l on l.{child_key} = c.{child_key} and l.{tenant_key} = c.{tenant_key} | filter p.{start_time} >= ago(7d) and l.{is_retried} = true | select { c.{sub_name}, l.{leaf_name}, count() as retries } | group_by c.{sub_name}, l.{leaf_name} | order_by retries desc | limit 50
```

## Template query — test FAIL-then-PASS

```hql
find entity "{test_module}:{test_entity}" | filter {start_time} >= ago(7d) and {result} = 'FAIL' | select { {test_name}, {class_name}, count() as fail_count } | group_by {test_name}, {class_name} | order_by fail_count desc | limit 50
```

Corroborate against a matching `{result} = 'PASS'` query on the same test names to identify FAIL-then-PASS patterns.

## Template query — marked-flake

```hql
find entity "{test_module}:{marking_entity}" | filter {flaky_status} = 'FLAKY' | select { {test_name}, {class_name}, {flaky_status} } | limit 100
```

Resolved carriers (IF discovery surfaced them): `pipeline:step_execution.is_retried` / `.retry_ids`, `ci:test_execution.result`, `ci:test_marking.flaky_status`.

## Anti-patterns

- Do NOT compute flakiness as `count({status}='FAILED') / count()` on a top-level execution entity alone.
- Do NOT skip the retry signal — it is the primary evidence.
- Do NOT report "no flaky tests" from a single query without checking retry AND FAIL-then-PASS AND marked-flake.
