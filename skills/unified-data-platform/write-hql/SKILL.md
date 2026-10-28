---
name: write-hql
description: >-
  Write, validate, and run HQL (Harness Query Language) queries against Harness data, and
  analyze pipeline, deployment, CI and security data with them. Use when asked to
  write, fix, explain, or validate an HQL query, create dashboard widget queries,
  find which types and fields can be queried, or answer "how many", "top N", trend,
  dashboard widget, or failure-rate questions over a time window or many runs. Do NOT use for the current state of one named pipeline run (use debug-pipeline)
  or for cloud cost totals (use analyze-costs). Trigger phrases: HQL, Harness Query Language,
  write a query, validate query, queryable types.
metadata:
  author: Harness
  version: 1.0.2
  mcp-server: harness-mcp-v2
  summary: Discover fields, then write, validate, and run dashboard-ready HQL queries
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2) with the knowledge-graph and semantic-layer toolsets enabled
---

# Write HQL

Write, validate, and run HQL queries against Harness data, primarily for dashboard widget creation. This skill teaches the query language, the type discovery workflow, and the validation loop. For non-dashboard multi-query analysis (overview, drill-down, synthesis), also follow [analysis-workflow.md](references/analysis-workflow.md).

## Instructions

### Step 0: Learn HQL syntax

Read the companion files in this skill directory before writing any queries:
- **`reference.md`** — practical examples, type casting rules, JOIN syntax, anti-patterns.
- **`references/patterns/*.md`** — worked query patterns per question shape (failure-diagnosis, build-time-analysis, bottleneck-analysis, flakiness, retry-signals, intermittent-vs-consistent, lint-first, batch).
- **`references/entity-reference/ci.md`** — CI-native field discipline (`stage_build_time` vs `duration`, `start_timestamp` vs `start_ts`).

Fetch the live grammar via `harness_get(resource_type='kg_grammar')` only when the reference files do not cover the syntax you need.

### Step 1: Discover queryable types (summaries only)

```
harness_list(resource_type='kg_queryable_type_summary')
```

You can filter by object kind to reduce the response:
```
harness_list(resource_type='kg_queryable_type_summary', kinds=['OBJECT_KIND_VIEW'])
```

This returns lightweight summaries: `identifier` (type_id for HQL), `name`, `description`, `kind` (OBJECT_KIND_*), `connectorId`, `tags`. Pick 1-5 types relevant to the user's question.

**IMPORTANT:** The only valid filter parameters are `kinds` (OBJECT_KIND_*) and `annotations`. Do NOT pass `filters`, `name`, `compact`, or any other made-up parameters — they are silently ignored and you will get the full unfiltered list.

Treat the returned list as authoritative and complete: if a type is not in it, you cannot query it. Do not guess or recall identifiers from earlier conversations, other accounts, or examples.

**Selection criteria:**
- Match by name to user intent
- For cost/billing → types with "ccm", "cost", "billing" in the name
- For pipelines/CI-CD → types with "pipeline", "stage", "execution" in the name
- For issues/tickets → types with "issue", "ticket", "jira", "sei" in the name
- For security → types with "sto", "vulnerability", "scan" in the name
- For audit/activity → types with "audit", "event", "activity" in the name
- For infrastructure → types with "kubernetes", "cloud", "infrastructure" in the name
- Consider type annotations to understand semantic purpose
- Prefer OBJECT_KIND_VIEW over OBJECT_KIND_ENTITY when both cover the same data
- Select 1-5 types that best match the user's query
- Note `connectorId` for each selected type — you need this for JOIN rules

### Step 2: Get field details for each selected type

For each type you selected in Step 1, fetch its full field metadata using the **semantic-layer** `kg_type` resource. **Always pass `params.kind` explicitly, using the exact `kind` value Step 1 returned for that identifier** — never omit it. If `kind` is omitted, `kg_type` silently defaults to `OBJECT_KIND_ENTITY`, which may not be the queryable type you selected in Step 1.

**List-first rule:** `resource_id` MUST be an `identifier` that appeared in a Step-1 `harness_list` response earlier in this session. Do not fetch a type by a guessed, memorized, or copied-from-example identifier. If you need a type you have not listed, run Step 1 first.

```
harness_get(resource_type='kg_type', resource_id='<identifier-from-Step-1>', params={kind: '<kind-from-Step-1>'})
```

`<identifier-from-Step-1>` and `<kind-from-Step-1>` are placeholders — substitute the exact `identifier` and `kind` values a Step-1 response returned. Do not invent literal type ids.

Make one call per selected type (1-5 types). Each returns a single type with its fields (~5-15KB).

From each response, note:
- Field names — use these exact names in HQL queries
- `field_type` values — especially `FIELD_TYPE_LONG` vs `FIELD_TYPE_TIMESTAMP` for time fields (see reference.md Type Casting section)
- Annotations — semantic hints about field purpose

### Step 3: Plan queries using connector groups

**JOIN CONSTRAINT:** You may ONLY join types that share the same `connectorId`. Types in different connector groups use different data sources and CANNOT be joined. When the user's question requires data from types in different connector groups, execute separate queries and correlate results in your analysis.

Group your selected types by connectorId:
- Types within the SAME connectorId CAN be JOINed in HQL
- Types in DIFFERENT connectorId groups require separate queries

### Step 4: Validate and fix

Always validate before executing:

```
harness_execute(resource_type='hql_query', action='validate',
                body={query_string: '<your HQL query>'})
```

**Apply repair suggestions verbatim.** Max 3 attempts (initial + 2 repairs). Repairs fix typos/syntax only — never drop filters, change aggregates, or alter ORDER BY direction. Unrepairable after 3 attempts → stop with a note. See `references/patterns/lint-first.md`.

Common fixes:
- Field name typos — check Step 2 field list
- Missing `group_by` for non-aggregated SELECT columns
- Wrong object kind prefix (entity vs event vs view)
- Unqualified fields in JOIN queries

### Step 5: Run

```
harness_execute(resource_type='hql_query', action='run',
                body={query_string: '<validated HQL query>', max_results: 100})
```

`timeout_ms` and `max_results` are optional. HQL is read-only, so running a query never changes data.

### Default HQL constraints

Assume generated HQL is for a dashboard widget unless the user explicitly asks for ad hoc analysis, a one-off query run, or a non-dashboard report. Unless the question is explicitly scope-agnostic or time-agnostic, every query must include:
1. **Scope**: an `account_identifier` filter, plus `org_identifier` and `project_identifier` when the user names an org or project (or has configured default org/project for the MCP server). If the user gives a Harness UI URL, take the scope from it: `/projects/<id>` → project scope; `/orgs/<id>` without `/projects/` → org scope; otherwise account scope. If scope is unclear, ask the user rather than guessing.
2. **Time window**: for dashboard widget queries, default to the dashboard predicates on the widget Time Field: `{time_field} >= ${start_time} and {time_field} <= ${end_time}`. Use `ago(...)` only for non-dashboard/ad hoc analysis. For non-dashboard recency, default to `ago(7d)` and do not exceed `ago(30d)` unless the user explicitly asks for a longer range and confirms they want to bypass this limit.
3. **Status filter**: `status = 'FAILED'` for failure-diagnosis questions.

### Dashboard widget time range predicates

When writing HQL for a dashboard widget, the query must include the dashboard time predicates on the widget's selected Time Field by default. Do not rely on the widget UI alone, and do not replace this with `ago(...)` unless the user is not building a dashboard widget.

Use this shape, substituting the discovered field name selected in the widget's Time Field control:

```
| filter <time_field> >= ${start_time} and <time_field> <= ${end_time}
```

Generic dashboard widget query shape:

```
find entity "{module}:{entity}" | filter {required_predicates} and {time_field} >= ${start_time} and {time_field} <= ${end_time} | select { {aggregate_expression} as {alias} }
```

Keep any required business predicates in the same filter as the dashboard time predicate.

When reviewing or sharing a dashboard query with a customer, check whether the query already includes the `${start_time}` and `${end_time}` predicate on the same field selected as the widget Time Field. If it is missing, suggest adding that predicate so the dashboard time range applies to the query.

### Query shape patterns

These files teach the **shape** of a query for a given question type — how to rank, join, aggregate, and window. They do **not** dictate which entity to use: the correct entity always comes from your Step-1/Step-2 discovery for this account. A "bottleneck" question may resolve to pipeline stages, CI stages, CCM cost, or a security scan queue depending on what discovery surfaces.

**Placeholder convention.** Worked queries in the pattern files are templates, not copy-paste queries. They use `{...}` placeholders you fill from discovery:
- `{module}:{entity}` — a queryable type_id. `{module}` is the domain the question resolves to (`pipeline`, `cd`, `ci`, `ccm`, `sto`, `chaos`, ...) and `{entity}` the specific type — both taken from your Step-1 listing, never assumed. Even `pipeline` is just one module; the same shape applies under any module whose discovery surfaced a matching entity.
- `{duration}`, `{start_time}`, `{status}`, ... — field names confirmed via Step-2 `kg_type` for the chosen entity (sibling entities diverge: `duration` vs `stage_build_time`, `start_ts` vs `start_timestamp`).

The transferable lesson is the structure around the placeholders (which aggregates, which joins, which filters) — not the placeholder values.

- `references/patterns/failure-diagnosis.md` — traverse an execution hierarchy to the failing leaf; filter to the failed rows.
- `references/patterns/build-time-analysis.md` — rank by duration on successful runs; pair `avg`/`p95`/`max`.
- `references/patterns/bottleneck-analysis.md` — rank sub-units by latency; percentiles over averages.
- `references/patterns/flakiness.md` — combine retry, FAIL-then-PASS, and marked-flake signals when the discovered entities expose them.
- `references/patterns/retry-signals.md` — attribute retries down a join chain using discovered join keys.
- `references/patterns/intermittent-vs-consistent.md` — classify by status distribution per group.
- `references/patterns/lint-first.md` — validate before execute, 3-attempt semantic-preserving repair ladder.
- `references/patterns/batch.md` — batching rules (≤20 validate, ≤10 execute).
- `references/entity-reference/ci.md` — CI-native field-name examples (illustrative; confirm via `kg_type`).

## Examples

### Write a query for failed runs

```
/write-hql
Write an HQL query for the pipelines that failed most often in the last 7 days in project my_proj.
```

Expected flow: list queryable types, pick the pipeline execution type, fetch its fields, build the query from `references/patterns/failure-diagnosis.md`, validate it, then run it.

### Fix a query that fails validation

```
/write-hql
This HQL fails validation, fix it: find entity "pipeline:pipeline_execution" | select {status, count()}
```

Expected flow: validate, read the errors, and repair syntax only (here, the missing `group_by status`).

### Find what data is available

```
/write-hql
Which types can I query for security issues, and what fields do they have?
```

## Performance Notes

- Start with `kg_queryable_type_summary`, not the grammar. Summaries are small; the grammar is large.
- Pass `kinds` on the list call to cut the response size.
- Fetch `kg_type` only for the 1-5 types you will use, one call per type.
- Always include a `limit`, and prefer aggregates over raw rows for large populations.
- Validate every query before running it. Batch validations as described in `references/patterns/batch.md`.

## Troubleshooting

### `kg_queryable_type_summary` or `hql_query` is not available

The MCP server is missing the `knowledge-graph` toolset. It is enabled by default; if `HARNESS_TOOLSETS` is set, make sure it includes `knowledge-graph` and `semantic-layer`.

### `kg_type` is not available

`kg_type` belongs to the `semantic-layer` toolset. Enable it alongside `knowledge-graph`.

### Empty type list or 401/403/404 from the query service

Check that the API key can read the account's data and that `HARNESS_BASE_URL` points at the right Harness instance. A 404 on the query service path means the gateway for that instance does not route `/query-service/`, or the query service is not enabled for the account.

### Validation keeps failing after 3 attempts

Stop and report the last error to the user. Do not drop filters or change aggregates to make the query pass.

### A field or type does not exist

Re-run Step 1 and Step 2. Types and fields differ between accounts, and sibling entities use different field names.
