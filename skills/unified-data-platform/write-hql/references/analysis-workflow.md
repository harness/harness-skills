# Analysis Workflow

Use this workflow when a question needs history or aggregation over more than one run, a time window, or a population of entities: pipeline errors, deployment trends, service dependencies, blast radius, security issues, "how many", "top N", rates, comparisons.

## When this applies

- **Across runs or a population** ("why do our pipelines keep failing", "top 10 slowest stages this month", "deployment trend by service"): use HQL as described here.
- **One named entity right now** ("why did this run fail", "what is the status of pipeline X"): not this workflow. Use `harness_diagnose`, `harness_status` or `harness_get` on that entity.
- **Cloud cost totals and billing**: not this workflow. Use the cost skill. Cost is in scope here only when attributed to DevOps entities through a join (for example cost per pipeline) and discovery surfaces a cost type in the same connector group.

Words like "keep", "always", "lately", "recent" and "trend" signal multiple runs.

## Pre-flight (mandatory before authoring any HQL)

1. `harness_list(resource_type='kg_queryable_type_summary', kinds=['OBJECT_KIND_ENTITY', 'OBJECT_KIND_EVENT'])` to list the types available for this account. Treat the result as authoritative.
2. For each type you plan to query: `harness_get(resource_type='kg_type', resource_id='<identifier>', params={kind: '<kind>'})` to get exact field names.
3. Use `kg_related_type` only when you need to join, not for every type.

Rules:
- Do not omit `kinds`; an unconstrained list is large.
- Do not guess or recall type identifiers. Only use identifiers returned by the list call in this session.
- Do not carry a private list of "good" or "banned" entities. Pick the starting entity from what discovery surfaces for the question.

## Scope

Establish scope before querying. If the user gives a Harness UI URL, take the most specific scope from it:

- URL contains `/projects/PROJECT_ID`: filter `account_identifier`, `org_identifier` and `project_identifier`.
- URL contains `/orgs/ORG_ID` but no `/projects/` segment: filter `account_identifier` and `org_identifier`.
- Account-level URL only: filter `account_identifier`.

Without a URL, use the org and project the user names, or the MCP server's configured defaults. If scope is unclear, ask. Use the most specific scope unless the user explicitly asks for a broader one ("across all projects").

Example for `.../account/ABC/orgs/default/projects/my_proj/overview`:

```
account_identifier = 'ABC' and org_identifier = 'default' and project_identifier = 'my_proj'
```

Do not add `module = '...'` to a query unless the user explicitly names the module ("CI pipelines only").

## Time filtering

Queries are live, so use `ago()` and `now()` for ranges: `ago(1d)`, `ago(7d)`, `ago(1M)`, `ago(12M)`. Default to `ago(7d)` when the question implies recency; do not exceed `ago(30d)` unless the user asks for a longer range and confirms.

Check the field type first (from `kg_type`):
- `FIELD_TYPE_TIMESTAMP`: use `ago()` and `now()` directly.
- `FIELD_TYPE_LONG` (epoch milliseconds): do not use `ago()`. Use epoch arithmetic; see the Type Casting section of [reference.md](../reference.md).

## Execute in rounds

```
Progress:
- [ ] Pre-flight done (types and field names confirmed)
- [ ] Round 1: 2-3 independent overview queries
- [ ] Round 2: 1-2 drill-down queries based on Round 1
- [ ] Round 3: only if the question is still unanswered
- [ ] Findings and follow-ups summarized
```

Validate, then run each query:

```
harness_execute(resource_type='hql_query', action='validate', body={query_string: 'HQL here'})
harness_execute(resource_type='hql_query', action='run', body={query_string: 'HQL here'})
```

Illustrative shape: top failing pipelines, project scope, last 7 days. HQL is pipe-delimited and written as a single line. Resolve the real type id and field names from pre-flight; do not copy identifiers verbatim:

```hql
find entity "pipeline:pipeline_execution" | filter account_identifier = 'ABC' and org_identifier = 'default' and project_identifier = 'my_proj' and status = 'FAILED' and start_ts >= ago(7d) | select { pipeline_identifier, count() as fail_count } | group_by pipeline_identifier | order_by fail_count desc | limit 20
```

For joins, filter on the failing leaf and keep the tenant predicate on each join clause. See [reference.md](../reference.md) and the worked joins in `patterns/`.

- **Round 1, overview:** 2-3 independent queries for totals, distributions and rates. They must not depend on each other.
- **Round 2, drill-down:** 1-2 queries based on Round 1, such as error details for the top failing pipeline.
- **Round 3:** only if Rounds 1-2 leave the question unanswered.

## Query strategy

| Question type | HQL approach |
|---|---|
| "How many X?" / "total" | `count()` aggregation |
| "Distribution" / "breakdown" | `group_by` + `count()` |
| "Rate" / "percentage" | `(x * 100.0 / y) as rate` |
| "Show me X" / "details" | Raw records with filters |
| "Trend over time" | `date_trunc("day", ts) as day` + `group_by day` |
| "Top N" / "worst" | Aggregation + `order_by desc` + `limit N` |
| "X with Y details" | JOIN types sharing a connector |

## Retry and flakiness signals

Use all four before reporting "no flakiness":

| Signal | Entity.field |
|---|---|
| Retry evidence | `pipeline:step_execution.is_retried` |
| Retry chain | `pipeline:step_execution.retry_ids` |
| Test-level flake | `ci:test_execution.result` (FAIL-then-PASS) |
| Marked flake | `ci:test_marking.flaky_status` |

See [flakiness.md](patterns/flakiness.md) and [retry-signals.md](patterns/retry-signals.md) for worked join queries. CI-native entities use different field names than `pipeline:*` (for example `stage_build_time` instead of `duration`); see [ci.md](entity-reference/ci.md).

## Synthesize

Summarize with the key numbers in bold, then give 3-5 follow-up questions and actionable suggestions. Always state the scope and time window the numbers cover.

## Iteration discipline

- Budget: 3-6 queries in total across all rounds.
- Stop if 2 consecutive queries return 0 rows.
- Stop when 3-5 useful insights are gathered.
- If validation fails, apply the repair suggestions verbatim and re-validate (3 attempts at most). Repairs fix typos and syntax only; never drop filters, change aggregates, or swap chart types.

## Anti-patterns

- Never group by unique IDs (plan_execution_id, entity_id, uuid).
- Never report LIMIT N results as "N total"; use `count()` for actual totals.
- Never use spaces in `group by` or `order by`; always use `group_by` and `order_by`.
- Never join types from different connector groups.
- Never invent type ids or field names that are not in the schema.
