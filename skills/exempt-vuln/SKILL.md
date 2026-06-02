---
name: exempt-vuln
description: >-
  Create Harness STO security exemptions (waivers) for vulnerabilities found by SAST, SCA, DAST,
  secret, container, or IaC scanners. Works from both entry points in the Harness UI: the
  Vulnerabilities tab of a specific pipeline execution (Target, Pipeline, or Project scope)
  and the All Issues page (Project scope only). Supports single creates with per-row error
  tolerance and bulk creates of up to 100 issues in one all-or-none transaction. The requester
  is derived automatically from the authenticated user.
  Use when a user wants to exempt a vulnerability, waive a CVE, suppress a security finding,
  mark a finding as a false positive, accept the risk, or exempt several vulnerabilities at
  once.
  Trigger phrases: exempt vuln, exempt vulnerability, exempt CVE, waive vulnerability, create
  exemption, suppress security issue, false positive, accept risk, ignore CVE, bulk exempt.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Exempt Vulnerability

Create a security exemption (waiver) for one or more Harness STO vulnerabilities. STO has two
places a user can request an exemption from, and each one allows a different set of scopes:

| Where the user is in the Harness UI | Scopes they can request |
|---|---|
| **Vulnerabilities tab** of a specific pipeline execution | This Project, This Pipeline, This Target |
| **All Issues** page (the project-wide baseline) | This Project only |

The reason for the difference is simple: rows on the All Issues page are aggregated across
executions and don't carry an `execution_id`, so the backend has no pipeline or target context
to attach a narrower scope to. Org- and Account-scoped exemptions are not created here at all;
they're produced later by approving an existing exemption at a higher scope (via
`harness_execute resource_type=security_exemption action=approve body={scope:'ORG'|'ACCOUNT'}`),
which is outside the scope of this skill.

## Instructions

### Step 1 — Find out where the user is starting from

Ask the user, in plain language:

> Which view are you in?
> 1. The **Vulnerabilities tab** for a specific pipeline execution, or
> 2. The **All Issues** page (the project-wide baseline view).
>
> If you have the URL handy, just paste it — I'll pull out the org, project, and execution from
> it automatically.

You also need:

- The **org and project**, unless they're already in session defaults or you can read them from a
  pasted URL.
- For the Vulnerabilities tab path: the **execution ID**, or any Harness URL that contains one.

A pasted Harness UI URL is always the fastest route. The MCP `url` parameter auto-extracts every
identifier in the path, so the user does not have to type anything else. The shapes to recognise:

| URL the user pastes | What it tells you | Which path |
|---|---|---|
| `…/sto/executions/{executionId}/pipeline` | The Vulnerabilities tab of one execution | **Vulnerabilities path** — extracts `org_id`, `project_id`, `execution_id` |
| `…/pipeline/orgs/{org}/projects/{project}/pipelines/{pipelineId}/executions/{executionId}/…` | A pipeline execution detail page | **Vulnerabilities path** — also extracts `pipeline_id` |
| `…/sto/issues` or `…/sto/issues/{issueId}` | The All Issues page | **All Issues path** — extracts `org_id`, `project_id` only |

If the user pastes a Vulnerabilities-tab URL, treat the request as the Vulnerabilities path no
matter how they phrased it. If they paste an All Issues URL, do not ask for an execution ID —
that view doesn't have one.

### Step 2 — List the issues so the user can pick

#### Show a small preview first, not the whole list

Chat is a narrow surface — a 50-row table is unreadable, and the user usually only cares about a
handful of issues. Start with a short preview, tell them the total, and let them ask for more or
narrow the filter.

The default opening move:

1. Ask `harness_list` for a small page (10 rows is a good default).
2. From the response, take **`total`** — the total number of matching issues in the project /
   execution — and decide what to show:
   - If `total` ≤ 10, show every row.
   - If `total` > 10, show **the first 5 sorted by severity** (Critical → High → Medium → Low),
     then say something like:
     > Showing 5 of {total} matching issues, sorted by severity. Tell me how to narrow this — for
     > example: "show 10 mediums", "only SAST", "search log4j", "show all highs" — or pick from
     > the list below.
3. If the user asks for more or narrows the filter, re-call `harness_list` with the new
   filters or a larger page size. Do not paginate manually unless the user asks.

#### Vulnerabilities tab (per-execution)

```
harness_list
  resource_type: "pipeline_security_issue"
  org_id: <org>
  project_id: <project>
  filters:
    execution_id: <execution_id>           # REQUIRED
    severity_codes: "Critical,High"        # optional, user-driven
    issue_types: "SCA,SAST"                # optional
    search: "<CVE or component>"           # optional
    include_exempted: false                # hide rows that already have an exemption
    page_size_existing: 10                 # small preview — bump only on user request
    page_size_new: 10
```

The response flattens the `existing` and `new` diff partitions into a single `items[]` and tags
each row with `_partition`. Each row exposes `issue_id` and `targetVariantName` (a display string
like `"nodegoat:master"`). It does **not** expose the raw `target_id` or `pipeline_id` — Step 3
covers how to look those up when the user picks a narrower scope.

#### All Issues page (baseline)

```
harness_list
  resource_type: "security_issue"
  org_id: <org>
  project_id: <project>
  filters:
    severity_codes: "Critical,High"
    issue_types: "SCA,SAST"
    search: "<CVE or component>"
    exemption_statuses: "None"             # hide rows that already have an exemption
    size: 10                               # small preview — bump only on user request
```

#### The selection prompt

When you ask the user which issues to exempt, always include three things in the same prompt:

1. **The total** (so they know what they're picking from).
2. **How to pick** — by row number or by pasting issue IDs.
3. **The per-batch limit** — the bulk endpoint accepts at most 100 issues per call, so a single
   selection cannot exceed that.

Phrase it conversationally, for example:

> Which issues would you like to exempt? Pick by number (e.g. `3`, `4-7`, `3,5,9`) or paste issue
> IDs. You can select up to **100 at a time** — that's the per-batch limit for bulk exemptions.
> If you want more than 100, narrow the filter first or split into multiple batches.

Do **not** offer "exempt all" as a shortcut. The selection should always be a deliberate list of
numbers or IDs — see the 100-issue cap in Step 5b for the full rationale.

### Step 3 — Pick the scope

#### From the Vulnerabilities tab

Offer one of:

- **This Project** — the exemption applies across every pipeline and target in the project.
- **This Pipeline** — it applies only when this issue shows up in one specific pipeline.
- **This Target** — it applies only to one repository, container, instance, or configuration.

Two rules the backend enforces, so this skill must enforce them too before calling
`harness_create`:

- `target_id` and `pipeline_id` are mutually exclusive on a single exemption. Never send both.
- For Project scope, send neither. The project is already implied by `project_id` on the request.

`pipeline_security_issue` rows do **not** carry `target_id` or `pipeline_id`, so you need to
resolve them yourself for the narrower scopes. Use the recipes below — do not poke at unrelated
endpoints.

##### Resolving `pipeline_id`

1. **If the user pasted a pipeline execution URL,** the URL extractor has already given you
   `pipeline_id`. Use it directly — do not look it up again.
2. **Otherwise** (you only have a raw `execution_id`), fetch the execution once:
   ```
   harness_get
     resource_type: "execution"
     resource_id:   <execution_id>
     org_id:        <org>
     project_id:    <project>
   ```
   Read `pipelineIdentifier` off the response.

Never list pipelines and search for a match. The execution-to-pipeline link is 1:1, and the
lookup above is constant-time.

##### Resolving `target_id`

Pull the scan steps for the same execution and build a small lookup map:

```
# 1. One call returns scanner + target metadata for every step in the execution.
harness_list
  resource_type: "pipeline_security_step"
  org_id: <org>
  project_id: <project>
  filters:
    execution_id: <same execution_id used for the issue list>

# 2. Build a map from the response:
#    key   = "<targetName>:<targetVariant>"   e.g. "nodegoat:master"
#    value = targetId                          (22-character Harness ID)
```

For each selected issue row, look its `targetVariantName` up in that map. The matching `targetId`
is what goes into `body.target_id` (single create) or each item's `target_id` (bulk create).

The `pipeline_security_issue` list response also embeds `_target_id_lookup_hint` and
`_pipeline_id_lookup_hint` fields that describe these same recipes — surface them verbatim to
the user if they ask why the extra call is needed.

##### Suggested call order

When the user starts from a URL, the cheapest deterministic plan is:

1. `harness_list pipeline_security_issue` — always, so the user can pick.
2. `harness_list pipeline_security_step` — only if This Target scope is in play.
3. `harness_get execution` — only if This Pipeline scope is in play and you don't already have
   `pipeline_id` from the URL.
4. `harness_create security_exemption` or `security_exemption_bulk`.

That's three reads at most, plus one write. Never more.

#### From the All Issues page

The only scope available is **This Project**. If the user asks for This Pipeline or This Target,
explain the limitation and wait for them to choose — don't quietly fall back to Project scope:

> The All Issues page doesn't know which execution surfaced this issue, so I can only create a
> Project-scoped exemption from here. If you need a narrower scope, open the **Vulnerabilities
> tab** for a recent execution of the pipeline that scanned this target, send me that URL or
> execution ID, and I'll scope the exemption to just that pipeline or target.

### Step 4 — Collect the exemption fields

| Field | Required | Notes |
|---|---|---|
| `issue_id` | yes | From the selected row. |
| `type` | yes | One of: `Compensating Controls`, `Acceptable Use`, `Acceptable Risk`, `False Positive`, `Fix Unavailable`, `Other`. These match the choices in the Harness UI's Request Exemption dialog. |
| `reason` | yes | A short justification (max 1024 characters). Ask if the user didn't give one — never invent it. |
| `duration_days` | no | Defaults to 30. Confirm if the user mentioned a different number. |
| `link` | no | A ticket URL (Jira, GitHub issue, etc.) if the user mentions one. |
| `occurrences` | no | A list of specific occurrence IDs. Use only when the user wants to exempt some occurrences and not the whole issue. |
| `scan_id` | no | Exempts every occurrence found in one scan. Requires This Target scope. |

`requester_id` is filled in automatically from the authenticated PAT — never ask the user for it.

If you ever need the full schema, run `harness_describe(resource_type="security_exemption")`. Do
the same if a create call returns a missing-field error.

### Step 5 — Confirm, then create (single)

Echo the payload back to the user in plain text before calling `harness_create`. Use the same
shape every time so users learn to scan it quickly:

```
About to create this exemption:
  Issue:    <id>
  Scope:    This Project | This Pipeline (<pipeline_id>) | This Target (<target_id>)
  Type:     <type>
  Reason:   "<reason>"
  Duration: <n> days
Proceed? (yes/no)
```

On `yes`, call:

```
harness_create
  resource_type: "security_exemption"
  org_id:        <org>
  project_id:    <project>
  body:
    issue_id:      <id>
    type:          <type>
    reason:        <reason>
    duration_days: <n>            # optional
    # exactly one of the next two, or NEITHER for This Project scope:
    pipeline_id:   <pipeline_id>  # This Pipeline scope only
    target_id:     <target_id>    # This Target scope only
    link:          <url>          # optional
    occurrences:   [ids]          # optional
    scan_id:       <scan_id>      # optional, This Target scope only
```

### Step 5b — When the user wants to exempt more than one issue

Pick one of the two paths below and tell the user which one you're taking and why:

| Path | Use when | How to call it | Behaviour |
|---|---|---|---|
| **Single** (loop) | Items need different `type`, `reason`, or `duration_days`, or the user wants every row to succeed or fail on its own. | One `harness_create resource_type=security_exemption` per row. | Each row is its own transaction. Row 3 can succeed even if row 4 fails. |
| **Bulk** | Every item shares the same `type`, `reason`, and `duration_days` — even if the scope differs per item. | One `harness_create resource_type=security_exemption_bulk` with up to 100 items. | **All-or-none.** If any item fails validation or insert, the whole batch is rolled back. One DB transaction, one audit row. |

**Default to bulk** when two or more issues share the batch-level fields. This is the common
case ("exempt all these Log4j highs"). Per-item scope can still vary — a single bulk call can
mix This Project, This Pipeline, and This Target items as long as the type and reason are the
same.

**Default to single** when items have different justifications or types, or when the user
explicitly wants per-row tolerance.

##### What's uniform per bulk batch vs what can vary per item

| Field | Where it sits in the body | Must be identical for every item? |
|---|---|---|
| `org_id`, `project_id` | request scope | Yes — one batch = one project. |
| `type`, `reason`, `duration_days`, `link`, `expiration` | top-level body | Yes — one value applied to all items. |
| `issue_id` | per item | One per item, required. |
| `target_id` *or* `pipeline_id` | per item | Each item picks its own scope. |
| `scan_id`, `occurrences`, `search` | per item | Independent per item. |

If the user wants different `type` or `reason` values per row, bulk cannot encode that — use
single creates.

##### The 100-issue cap — never offer "exempt all" without checking

The bulk endpoint accepts at most 100 items per call. The MCP preflight enforces this and will
throw `items must contain at most 100 entries` before the request is sent. Apply these rules:

1. **Count before you offer.** Always read `total` from the prior `harness_list` response. If
   `total > 100`, do not present "exempt all" as a default. Show the count and ask the user to
   either narrow the filter (severity, scanner, search term, target) or explicitly opt into
   chunking.
2. **Chunk only on explicit opt-in.** If the user confirms "yes, exempt all" for more than 100
   issues, split the list into chunks of 100 or fewer and send one bulk call per chunk. Each
   chunk is its own all-or-none transaction — a failed chunk does not roll back successful ones,
   and a successful chunk does not retry the failed one. Report `succeeded` / `failed` counts
   per chunk in the summary.
3. **Never silently truncate.** Dropping issues to fit under 100 is a worse outcome than the
   API error. Always ask.
4. **Refuse vague "all" requests.** If the user says "exempt all the highs" without seeing the
   count, list the candidates first (page one is enough) and show the `total`. Wait for them to
   acknowledge the number before proceeding.

When you select rows for the user, ask them to choose by **number or issue ID**, not by typing
"all". Phrase the prompt as something like:

> Which issues would you like to exempt? Pick by number (e.g. `1,3,5-7`) or paste issue IDs.

If the user still says "all" and the count is over 100, surface the rule from point 1 above.

##### Bulk call shape

```
harness_create
  resource_type: "security_exemption_bulk"
  org_id:        <org>
  project_id:    <project>
  body:
    type:          <type>          # applied to every item
    reason:        <reason>        # applied to every item
    duration_days: <n>             # optional, default 30, applied to every item
    link:          <url>           # optional, applied to every item
    items:                         # 1..100 entries
      - issue_id: <id1>
        # per item, optional: target_id XOR pipeline_id, scan_id, occurrences, search
      - issue_id: <id2>
        pipeline_id: <pipeline_id>
      - issue_id: <id3>
        target_id: <target_id>
```

Per-item rules:

- `target_id` and `pipeline_id` are mutually exclusive within a single item.
- From the All Issues page, no item may carry `target_id` or `pipeline_id` — the whole batch is
  Project-scoped.
- From the Vulnerabilities tab, each item picks its own scope independently.

##### Reading the bulk response

The response carries a top-level `status` banner. Surface it verbatim and react accordingly:

| `status` | What it means | What to do |
|---|---|---|
| `ALL_SUCCEEDED` | Every item was created. | Report each `{issueId, id}` and note that all are Pending approval. |
| `ALL_FAILED` | The whole batch was rolled back, and every item carries the same error. | Surface `results[0].error`, fix the root cause, then resubmit the **full corrected list** — never retry only the failed rows. |
| `MIXED_UNEXPECTED` | The server returned both successes and failures, which violates the all-or-none contract. | Treat this as a server bug. Show the raw `results[]`, do not auto-retry. |
| `EMPTY` | No results in the response. | Treat as a failure; check that the request actually included items. |

Typical causes of `ALL_FAILED` are: an unknown `issue_id`, no scan found for the issue within
the project scope, a mutual-exclusion slip, or a duplicate exemption. `results[0].error` names
the actual cause.

If a single bad item is poisoning a large batch and the user wants to know which one, you may
fall back to single creates to isolate it — but ask first; don't switch strategies silently.

### Step 6 — Report what happened

For each created exemption, return:

- `exemption_id`
- `status` — this will be `Pending` until someone with the right permissions approves it.
  Approval is a separate workflow and is outside the scope of this skill.
- A deep link to the project's Exemptions page:
  `/ng/account/{accountId}/all/orgs/{org}/projects/{project}/sto/exemptions`

If any create call failed, surface the API error verbatim — it's almost always a
mutual-exclusion violation or a missing field, and the message tells the user exactly what to
fix.

## Examples

### Example 1 — One CVE, This Pipeline scope, from a specific execution

User: *"Exempt CVE-2024-1234 from execution `ehsPKtczTRO5CUDAt-NR` for that pipeline only.
False positive — already patched in our fork."*

1. Confirm org and project from session defaults.
2. `harness_list pipeline_security_issue` with `execution_id` and `search: "CVE-2024-1234"`.
3. Pick the matching row and note its `issue_id`.
4. Resolve `pipeline_id` — either from the pasted URL, or via `harness_get execution`.
5. Echo the confirmation block, wait for `yes`, then `harness_create` with
   `body: { issue_id, type: "False Positive", reason: "Patched in our fork — see PR #422", pipeline_id }`.

### Example 2 — Three Log4j highs from the All Issues page, This Project scope, bulk

User: *"From the All Issues page, suppress these three high-severity Log4j findings for 90
days. Acceptable risk — we've mitigated at the gateway."*

1. `harness_list security_issue` with `severity_codes: "High"`, `search: "log4j"`.
2. User picks three `issue_id`s.
3. All Issues path → This Project scope (no `target_id` or `pipeline_id` on any item).
4. All three share batch-level fields → bulk.
5. One `harness_create resource_type=security_exemption_bulk` with
   `body: { type: "Acceptable Risk", reason: "Mitigated at API gateway WAF — ticket SEC-880", duration_days: 90, items: [{issue_id:"i1"}, {issue_id:"i2"}, {issue_id:"i3"}] }`.
6. Expect `status: ALL_SUCCEEDED`; report the three returned exemption IDs.

### Example 2b — Mixed-scope bulk from the Vulnerabilities tab

User: *"From execution `ehsPKtczTRO5CUDAt-NR`, exempt these five Critical issues — the first
two for the whole project, the next two only on this pipeline, the last one only on the
`api-gateway` target. False positive across the board."*

1. `harness_list pipeline_security_issue` with `execution_id` and `severity_codes: "Critical"`.
2. `harness_list pipeline_security_step` (same execution) to resolve `target_id` for the
   `api-gateway` row.
3. User picks the five rows.
4. One bulk call — all five share `type` and `reason`, and per-item scope is encoded per row:
   ```
   harness_create resource_type=security_exemption_bulk body:
     type: "False Positive"
     reason: "False positive — see triage doc #441"
     items:
       - { issue_id: i1 }                              # This Project
       - { issue_id: i2 }                              # This Project
       - { issue_id: i3, pipeline_id: <pipelineId> }   # This Pipeline
       - { issue_id: i4, pipeline_id: <pipelineId> }   # This Pipeline
       - { issue_id: i5, target_id:   <targetId> }     # This Target
   ```

### Example 2c — Two CVEs with different exemption types

User: *"Exempt these two CVEs — the Log4j one is a False Positive, the Spring4Shell one is
Acceptable Risk."*

The two items need different `type` values, which bulk cannot encode. Use the single path: two
sequential `harness_create resource_type=security_exemption` calls. Splitting into two batches
of one is just the single path with extra ceremony.

### Example 3 — User asks for This Target scope from the All Issues page

User: *"From the All Issues page, exempt this XSS finding for the `web-frontend` target only."*

Don't quietly downgrade. Say:

> The All Issues page doesn't know which execution found this issue, so I can only create a
> Project-scoped exemption from here. Two options:
> 1. Create it as a This Project exemption now, or
> 2. Open the Vulnerabilities tab for a recent execution that scanned `web-frontend`, send me
>    that URL or execution ID, and I'll scope it to just that target.

### Example 4 — Mutual-exclusion error recovery

If the user supplies both `pipeline_id` and `target_id` for the same exemption, push back before
calling the API:

> An exemption can be scoped to one pipeline **or** one target, not both. Pick one: **This
> Pipeline** applies across every target this pipeline scans, while **This Target** applies
> across every pipeline that scans this target.

## Performance Notes

- `pipeline_security_issue` uses diff pagination — `page_existing` / `page_size_existing` and
  `page_new` / `page_size_new` are independent counters. Open with a small preview (10 of each)
  and only bump the size when the user asks for more or narrows the filter. The response always
  reports the partition-aware `total`, so you can show "5 of 19" without paging further.
- `security_issue` uses standard pagination (`page` / `size`). Same pattern — start with `size:
  10`, surface `total`, expand on request.
- Filter out already-exempted noise up front: pass `include_exempted: false` on
  `pipeline_security_issue`, or `exemption_statuses: "None"` on `security_issue`.
- Single create is one POST per issue. The MCP server marks it as
  `risk: high_write, retryPolicy: do_not_retry` — surface failures to the user instead of
  auto-retrying.
- Bulk create is one POST for up to 100 items, producing one database transaction and one audit
  row. At 100 items, that's roughly 5 DB round-trips vs ~400 with a loop of singles (see
  `sto-core/docs/STO-8977-bulk-exemption-api.md`). Prefer bulk whenever two or more items share
  the batch-level fields.
- Bulk is all-or-none. Never retry only the failed rows from an `ALL_FAILED` or
  `MIXED_UNEXPECTED` response — resubmit the full corrected list instead.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Missing required fields for security_exemption: issue_id, type, reason` | A required field is absent from `body`. | Ask the user — never invent a `reason` or default a `type`. |
| API error: `targetId` cannot be combined with `pipelineId` / `projectId` | Both scope fields were sent on one exemption. | Pick exactly one — see the rules in Step 3. |
| List error: `account scope not supported` | The caller passed `resource_scope='account'` or `'org'` when listing exemptions. | `security_exemption` is always listed at project scope. Those keywords are *approval* scopes (used with `harness_execute`), not list scopes. Remove the override and re-list. |
| A new exemption shows up as `Approved` immediately | The requester's RBAC grants auto-approval at that scope. | This is working as designed; mention it in the report. |
| `getCurrentUserId` failure | The PAT-derived user lookup failed (network or auth). | Surface the error verbatim — never fabricate an ID. Check that `HARNESS_API_KEY` is still valid. |
| User asks for Org- or Account-scope on creation | The create endpoint can't do that. | Create at This Project scope, then promote it via `harness_execute resource_type=security_exemption action=approve body={scope:'ORG'|'ACCOUNT'}`. That flow is outside this skill. |
| User started on the All Issues page but now wants This Pipeline or This Target | The All Issues path is Project-only by design. | Switch to the Vulnerabilities tab path with a relevant `execution_id`. |
| The agent keeps hunting for `target_id` on issue rows | `pipeline_security_issue` doesn't expose `target_id` — only `targetVariantName` (a display string). | Call `harness_list pipeline_security_step` once with the same `execution_id`, build a `{targetName:targetVariant → targetId}` map, then look up each row's `targetVariantName`. The list response embeds `_target_id_lookup_hint` with this same recipe. |
| Bulk response `status: ALL_FAILED` | One or more items failed validation or insert; the whole batch was rolled back per the all-or-none contract. | Read `results[0].error` for the real cause (unknown `issue_id`, no matching scan in scope, mutual-exclusion slip, duplicate exemption). Fix it and resubmit the **full** corrected list — never retry only the failed rows. |
| Bulk response `status: MIXED_UNEXPECTED` | The server returned both successes and failures, which violates the all-or-none contract. | Treat as a server-side bug. Show the raw `results[]`, do not auto-retry. Fall back to single creates for the failed items only after the user acknowledges. |
| Preflight error: `items must contain at most 100 entries` | The caller exceeded the per-batch limit. | Split into multiple bulk calls of 100 or fewer items each. **Prevent this** by checking `total` from the prior list before offering "exempt all" — see the 100-issue cap in Step 5b. Never silently truncate. |
| Preflight error: `items[N].issue_id` or `items[N] sets both target_id and pipeline_id` | One item in the batch is malformed. | The index in the error message tells you which item. Fix that one, then resubmit the full list. |
