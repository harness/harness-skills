# Lint-first pattern (validate before execute)

## Contents

- Rule
- Repair ladder
- Worked flow
- Anti-patterns

## Rule

Every HQL query MUST pass `harness_execute(resource_type='hql_query', action='validate')` before `harness_execute(resource_type='hql_query', action='run')`. Query Service catches syntax + semantic errors — field-typo, wrong cast, cross-connector join — at validate time. Skipping validate turns those into execute-time loops (evidence: QA trace `bede818c` ran `harness_execute(hql_query, run)` 40 times, 34 syntax errors, zero validate calls, 279s wall-clock).

## Repair ladder

Max 3 attempts total (initial + 2 repairs). Semantic-preserving only — do NOT change the aggregate function, drop `group_by`, drop a predicate, change `order_by` direction, or downgrade the widget type on repair. If validate still fails after 3 attempts, skip the query with a note.

Attempt 1: submit original query.
Attempt 2: apply the returned `errors[]` **verbatim** (fix field names, casts, join predicates).
Attempt 3: retry only if attempt 2 was semantic-preserving.

## Worked flow

```
harness_execute(resource_type='hql_query', action='validate', body={query_string: <q>})
    on errors: repair per error (semantic-preserving, verbatim)
    re-validate the repaired query
    on green: harness_execute(resource_type='hql_query', action='run', body={query_string: <q>})
```

## Anti-patterns

- Do NOT call `harness_execute(hql_query, run)` without a prior validate on the same fingerprint.
- Do NOT paraphrase validate errors — apply the returned suggestions verbatim.
- Do NOT repair by changing semantics ("just drop the group_by") — surface the failure instead.
