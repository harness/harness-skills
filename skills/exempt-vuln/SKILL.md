---
name: exempt-vuln
description: >-
  Create Harness STO security exemptions (waivers) for vulnerabilities from SAST, SCA, DAST,
  secret, container, or IaC scanners. Supports both entry points: the per-execution Pipeline
  Security (Vuln) tab — scoped to Target, Pipeline, or Project — and the cross-execution All
  Issues page (baseline), Project-scope only. Supports single (per-row error tolerance) and
  bulk (up to 100 issues, one audit row, all-or-none) creation. Auto-derives the requester
  from the authenticated user.
  Use when asked to exempt a vulnerability, waive a CVE, suppress a security issue, mark a
  finding as false positive, accept the risk, or bulk-exempt multiple vulnerabilities.
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

Create a security exemption (waiver) for a Harness STO vulnerability. The skill enforces the
two scope envelopes the STO backend supports based on **where the user is creating the
exemption from**:

| Entry point | Where the user is | Allowed exemption scopes |
|---|---|---|
| **Pipeline Security / Vuln tab** | Looking at issues for ONE pipeline execution | `Project`, `Pipeline`, `Target` |
| **All Issues** | Looking at the cross-execution baseline issues page | `Project` only |

The asymmetry is structural: All Issues rows do not carry an `execution_id`, so the backend has
no pipeline/target context to anchor a narrower scope. Account- and Org-scoped exemptions are
**not** created directly — they are reached by approving an existing exemption with `scope:
'ORG'` or `scope: 'ACCOUNT'` (see the `/configure-repo-scan` and Harness `security_exemption`
`promote` action). This skill only creates the initial exemption.

## Instructions

### Step 1 — Establish entry point and scope

Ask the user (do NOT guess):

1. **Where are you creating this exemption from?**
   - `Vuln tab for a specific pipeline execution` → Branch A
   - `All Issues page (baseline)` → Branch B
2. **Org and project** (skip if already known).
3. For Branch A: the **execution ID** (or the pipeline execution URL).

**URL-driven scope resolution.** All Harness UI URLs encode `accountId`, `orgIdentifier`, and
`projectIdentifier` in the path — the MCP `url` parameter auto-extracts them, so the user does
not need to type org/project separately. Recognize and accept:

| URL the user pastes | What it identifies | Branch |
|---|---|---|
| `…/sto/executions/{executionId}/pipeline` | Pipeline Security (Vuln tab) of one execution | **A** — extracts `org_id`, `project_id`, `executionId` |
| `…/pipeline/orgs/{org}/projects/{project}/pipelines/{pipelineId}/executions/{executionId}/…` | A pipeline execution | **A** — extracts `org_id`, `project_id`, `executionId` |
| `…/sto/issues` or `…/sto/issues/{issueId}` | The All Issues / baseline page | **B** — extracts `org_id`, `project_id` (no execution context) |

If the user pastes an All Issues URL, the skill already has `org_id` + `project_id` — only ask
for the issue identifier(s) or filter criteria. If the user mentions "all issues" / "baseline"
without a URL, ask for org and project (or fall back to session defaults). Either way, treat
the request as Branch B and do **not** ask for an execution ID — the All Issues view does not
have one.

If the user pastes a Pipeline Execution or `…/sto/executions/{executionId}/pipeline` URL,
treat the request as Branch A regardless of how they phrased it.

### Step 2 — List issues for selection

#### Branch A — Pipeline Security (per-execution)

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
    include_exempted: false                # optional — set false to hide already-exempted rows
    page_size_existing: 100
    page_size_new: 100
```

The response flattens `existing` + `new` partitions into `items[]` and tags each row with
`_partition`. Each item exposes `issue_id`, plus the per-execution `pipelineId` and
`targetId` you'll need for narrower scopes.

#### Branch B — All Issues (baseline)

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
```

Present the matching rows back to the user with: `issue_id`, severity, title/CVE, component,
target (if shown), and exemption status. Ask which issues to exempt.

### Step 3 — Choose exemption scope

#### Branch A scope prompt

Ask the user to pick **one** of:

- `Project` — applies to this issue across every pipeline and target in the project.
- `Pipeline` — applies only when this issue surfaces from the chosen pipeline. Use the
  `pipelineId` from the selected `pipeline_security_issue` row (or ask the user which pipeline).
- `Target` — applies only to the chosen target (repository / container / instance /
  configuration). See the recipe below — the `target_id` is NOT on the issue row.

##### Resolving `pipeline_id` and `target_id` (REQUIRED recipes)

`pipeline_security_issue` rows expose `targetVariantName` (a display string like
`"nodegoat:master"`) — they do **not** carry a raw `target_id` OR `pipeline_id`. Do not
chase these IDs through unrelated endpoints (`security_issue_filter`, `harness_get` on the
issue, etc.). Use the deterministic two-source recipe below.

###### `pipeline_id` (for Pipeline-scope exemptions)

Source priority — pick the first one that applies:

1. **From the URL the user already pasted.** Harness pipeline execution URLs encode
   `…/pipelines/{pipelineId}/executions/{executionId}/…`. The URL extractor in
   `harness_list` / `harness_get` auto-extracts `pipeline_id` alongside `execution_id`,
   `org_id`, and `project_id`. If you accepted a URL in Step 1, you already have
   `pipeline_id` — do not look it up again.
2. **Lookup via the execution itself** (fallback when the user gave only a raw
   `execution_id`):
   ```
   harness_get
     resource_type: "execution"
     resource_id:   <execution_id>
     org_id:        <org>
     project_id:    <project>
   ```
   Read `pipelineIdentifier` (or `pipelineId`) off the response. One call, deterministic.

Never iterate through `harness_list resource_type=pipeline` searching for a match — the
execution → pipeline link is 1:1 and the lookup above is constant-time.

###### `target_id` (for Target-scope exemptions)

The canonical source is `pipeline_security_step` for the same execution:

```
# 1. List the steps (one call, returns scanner + target metadata for every step).
harness_list
  resource_type: "pipeline_security_step"
  org_id: <org>
  project_id: <project>
  filters:
    execution_id: <same execution_id used for issues>

# 2. Build a lookup map from the response:
#    key   = "<targetName>:<targetVariant>"  (e.g. "nodegoat:master")
#    value = targetId                         (the 22-char Harness ID you need)
```

Then for each selected issue row, look its `targetVariantName` up in that map → that's
the `target_id` to pass as `body.target_id` (single create) or per-item `target_id`
(bulk create).

The first response from `harness_list resource_type=pipeline_security_issue` includes a
`_target_id_lookup_hint` field spelling out this recipe — surface it to the user if
they ask why an extra call is needed.

###### Suggested call order for Branch A

When the user picks any scope from the Vuln tab, the cheapest deterministic plan is:

1. `harness_list pipeline_security_issue` (selection list — required regardless of scope).
2. If Target scope is possible: `harness_list pipeline_security_step` (one call, builds
   the target map).
3. If Pipeline scope is possible AND no URL was pasted: `harness_get execution` (one call).
4. `harness_create security_exemption` or `security_exemption_bulk`.

Three list/get calls + one create. Never more.

Hard rules (enforced before calling `harness_create`):

- `target_id` and `pipeline_id` are **mutually exclusive**. Never pass both.
- `target_id` is also mutually exclusive with explicit project scoping; the backend treats
  presence of `target_id` as a target-scope intent.
- For Project scope, do not pass either `target_id` or `pipeline_id` — the project comes from
  `project_id` on the request scope.

#### Branch B scope

Force `Project` scope. If the user asks for Pipeline or Target scope, explain:
> "Target/Pipeline-scoped exemptions can only be created from the Pipeline Security view
> of a specific execution, because the All Issues view does not carry execution context.
> Either I can create this as a Project-scope exemption now, or you can re-run the request
> with a specific pipeline execution ID and I'll scope it narrower."

Wait for a decision — do not silently downgrade.

### Step 4 — Collect required exemption fields

For every create call:

| Field | Required | Notes |
|---|---|---|
| `issue_id` | yes | From the selected row. |
| `type` | yes | One of: `Compensating Controls`, `Acceptable Use`, `Acceptable Risk`, `False Positive`, `Fix Unavailable`, `Other`. |
| `reason` | yes | Free text justification, max 1024 chars. Ask if the user did not provide one — do not invent. |
| `duration_days` | no | Defaults to 30. Confirm if the user mentioned a different duration. |
| `link` | no | Ticket URL (Jira / GitHub issue / etc.) if the user mentions one. |
| `occurrences` | no | Array of occurrence IDs. Use only when the user wants to exempt specific occurrences and not the whole issue. |
| `scan_id` | no | Exempts all occurrences from one scan. Requires Target scope. |

`requester_id` is auto-derived from the authenticated PAT by the MCP server — **never** ask the
user for it.

Run `harness_describe(resource_type="security_exemption")` if the user asks for the full
schema or if a create call returns a missing-field error.

### Step 5 — Confirm and create

Echo the exact payload back to the user for confirmation before calling `harness_create`:

```
About to create exemption:
  issue_id:       <id>
  scope:          Project | Pipeline (<pipeline_id>) | Target (<target_id>)
  type:           <type>
  reason:         "<reason>"
  duration_days:  <n>
Proceed? (yes/no)
```

On confirmation, call:

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
    # exactly one of the following, or NEITHER for Project scope:
    pipeline_id:   <pipeline_id>  # Pipeline scope only
    target_id:     <target_id>    # Target scope only
    link:          <url>          # optional
    occurrences:   [ids]          # optional
    scan_id:       <scan_id>      # optional, Target scope only
```

### Step 5b — Multi-issue requests: pick single vs bulk

When the user wants to exempt **two or more** issues, decide between two paths and tell the
user which one you're taking:

| Path | Use when | Tool call | Semantics |
|---|---|---|---|
| **Single** (loop one `harness_create` per issue) | The user wants per-issue success/failure independence, mixes scopes (some Pipeline, some Target), or each issue needs a different `reason`/`type`. | `harness_create resource_type=security_exemption` per row | Each row is an independent transaction. Row 3 can succeed even if row 4 fails. |
| **Bulk** (one `harness_create` with `resource_type=security_exemption_bulk`) | The user wants all issues exempted under the **same** `type`, `reason`, and `duration_days`, in a single audit row, and accepts all-or-none semantics. | `harness_create resource_type=security_exemption_bulk body={type, reason, items:[…]}` | **All-or-none** — if ANY item fails validation or DB insert, the whole batch is rolled back. No partial state. |

Default to **bulk** when ≥2 issues share the same `type` + `reason` (the common case for
"exempt all these Log4j Highs"). Default to **single** when the items need different
justifications or you genuinely want per-row error tolerance.

#### Bulk call shape

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
        # optional per-item: target_id XOR pipeline_id, scan_id, occurrences, search
      - issue_id: <id2>
        pipeline_id: <pipeline_id>
      - issue_id: <id3>
        target_id: <target_id>
```

Per-item rules — same mutual exclusion as the single path:
- `target_id` and `pipeline_id` are **mutually exclusive** within each item.
- For Branch B (All Issues), **none** of the items may carry `target_id` or `pipeline_id` —
  the whole batch is Project-scoped.
- For Branch A (Pipeline Security), each item may carry its own narrower scope independently
  (one row can be Pipeline-scoped while another is Target-scoped).

#### Reading the bulk response

The response carries a top-level `status` banner the skill should surface verbatim:

| `status` | Meaning | Skill response |
|---|---|---|
| `ALL_SUCCEEDED` | Every item created. | Report each `{issueId, id}` and the Pending status. |
| `ALL_FAILED` | Entire batch rolled back. Every item shows the same error. | Surface `results[0].error`, ask the user to fix and re-submit the **full corrected list** — never retry only the failed rows. |
| `MIXED_UNEXPECTED` | Server returned both successes and failures (contract violation). | Treat as a server bug, dump the raw `results[]` to the user, do not auto-retry. |
| `EMPTY` | No items in response. | Treat as failure; verify the request actually included items. |

If you get `ALL_FAILED`, the typical causes (from the bulk service implementation in
`sto-core`) are: unknown `issue_id`, no matching scan within the user's org/project scope,
mutual-exclusion violation that slipped past preflight, or a duplicate exemption. The
`results[0].error` message will name the actual cause.

#### Fallback

If the bulk call returns `ALL_FAILED` because of one bad item, you can fall back to the
single path to identify the offender — but ask the user first; do not silently switch
strategies.

### Step 6 — Report

For each created exemption, return:

- `exemption_id`
- `status` — will be `Pending` until approved (use the `security_exemption` `approve` /
  `reject` execute actions to action it; that flow is out of scope for this skill).
- Deep link: `/ng/account/{accountId}/all/orgs/{org}/projects/{project}/sto/exemptions`

If any create call failed, surface the API error verbatim — these are usually mutual-exclusion
violations or missing required fields and the message is actionable.

## Examples

### Example 1 — Exempt one CVE from a pipeline execution at Pipeline scope

User: "Exempt CVE-2024-1234 from execution `ehsPKtczTRO5CUDAt-NR` for that pipeline only.
False positive — patched in our fork."

1. Confirm org/project (from session defaults).
2. `harness_list` `pipeline_security_issue` with `execution_id` + `search: "CVE-2024-1234"`.
3. Pick the single matching row; note its `pipelineId` and `issue_id`.
4. Scope: Pipeline → body.pipeline_id = `<pipelineId>`.
5. type = `False Positive`, reason = `"Patched in our fork — see PR #422"`.
6. Confirm, then `harness_create` with `body: { issue_id, type, reason, pipeline_id }`.

### Example 2 — Exempt three highs from All Issues at Project scope (bulk)

User: "From the All Issues page, suppress these three high-severity Log4j findings for 90
days. Acceptable risk — mitigations in place at the gateway."

1. `harness_list` `security_issue` with `severity_codes: "High"`, `search: "log4j"`.
2. Present rows, user picks three `issue_id`s.
3. Branch B → force Project scope (no target/pipeline fields).
4. Same `type` + `reason` + `duration_days` for all three → use **bulk**.
5. One `harness_create` with `resource_type=security_exemption_bulk`,
   `body: { type: "Acceptable Risk", reason: "Mitigated at API gateway WAF — ticket SEC-880",
   duration_days: 90, items: [{issue_id:"i1"},{issue_id:"i2"},{issue_id:"i3"}] }`.
6. Expect `status: ALL_SUCCEEDED`; report the three returned exemption IDs.

### Example 2b — Mixed-scope bulk from the Vuln tab

User: "From execution `ehsPKtczTRO5CUDAt-NR`, exempt these five Critical issues — first two
for the whole project, next two only on this pipeline, last one only on the `api-gateway`
target. False positive across the board."

1. List `pipeline_security_issue` with `execution_id` + `severity_codes: "Critical"`.
2. User picks five rows; note each row's `pipelineId` / `targetId`.
3. Single bulk call:
   ```
   harness_create resource_type=security_exemption_bulk body:
     type: "False Positive"
     reason: "False positive — see triage doc #441"
     items:
       - { issue_id: i1 }                              # project-scope
       - { issue_id: i2 }                              # project-scope
       - { issue_id: i3, pipeline_id: <pipelineId> }   # pipeline-scope
       - { issue_id: i4, pipeline_id: <pipelineId> }   # pipeline-scope
       - { issue_id: i5, target_id:   <targetId> }     # target-scope
   ```
4. All five share `type` + `reason`, so one bulk call is the right shape; per-item scope
   fields are honored independently.

### Example 2c — When NOT to use bulk

User: "Exempt these two CVEs — the Log4j one is a False Positive, the Spring4Shell one is
Acceptable Risk."

Different `type` per row → **single** path. Loop two `harness_create
resource_type=security_exemption` calls. Bulk would require splitting into two batches of
one, which is just the single path with extra steps.

### Example 3 — User asks for Target scope from All Issues

User: "From the issues page, exempt this XSS finding for the `web-frontend` target only."

The skill refuses to silently downgrade. It responds:

> The All Issues view does not carry per-execution context, so Target-scope exemptions can't
> be created from there. Two options:
> 1. Create this as a Project-scope exemption.
> 2. Open the Pipeline Security tab on a recent execution of the pipeline that scanned
>    `web-frontend`, give me its execution ID, and I'll scope it to the target.

### Example 4 — Mutual-exclusion error recovery

If the user supplies both a pipeline and a target, push back before calling the API:

> `pipeline_id` and `target_id` cannot both be set on a single exemption. Pick one:
> Pipeline scope (apply across every target this pipeline scans) or Target scope (apply
> across every pipeline that scans this target).

## Performance Notes

- `pipeline_security_issue` uses **diff pagination** — `page_existing` / `page_size_existing`
  and `page_new` / `page_size_new` are independent. For most chat workflows, request
  `page_size_existing: 100, page_size_new: 100` once and avoid further paging.
- `security_issue` uses standard `page` / `size`. Default page size is fine for selection
  prompts (≤20 rows).
- Always pass `include_exempted: false` on `pipeline_security_issue` or
  `exemption_statuses: "None"` on `security_issue` when the user is hunting for new things
  to exempt — it strips already-exempted noise.
- **Single** create calls are one POST per issue. The MCP server marks them
  `risk: high_write, retryPolicy: do_not_retry` — never auto-retry on failure; surface the
  error to the user.
- **Bulk** create is one POST for up to 100 items, producing **one** database transaction
  and **one** audit row regardless of batch size. For 100 items this is ~5 DB round-trips
  total vs ~400 with the loop approach (see `sto-core/docs/STO-8977-bulk-exemption-api.md`).
  Use bulk whenever ≥2 items share `type` + `reason`.
- Bulk is **all-or-none** — never retry only the failed rows from a `MIXED_UNEXPECTED` or
  `ALL_FAILED` response; resubmit the full corrected list.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Missing required fields for security_exemption: issue_id, type, reason` | Required field absent from `body`. | Re-ask the user; do not invent a `reason` or default `type`. |
| API error mentioning `targetId` cannot be combined with `pipelineId` / `projectId` | Both scope fields sent. | Enforce mutual exclusion in Step 3 — pick exactly one. |
| API error `account scope not supported` on **list** | Caller passed `resource_scope='account'` or `resource_scope='org'` when listing exemptions. | `security_exemption` is always listed at project scope. Those keywords are *approval* scopes, not list scopes. Remove the override and re-list. |
| Created exemption immediately shows `Approved` | RBAC granted auto-approval at that scope for the requester. | Working as designed; mention in the confirmation report. |
| Cannot resolve `requester_id` | The PAT-derived user lookup failed (network/auth). | Surface the error verbatim; do not fabricate an ID. Check that `HARNESS_API_KEY` is valid. |
| User wants to exempt at Org/Account scope on creation | Not supported by the create endpoint. | Create at the highest available scope (Project), then approve with `harness_execute resource_type=security_exemption action=approve body={scope:'ORG'|'ACCOUNT'}`. That flow is outside this skill. |
| Issue selected from Branch B but user later asks for Pipeline/Target scope | Branch B is Project-only. | Re-enter Branch A with the relevant `execution_id`. |
| Agent loops looking for `target_id` on `pipeline_security_issue` rows | The API does not put `target_id` on issue rows — only `targetVariantName` (display string). | Run `harness_list resource_type=pipeline_security_step filters={execution_id:<same id>}` once, build a `{targetName:targetVariant → targetId}` map, and look up each issue's `targetVariantName` in it. See the "Resolving `target_id`" recipe in Step 3. The list response also embeds a `_target_id_lookup_hint` field with the same instruction. |
| Bulk response shows `status: ALL_FAILED` | One or more items failed validation or DB insert; the entire batch was rolled back per the all-or-none contract. | Read `results[0].error` for the actual cause (unknown `issue_id`, no matching scan in scope, mutual-exclusion violation, duplicate exemption). Fix and resubmit the **full** corrected list — never retry only the failed rows. |
| Bulk response shows `status: MIXED_UNEXPECTED` | Server violated the all-or-none contract by returning both succeeded and failed items. | Treat as a server-side bug. Surface the raw `results[]` to the user, do not auto-retry, and consider falling back to the single path for the failed items only after the user acknowledges. |
| Bulk preflight error `items must contain at most 100 entries` | Caller exceeded the per-batch limit. | Split into multiple bulk calls of ≤100 items each. |
| Bulk preflight error mentioning `items[N].issue_id` or `items[N] sets both target_id and pipeline_id` | One item in the batch is malformed. | Fix only that item — the index in the error message tells you which one — then resubmit the full list. |
