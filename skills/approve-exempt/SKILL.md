---
name: approve-exempt
description: >-
  Approve pending Harness STO security exemptions (waivers) at their current scope or elevate
  them to Project, Org, or Account scope. Users say "approve" for both in-scope approval and
  higher-scope elevation — do not require the word "promote". Supports approving one exemption
  or a mixed list where each row has a different approval scope. Default workflow lists pending
  exemptions in chat (paginated preview) so the user picks by row number — no copying from the
  Harness UI. Use when a user wants to approve, sign off on, or clear pending exemptions, waive approvals,
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

**Keep the Harness UI out of the loop.** Do not ask the user to copy issue titles, CVEs, or
exemption IDs from the platform. Your default opening move is to **list pending exemptions in
chat**, show a numbered table, report `total`, and let them pick by row number (or narrow with
`search` if they volunteer a keyword). Pagination surfaces more rows on request — you never dump
the full queue at once.

## Instructions

### Step 1 — Establish project context

You need **org** and **project** unless they are already in session defaults or a pasted Harness
URL provides them.

Exemptions list URL shape (auto-extracts org/project):

`…/ng/account/{accountId}/all/orgs/{org}/projects/{project}/sto/exemptions`

### Step 2 — Surface pending exemptions (default opening move)

Unless the user already picked row numbers from a table **you showed in this same session**,
call `harness_list` before asking them to choose anything. Do not send them to the Harness UI.

#### Show a paginated preview, not the whole queue

Chat is a narrow surface — dumping 50 pending rows is unreadable. Default behavior:

1. Call `harness_list` with `status: Pending`, `size: 5`, `page: 0` (unless org/project are
   still unknown — resolve those first).
2. Read **`total`** from the response.
3. Render the table from `items[]` following `_display_hint`. Number rows **1–N** to match
   `_action_id_by_row` (1-based).
4. Tell the user how many pending exemptions exist and how to proceed:
   - If `total` ≤ 5: show every row; ask which to approve.
   - If `total` > 5: show the first page and say something like:
     > **{total}** pending exemption(s) in this project. Showing rows 1–5 below. Pick by
     > number (e.g. `1`, `1 and 3`, `2-4`), say **next** for the next page, or give a
     > **search** term to narrow (CVE, requester, issue title).
5. For **next page**, follow `_nextPageHint` exactly — keep `size`, `status`, and any `search`
   identical; only increment `page`.

```
harness_list
  resource_type: "security_exemption"
  org_id: <org>
  project_id: <project>
  filters:
    status: "Pending"
    size: 5
    page: 0
    search: "<optional — only when user narrows>"
```

Rules:

- `status` must be a **single** value (`Pending`), not comma-separated.
- **Default `size: 5`** inside `filters` on every call in a pagination session. Do not bump
  `size` mid-session unless the user explicitly asks for a larger page (e.g. "show 10").
- Keep `size` and all other filters **identical** when paginating; follow `_nextPageHint`
  verbatim.
- Never pass `resource_scope`, and never set `org_id` / `project_id` to words like `org` or
  `account` — those are approval-scope phrases, not list overrides.

The list response is optimized for chat:

- `items[]` — display fields only (`issue_title`, `severity`, `type`, `requested_by`, `target`,
  `scope`, `reason`, …). **No exemption IDs in the table.**
- `_action_id_by_row` — maps row number (1-based **on the current page**) → `exemption_id` for
  execute calls.
- `_display_hint` — column layout; follow it.
- Each row's `scope` is the exemption's **requested scope** — expect only `TARGET`, `PIPELINE`,
  or `PROJECT` for pending rows.

#### The selection prompt

After showing the table, always include:

1. **`total`** pending count (project-wide, not just this page).
2. **How to pick** — by row number from the table you just rendered.
3. **How to see more** — "next" / "next page" (pagination) or a search term to narrow.

Example:

> **12** pending exemptions. Showing 1–5 below. Which would you like to approve? Pick by number
> (e.g. `2`, `1 and 4`). Say **next** for rows 6–10, or search e.g. `log4j` to narrow.

Only add `search` to the list call when the user gives a keyword — do not require them to know
CVE or title text upfront.

#### When listing returns zero rows

Say there are no pending exemptions in this project (for the current filter). Do not ask them to
check the UI — offer to list without `search` if they had narrowed, or confirm org/project.

### Step 3 — Resolve which rows to approve

**Primary path:** the user picks **row numbers from your table**. Map through
`_action_id_by_row` on the **same page** they selected from. If they say "next" and pick from a
later page, re-list that page (or keep page context) before mapping numbers.

| How they pick | What you do |
|---|---|
| Row numbers (`1`, `1 and 3`, `2-4`) | Map through `_action_id_by_row` on the current page. |
| "Next" / "next page" | Increment `page` per `_nextPageHint`; show the new table; wait for picks. |
| Search term (`log4j`, requester name) | Re-list with `search`, reset to `page: 0`; show filtered preview. |
| Exemption ID (22-char Harness ID) | Accept if they paste one — but **never ask** for IDs; listing is the default. |
| "All on this page" | Every row on the **current page only** — confirm scope per row or one shared scope. |

When multiple rows match one search term, show the filtered table and ask which row(s) — do not
guess.

If the user gives a vague approve request with no row numbers yet ("approve pending exemptions",
"sign off waivers"), **go back to Step 2** — list first, then ask them to pick. Do not execute
until they choose from the surfaced table (or confirm "all on this page" with explicit scope).

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

### Example 1 — Default flow: list in chat, user picks by row (no UI copy)

User: *"Approve pending exemptions."*

1. Confirm org/project from session or URL.
2. `harness_list` with `status: Pending`, `size: 5`, `page: 0`.
3. Show numbered table + `total` (e.g. "8 pending, showing 1–5").
4. User: *"#2 and #4, as-is."* → map `_action_id_by_row[2]` and `[4]`, both `CURRENT`.
5. Confirm table, then execute.

Do **not** ask them to open Harness or paste issue names first.

### Example 2 — Pagination

User: *"Next page"* after seeing rows 1–5 of 12.

1. Follow `_nextPageHint` (`page: 1`, same `size: 5`).
2. Show rows 6–10 (numbered 1–5 on **this page** — clarify page-relative numbers or renumber
   as 6–10 in the display so picks are unambiguous).
3. User picks; map via `_action_id_by_row` for that page's response.

### Example 3 — Approve one row at current scope (after list)

User: *"Approve pending exemptions"* → sees table → *"#1, as-is."*

1. Row 1 pending `scope: TARGET` → `CURRENT`.
2. Confirm, then `harness_execute` with `resource_id` from `_action_id_by_row[1]`.

### Example 4 — Target → project elevation (user says "approve for project")

User picks row from table: *"#1 for the whole project."*

1. List already showed `scope: TARGET` on row 1.
2. "For project" → `body.scope: "PROJECT"`.
3. Confirm **Pending scope: TARGET → Approve at: PROJECT**, then execute.

### Example 5 — Org-wide approval (user says "approve", not "promote")

User: *"#2 for org"* (after selecting from surfaced table).

1. Map row 2 → `body.scope: "ORG"`.
2. Confirm showing **Approve at: ORG**, execute with `action: "approve"`.

### Example 6 — Target → org in one step (skip project)

User: *"Approve row 3 for org"* from the pending table.

1. Row 3 shows `scope: TARGET`.
2. `body.scope: "ORG"` — omit `project_id` on execute.

### Example 7 — Mixed scopes in one request

User: *"Approve #1 as-is, #2 for org, and #3 for account."* (from the same page table).

1. Plan three rows with `CURRENT`, `ORG`, `ACCOUNT`.
2. One confirmation table; three sequential executes.

### Example 8 — Optional search narrow (user volunteers a keyword)

User: *"Show pending log4j exemptions."*

1. List with `search: "log4j"`, `page: 0`, `size: 5`.
2. Show filtered table; user picks by row number.

### Example 9 — Reject is out of scope unless asked

User: *"Reject the XSS exemption."*

This skill is for **approval**. Use `harness_execute` with `action: "reject"` and the same
`resource_id` lookup pattern, or handle via a separate reject workflow if the user insists.

## Performance Notes

- **List-first workflow** — one small `harness_list` preview beats asking the user to hunt in the
  UI. Default `size: 5`; paginate with `_nextPageHint` when they say "next".
- Listing is POST-based and paginated; keep `size` constant across pages in a session.
- Approvals are `high_write` with `do_not_retry` — surface errors to the user instead of
  auto-retrying.
- Sequential executes are correct for mixed scopes; do not parallelize writes.
- `approver_id` is derived once per call from the PAT — no extra user lookup needed.
- Add `search` only when the user narrows — not as a substitute for showing the pending queue.

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
| Row number does not match after pagination | User referred to `#3` from an earlier page while you re-listed with different filters. | Re-show the current page table; use absolute row labels (6–10) on page 2+ or re-fetch the page they picked from. |
| User asked to approve but agent skipped the list | Violates list-first workflow. | Always `harness_list` Pending first; surface numbered table before execute. |
| Agent asked user to copy from Harness UI | Skill requires zero/minimal UI interaction. | List pending exemptions in chat; selection by row number only. |
| `_action_id_by_row` missing an index | Row had no `id` in the API payload. | Re-list or ask the user for the exemption ID. |
| Exemption not in Pending list | Already approved, rejected, or expired. | List with the appropriate `status` or explain the current state. |
| User expects pending `scope: ORG` | Requests are only created at project/pipeline/target. | Org/account effect comes from `body.scope` on approve, not from the create path. |
| Agent used `security_issue` | Wrong resource — issues are vulnerabilities, not exemptions. | Switch to `resource_type: "security_exemption"`. |
