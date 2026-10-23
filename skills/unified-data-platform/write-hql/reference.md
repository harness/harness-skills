# HQL Reference

## Syntax

- `find entity "type_id"` / `find event "type_id"` / `find metric "type_id"` / `find view "type_id"` (double quotes for type_ids)
- `filter field = 'value'` (single quotes for string values)
- `select {field1, field2}` (curly braces REQUIRED)
- `group_by field` and `order_by field` (underscore, NOT space — never use "group by" or "order by")
- Every non-aggregated SELECT column MUST appear in group_by — NO EXCEPTIONS
- Write queries as single lines (no newlines)
- Always include LIMIT for performance (100 for raw records, 20-50 for aggregates)

**Match object_kind to query type:**
- OBJECT_KIND_ENTITY → `find entity "type_id"`
- OBJECT_KIND_EVENT → `find event "type_id"`
- OBJECT_KIND_METRIC → `find metric "type_id"`
- OBJECT_KIND_VIEW → `find view "type_id"`
- OBJECT_KIND_RELATIONSHIP → NOT directly queryable. These are schema metadata describing known join paths between types. When planning JOINs, prefer relationship types as join hints when available, but other joins between types sharing a `connectorId` are also valid.

## Schema Compliance

1. ONLY use type_ids EXACTLY as listed in the queryable types response
2. ONLY use field names EXACTLY as listed under each type
3. NEVER invent, guess, or approximate type_ids or field names
4. If a field doesn't exist in the schema, DO NOT use it — find an alternative or state the limitation
5. Follow the HQL grammar — do NOT invent SQL-like syntax that isn't in the grammar
6. When unsure about syntax, use the simpler form from the grammar
7. NEVER say "100 failures found" from raw query — that's LIMIT truncation, not actual count
8. Use `count()` aggregation for accurate totals
9. Do NOT extrapolate or estimate beyond what the data shows

## Aggregation Functions

- `count()` — total count
- `avg(field)` — average
- `sum(field)` — sum
- `min(field)`, `max(field)` — min/max
- `distinct_count(field)` — unique count
- `median(field)` — median
- `p95(field)`, `p99(field)`, `percentile(field, n)` — percentiles
- `stddev(field)`, `variance(field)` — statistical spread

**Aggregation order:**
- **Prefer 1st order aggregates**: Use aggregation functions directly in the SELECT clause
- **2nd order aggregates** (`aggregate` operation): Only use when aggregating already-aggregated data
- Default to 1st order — only use the `aggregate` operation when explicitly needed for second-level aggregation

**GROUP_BY rule:** Every non-aggregated column in SELECT MUST appear in group_by.

WRONG: `select { pipeline_id, pipeline_name, stage_id, count() } | group_by pipeline_id, pipeline_name`
RIGHT: `select { pipeline_id, pipeline_name, count() } | group_by pipeline_id, pipeline_name`

**Match aggregate function to user intent:**
- "count" / "total" / "how many" → `count()`
- "rate" / "percentage" / "%" → arithmetic ratio: `(x * 100.0 / y) as rate`
- "average" / "mean" → `avg(field)`
- "sum" / "total value" → `sum(field)`
- "unique" / "distinct" → `distinct_count(field)`
- "median" / "middle" → `median(field)`
- "percentile" / "p95" / "p99" → `p95(field)`, `p99(field)`, `percentile(field, n)`
- "min" / "max" / "range" → `min(field)`, `max(field)`
- "variation" / "spread" → `stddev(field)`, `variance(field)`

## Type Casting and Time Filtering

Check the field's `field_type` (from Step 2 of the SKILL.md) and use the matching pattern:

**FIELD_TYPE_LONG (epoch millis):**
- Comparison: `cast(<epoch_millis_value> as long)`
- NEVER use `ago()`/`now()` as a filter value against LONG fields — they produce timestamps, not integers (e.g., `filter field >= ago(1h)` is WRONG for LONG fields)
- Day bucket: `(field / 86400000) * 86400000`
- Hour bucket: `(field / 3600000) * 3600000`
- Days between: `(field1 - field2) / 86400000`
- Hours between: `(field1 - field2) / 3600000`

**FIELD_TYPE_TIMESTAMP:**
- Comparison: `cast('<datetime_string>' as timestamp)` OR `ago()`/`now()` directly
- Day bucket: `date_trunc("day", field)`
- Hour bucket: `date_trunc("hour", field)`

## JOIN Syntax

**Discovering join paths:** OBJECT_KIND_RELATIONSHIP types describe known join paths between types. When available, prefer these as join hints — they indicate which fields to join on. However, relationship types are not exhaustive; any two types sharing a `connectorId` with matching fields can be joined.

Combining types from the SAME connector group only:

```
| [left|right|full] join sourceType "type_id" alias on alias.field = alias.field
```

- In join queries, ALL fields MUST be qualified as `alias.field` — unqualified fields fail
- ON clause: equality predicates only, joined with `and`; include tenant/account key when both types have it

**Examples:**

```
find entity "pipeline:pipeline_execution" pe | join entity "pipeline:stage_execution" se on se.plan_execution_id = pe.plan_execution_id and se.account_identifier = pe.account_identifier | select { pe.pipeline_name, se.service_name, se.env_name } | limit 100
```

```
find view "ci:stage_execution_summary_ci_table" a | left join view "ci:pipeline_execution_summary_ci" b on a.planexecutionid = b.planexecutionid | select { a.stagename, b.pipelinename, count() as total } | group_by a.stagename, b.pipelinename | order_by total desc | limit 100
```

**JOIN anti-patterns:**
- NEVER use unqualified fields in a join query
- NEVER join types from different connector groups
- NEVER use non-equality operators (>, <, IN) in ON clause

## General Anti-patterns

- NEVER group by unique IDs (plan_execution_id, entity_id, uuid)
- NEVER report LIMIT N results as "N total" — use `count()` for actual totals
- NEVER use spaces in `group by` / `order by` — always use `group_by`, `order_by`
- NEVER join types from different connector groups
- NEVER invent type_ids or field names not in the schema

## STO Notes

STO `severity_code` values are CASE SENSITIVE: Use `'Critical'`, `'High'`, `'Medium'`, `'Low'`, `'Info'` (exact capitalization).

## Canonical MCP surface names

Entity selection is governed by discovery, not by a hardcoded list here — the queryable-type listing for the account is authoritative. If a type is not in it, you cannot query it; if it is stale/deprecated, the platform excludes it from the listing. Do not maintain a private ban list.

The one thing this file does pin is the **names of the discovery tools themselves**, because these are frequently hallucinated. Use only the real surfaces:

| Hallucinated name | Real surface |
|---|---|
| `type-registry` | `harness_list(resource_type='kg_queryable_type_summary')` + `harness_get(resource_type='kg_type')` |
| `business-glossary` | no glossary API exists — use `sei_business_alignment` (team/product) or `cost_category` (CCM) |
| `kg_queryable_type` (bare) | `harness_get(resource_type='kg_type', resource_id, params={kind})` |
