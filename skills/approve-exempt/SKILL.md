---
name: approve-exempt
description: >-
  Approve pending Harness STO security exemptions (waivers) at their current scope or elevate
  them to Project, Org, or Account scope. Users say "approve" for both in-scope approval and
  higher-scope elevation — do not require the word "promote". Supports approving one exemption
  or a mixed list where each row has a different approval scope. Lists pending exemptions via
  security_exemption, resolves rows by issue title or search, and executes per-item approvals.
  Use when a user wants to approve, sign off on, or clear pending exemptions, waive approvals,
  org-wide approval, or account-wide approval.
  Trigger phrases: approve exempt, approve exemption, approve waiver, sign off exemption,
  clear pending exemption, approve for org, approve for account, org-wide approval,
  account-wide approval, pending exemptions.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Approve Exemption

Approve one or more **Pending** STO security exemptions. This skill covers the approval
workflow after someone has requested an exemption (see `/exempt-vuln` for creation).

**Pending scope is only `PROJECT`, `PIPELINE`, or `TARGET`.** Exemptions are *requested* at
project, pipeline, or target scope only (All Issues → project; Vulnerabilities tab → project,
pipeline, or target). STO does not create pending requests at org or account scope — those
wider scopes exist only **after** elevation on approve (`body.scope` `ORG` or `ACCOUNT`). You
will not see `scope: ORG` or `scope: ACCOUNT` on rows from `status: Pending` in normal flows.
If a list row shows `ORG`/`ACCOUNT`, it is already approved/widened (re-approve or a different
workflow), not a fresh pending request this skill targets.

Harness exposes two different "scope" ideas — do not mix them up:

| Concept | What it controls | How you use it |
|---|---|---|
| **Listing scope** | Which project's exemption queue you read | Always list at **project** scope. Never pass `resource_scope='account'` or `'org'` to `harness_list`. |
| **Approval scope** | Where the exemption becomes effective after approval | Passed as `body.scope` on `harness_execute` — `CURRENT`, `PROJECT`, `ORG`, or `ACCOUNT`. |

Users almost always say **approve**, even when they want org- or account-wide coverage. Treat
"approve for org", "org-wide", and "at account level" as **approve with elevation** — the MCP
server routes those to the promote endpoint internally. You never need a separate
`action='promote'` call; always use `action='approve'` with the right `body.scope`.

## Instructions

### Step 1 — Establish project context

You need **org** and **project** unless they are already in session defaults or a pasted Harness
URL provides them.

Exemptions list URL shape (auto-extracts org/project):

`…/ng/account/{accountId}/all/orgs/{org}/projects/{project}/sto/exemptions`

### Step 2 — List pending exemptions

Always start from **Pending** status. Use a small page size so the table stays readable:

```
harness_list
  resource_type: "security_exemption"
  org_id: <org>
  project_id: <project>
  filters:
    status: "Pending"
    size: 5
    search: "<optional — CVE, package, issue title fragment>"
    page: 0
```

Rules:

- `status` must be a **single** value (`Pending`), not comma-separated.
- Pass `size: 5` inside `filters` on the first call (the global default of 20 is too large).
- Keep `size` and all other filters **identical** when paginating; follow `_nextPageHint` verbatim.
- Never pass `resource_scope`, and never set `org_id` / `project_id` to words like `org` or
  `account` — those are approval-scope phrases, not list overrides.

The list response is optimized for chat:

- `items[]` — display fields only (`issue_title`, `severity`, `type`, `requested_by`, `target`,
  `scope`, `reason`, …). **No exemption IDs in the table.**
- `_action_id_by_row` — maps row number (1-based) → `exemption_id` for execute calls.
- `_display_hint` — column layout; follow it.
- Each row's `scope` is the exemption's **requested scope** — expect only `TARGET`, `PIPELINE`,
  or `PROJECT` for pending rows. (`ORG` / `ACCOUNT` appear on already-widened exemptions, not
  on new requests.)

If the user already named specific exemptions (CVE, issue title, requester), add `search` on the
first list call. If nothing matches, say so and offer to broaden the search or show the full
pending queue.

### Step 3 — Resolve which rows to approve

The user may identify exemptions by:

| How they pick | What you do |
|---|---|
| Row numbers (`1`, `1 and 3`, `2-4`) | Map through `_action_id_by_row`. |
| Issue title / CVE / package name | Match against `issue_title` in `items[]`, or re-list with `search`. |
| Exemption ID (22-char Harness ID) | Use directly as `resource_id` — skip row lookup. |
| "All pending" / "all on this page" | Every row on the current page (warn if `total` is large; paginate only on request). |

When multiple pending rows match one search term, show the candidates and ask which row(s) to
approve — do not guess.

For a **mixed batch**, the user may assign a **different approval scope per exemption** in one
message, for example:

> Approve #1 as-is, #2 for org, #3 for account.

Build an internal plan: `{ exemption_id, approval_scope, issue_title }[]` — one entry per
exemption, scopes may differ.

### Step 4 — Map user intent to `body.scope`

`body.scope` is **required** on every approve call. It is the **approval scope** (where the
exemption takes effect), not the pending row's current scope label.

#### Elevation paths (pending → destination)

`body.scope` is always one of **`CURRENT`**, **`PROJECT`**, **`ORG`**, or **`ACCOUNT`**. It
names the **destination** after approval. The list row's `scope` is always the **starting**
request scope (`TARGET`, `PIPELINE`, or `PROJECT` only). Elevation uses `/promote` when the
destination is wider than “approve as-is”; the MCP routes that from `action='approve'`.

| Pending `scope` (start) | User intent | `body.scope` (destination) |
|---|---|---|
| `TARGET` | Approve as requested | `CURRENT` |
| `TARGET` | Widen to project | `PROJECT` |
| `TARGET` | Widen to org (skip project OK) | `ORG` |
| `TARGET` | Widen to account | `ACCOUNT` |
| `PIPELINE` | Approve as requested | `CURRENT` |
| `PIPELINE` | Widen to project | `PROJECT` |
| `PIPELINE` | Widen to org | `ORG` |
| `PIPELINE` | Widen to account | `ACCOUNT` |
| `PROJECT` | Approve as requested | `CURRENT` |
| `PROJECT` | Widen to org | `ORG` |
| `PROJECT` | Widen to account | `ACCOUNT` |

There is **no** pending row that starts at `ORG` or `ACCOUNT` — creation cannot request those
scopes (`canCreate` is false at org/account in sto-core). Do not plan paths like “org → org” or
“org → account” on the **Pending** queue. `ORG` / `ACCOUNT` in the table above are **only**
`body.scope` destinations when widening from target, pipeline, or project.

**Skip-level elevation:** A pending **target** (or pipeline) row can go to **org** or **account**
in one call — the user does not need a separate project approval step first unless they ask for
project scope explicitly.

**Project → project:** When the row is already `PROJECT` and the user wants no widening, use
`CURRENT`. Do **not** pass `body.scope: "PROJECT"` for that — `PROJECT` on execute means
“promote **to** project scope” (for target/pipeline pending rows). Plain “approve this
project exemption” → `CURRENT`.

**Not supported (do not offer):**

| Request | Why |
|---|---|
| Narrow scope (project → target, org → project, etc.) | Promotion only widens; downscoping is invalid. Pending requests cannot start at org/account. |
| Pending row shows `ORG` or `ACCOUNT` | Not a normal pending *request* — already widened or a re-approve case. | List `status: Pending` for standard approvals; expired org/account re-approve is a different UI/API path. |
| `body.scope` of `TARGET` or `PIPELINE` on execute | MCP preflight rejects these; pending scopes only. Use `CURRENT` to approve at target/pipeline as requested. |
| Approve at a scope above the user's RBAC | API returns 403; `CanApproveFor` on the exemption must include the destination scope. |
| Multi-hop in one call beyond one destination | Each execute picks a single destination scope; you cannot pass both `ORG` and `ACCOUNT`. |

**Org / account execute params:** When `body.scope` is `ORG`, omit `project_id` on the execute
call. When `body.scope` is `ACCOUNT`, omit both `org_id` and `project_id` (MCP preflight
clears them). For `CURRENT` and `PROJECT`, keep normal project context.

#### Natural language → `body.scope`

| User says (examples) | `body.scope` | Effect |
|---|---|---|
| "approve", "approve as-is", "at current scope", "this target/pipeline/project" | `CURRENT` | Approve at the exemption's existing requested scope (no elevation). |
| "approve for project", "project-wide", "elevate to project" | `PROJECT` | Widen a **Target** or **Pipeline** pending exemption to project scope. |
| "approve for org", "org-wide", "organization level", "at org" | `ORG` | Elevate and approve at organization scope. |
| "approve for account", "account-wide", "account level" | `ACCOUNT` | Elevate and approve at account scope. |

**Default:** If the user says plain "approve" with no elevation hint, use `CURRENT`.

**Per-row overrides:** In a mixed list, honor each row's stated scope. Row 2 can be `ORG` while
row 3 is `ACCOUNT` in the same session.

Optional fields (same for every row unless the user specifies otherwise):

| Field | Notes |
|---|---|
| `comment` | Optional approval note. Ask if they want one; do not invent text. |
| `approver_id` | Auto-derived from the PAT — never ask the user. |

Do **not** use `harness_execute` with `action='promote'`. The `approve` action accepts
`body.scope` and picks `/approve` vs `/promote` automatically (`CURRENT` → approve endpoint;
`ORG` / `ACCOUNT` / `PROJECT` → promote endpoint).

### Step 5 — Confirm before executing

Echo a compact confirmation table before any write:

```
About to approve N exemption(s):
  # | Issue                          | Pending scope | Approve at   | Comment
  1 | CVE-2024-1234 in log4j-core    | TARGET        | CURRENT      | —
  2 | SQL Injection in api-gateway   | PROJECT       | ORG          | SEC-440
  3 | Spring4Shell                   | PROJECT       | ACCOUNT      | —
Proceed? (yes/no)
```

Wait for explicit **yes** (or pass `confirm: true` on `harness_execute` only after the user
confirms in clients that cannot elicit interactively).

### Step 6 — Execute approvals (one call per exemption)

There is **no bulk approve API**. Mixed scopes require **sequential** `harness_execute` calls —
one per exemption, each with its own `body.scope`:

```
harness_execute
  resource_type: "security_exemption"
  action: "approve"
  resource_id: <exemption_id from _action_id_by_row or user>
  org_id: <org>          # omit org_id/project_id when body.scope is ACCOUNT
  project_id: <project>  # omit project_id when body.scope is ORG or ACCOUNT
  body:
    scope: <CURRENT | ORG | ACCOUNT | PROJECT>
    comment: "<optional>"
```

After each call, record success or failure. If call 2 of 3 fails, report which succeeded and
which failed — do not silently retry with a different scope.

### Step 7 — Report results

For each approved exemption, return:

- Issue title (from the plan)
- Previous pending `scope` and the `body.scope` used
- New status from the API response (expect `Approved` when successful)
- Deep link: `/ng/account/{accountId}/all/orgs/{org}/projects/{project}/sto/exemptions`

If the user's RBAC does not allow the requested elevation, surface the API error verbatim and
suggest a lower scope (for example `CURRENT` or `PROJECT`) or a different approver.

## Examples

### Example 1 — Approve one pending exemption at current scope

User: *"Approve the pending Log4j exemption."*

1. `harness_list` with `status: Pending`, `search: "log4j"`, `size: 5`.
2. One match → row 1, pending `scope: TARGET`, user did not ask for elevation → `CURRENT`.
3. Confirm, then `harness_execute` with `resource_id` from `_action_id_by_row[1]`,
   `body: { scope: "CURRENT" }`.

### Example 2 — Target → project elevation (user says "approve for project")

User: *"Approve the pending Log4j exemption for the whole project."*

1. List shows `scope: TARGET`.
2. "For project" / "project-wide" → `body.scope: "PROJECT"` (not `CURRENT`).
3. Confirm **Pending scope: TARGET → Approve at: PROJECT**, then execute.

### Example 3 — Org-wide approval (user says "approve", not "promote")

User: *"Approve the Spring4Shell waiver for org."*

1. List pending with `search: "Spring4Shell"`.
2. Map "for org" → `body.scope: "ORG"`.
3. Confirm showing **Approve at: ORG**, execute with `action: "approve"` (not `promote`).

### Example 4 — Target → org in one step (skip project)

User: *"Approve the pending api-gateway exemption for org."*

1. List shows `scope: TARGET`.
2. "For org" → `body.scope: "ORG"` (not `CURRENT`, not a two-step project then org).
3. Execute with `project_id` omitted when scope is `ORG`.

### Example 5 — Mixed scopes in one request

User: *"Approve #1 as-is, #2 for org, and #3 for account."*

1. List pending (`size: 5`); user refers to row numbers from the table.
2. Plan:
   - Row 1 → `CURRENT`
   - Row 2 → `ORG`
   - Row 3 → `ACCOUNT`
3. One confirmation table with three rows and different **Approve at** columns.
4. Three sequential `harness_execute` calls, each with the matching `body.scope`.

### Example 6 — User provides exemption IDs and scopes explicitly

User: *"Approve exemption `abc…xyz` at current scope and `def…uvw` for account."*

Skip search when IDs are valid. Two executes with `CURRENT` and `ACCOUNT` respectively.

### Example 7 — Reject is out of scope unless asked

User: *"Reject the XSS exemption."*

This skill is for **approval**. Use `harness_execute` with `action: "reject"` and the same
`resource_id` lookup pattern, or handle via a separate reject workflow if the user insists.

## Performance Notes

- Listing is POST-based and paginated; always pass explicit `size: 5` for the first page.
- Approvals are `high_write` with `do_not_retry` — surface errors to the user instead of
  auto-retrying.
- Sequential executes are correct for mixed scopes; do not parallelize writes.
- `approver_id` is derived once per call from the PAT — no extra user lookup needed.
- Filter with `search` early when the user names a CVE or component to avoid paging the full
  pending queue.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `security_exemption approve: body.scope is required` | `body.scope` omitted on execute. | Always pass `scope`; default plain "approve" to `CURRENT`. |
| List error: `account scope not supported` | `resource_scope='account'` or `'org'` on **list**. | Remove scope override; list at project. Put `ORG`/`ACCOUNT` only on **execute** `body.scope`. |
| `invalid scope 'PIPELINE'` or `'TARGET'` on approve | `body.scope` must be `CURRENT`, `PROJECT`, `ORG`, or `ACCOUNT`. | Approve at target/pipeline as-is → `CURRENT`. Widen to project → `PROJECT`. |
| User wants project → project | Already project-scoped; no promotion. | `CURRENT`, not `PROJECT`. |
| User wants target → org (or pipeline → account, etc.) | Valid skip-level elevation. | Single execute with `ORG` or `ACCOUNT`; do not require an intermediate `PROJECT` step unless the user asked for project first. |
| 403 on target → account | Missing account-level `sto_exemption_approve`. | Try `CURRENT` or `PROJECT`, or a user with account approve rights. |
| Downscope request (“approve only for this target” on a project pending row) | Cannot narrow on approve. | Explain; they need a new target-scoped exemption request via `/exempt-vuln`. |
| User says "promote to org" | Same as org-wide approve. | `action: "approve"`, `body.scope: "ORG"`. |
| API 403 / permission denied | PAT user lacks `sto_exemption_approve` at that elevation scope. | Try `CURRENT` or ask someone with org/account approve permissions. |
| Row number does not match after pagination | User referred to `#3` from an earlier page while you re-listed with different filters. | Re-show the current page table or re-fetch the same `page`/`search`/`size` before mapping rows. |
| `_action_id_by_row` missing an index | Row had no `id` in the API payload. | Re-list or ask the user for the exemption ID. |
| Exemption not in Pending list | Already approved, rejected, or expired. | List with the appropriate `status` or explain the current state. |
| User expects pending `scope: ORG` | Requests are only created at project/pipeline/target. | Org/account effect comes from `body.scope` on approve, not from the create path. |
| Agent used `security_issue` | Wrong resource — issues are vulnerabilities, not exemptions. | Switch to `resource_type: "security_exemption"`. |
