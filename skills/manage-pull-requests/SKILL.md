---
name: manage-pull-requests
description: >-
  Manage Harness Code pull requests via MCP. List, create, update, and merge PRs; add reviewers and
  submit review decisions (approve / request changes); post, update, and delete comments; read the
  discussion timeline; and check CI status. Use when asked to open a PR, merge a PR, approve a PR,
  leave a code review comment, request changes, assign reviewers, or inspect PR checks and activity.
  Trigger phrases: pull request, PR review, merge PR, approve PR, request changes, add reviewer,
  PR comments, PR checks, PR activity, code review.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP server (harness-mcp-v2)
---

# Manage Pull Requests

Manage Harness Code pull requests, reviewers, comments, checks, and activity via MCP.

## MCP Tools Used

| Tool | Resource Type | Purpose |
|------|---------------|---------|
| `harness_list` | `pull_request` | List PRs in a repo, filter by state |
| `harness_get` | `pull_request` | Get PR details by number |
| `harness_create` | `pull_request` | Open a new PR |
| `harness_update` | `pull_request` | Update PR title / description / state |
| `harness_execute` (action: `merge`) | `pull_request` | Merge a PR (merge/squash/rebase/fast-forward) |
| `harness_list` | `pr_reviewer` | List reviewers on a PR |
| `harness_create` | `pr_reviewer` | Add a reviewer to a PR |
| `harness_execute` (action: `submit_review`) | `pr_reviewer` | Submit an `approved` or `changereq` review |
| `harness_create` | `pr_comment` | Post a top-level or inline code comment |
| `harness_update` | `pr_comment` | Edit a comment |
| `harness_delete` | `pr_comment` | Delete a comment |
| `harness_list` | `pr_activity` | Read the discussion timeline — **the only way to READ comments** |
| `harness_list` | `pr_check` | List CI status checks on a PR |
| `harness_schema` | any of the above | Exact JSON Schema for `create` / `update` body fields |

All pull-request resources are **repo-scoped**. Every call needs `repo_id` and `pr_number` (except `harness_list` for `pull_request`, which only needs `repo_id`). `org_id` / `project_id` are optional (the server infers them from the repo).

**URL shortcut:** the MCP server auto-extracts `repo_id` and `pr_number` if you pass a Harness PR URL via the `url` parameter — e.g. `harness_get(resource_type="pull_request", url="https://app.harness.io/ng/account/.../pulls/42")`.

## Instructions

### Step 1: List or find the PR

```
Call MCP tool: harness_list
Parameters:
  resource_type: "pull_request"
  repo_id: "<repository_identifier>"
  state: "open"        # optional: open | closed | merged
  query: "<keyword>"   # optional: full-text search
```

Or fetch a specific PR:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "pull_request"
  repo_id: "<repository_identifier>"
  pr_number: <number>
```

### Step 2: Open a PR

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pull_request"
  repo_id: "<repository_identifier>"
  body:
    title: "Fix race condition in scheduler"
    source_branch: "fix/scheduler-race"
    target_branch: "main"
    description: "Resolves HAR-1234. Adds mutex around queue access."
```

`title`, `source_branch`, `target_branch` are required. `description` supports markdown.

### Step 3: Update PR metadata

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pull_request"
  repo_id: "<repo>"
  pr_number: <number>
  body:
    title: "Updated title"
    description: "Updated description"
    state: "closed"     # optional: open | closed
```

All body fields are optional — only include what you want to change.

### Step 4: Add reviewers

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pr_reviewer"
  repo_id: "<repo>"
  pr_number: <number>
  body:
    reviewer_id: <numeric_user_id>
```

List current reviewers with `harness_list(resource_type="pr_reviewer", repo_id, pr_number)`.

### Step 5: Submit a review decision

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "pr_reviewer"
  action: "submit_review"
  repo_id: "<repo>"
  pr_number: <number>
  body:
    decision: "approved"          # approved | changereq
    commit_sha: "<sha>"           # optional — the commit you reviewed
```

### Step 6: Post a comment

**Top-level comment:**

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pr_comment"
  repo_id: "<repo>"
  pr_number: <number>
  body:
    text: "LGTM with one nit — see inline."
```

**Inline code comment:**

```
Call MCP tool: harness_create
Parameters:
  resource_type: "pr_comment"
  repo_id: "<repo>"
  pr_number: <number>
  body:
    text: "This loop can leak if the context is cancelled."
    path: "scheduler/queue.go"
    line_new: 142
    source_commit_sha: "<source_sha>"
    target_commit_sha: "<target_sha>"
```

Use `line_old` for comments on removed lines.

### Step 7: Read comments — use `pr_activity`, not `pr_comment`

The Harness Code API does **not** expose `GET` on `/comments`. To read the discussion, list PR activity filtered by kind:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "pr_activity"
  repo_id: "<repo>"
  pr_number: <number>
  kind: "comment"        # just comments (general + code)
  # or type: "code-comment" for inline code review comments only
```

Other useful `type` filters: `review-submit`, `reviewer-add`, `state-change`, `merge`, `title-change`.

### Step 8: Edit or delete a comment

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pr_comment"
  repo_id: "<repo>"
  pr_number: <number>
  comment_id: <numeric_comment_id>
  body:
    text: "Updated comment body"
```

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "pr_comment"
  repo_id: "<repo>"
  pr_number: <number>
  comment_id: <numeric_comment_id>
```

### Step 9: Inspect CI checks

```
Call MCP tool: harness_list
Parameters:
  resource_type: "pr_check"
  repo_id: "<repo>"
  pr_number: <number>
```

Returns the status of each status check (pipeline, test run, external check) associated with the PR head commit. Use this before merging to confirm required checks are green.

### Step 10: Merge

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "pull_request"
  action: "merge"
  repo_id: "<repo>"
  pr_number: <number>
  body:
    method: "squash"               # merge | squash | rebase | fast-forward
    delete_source_branch: true
    dry_run: false
    source_sha: "<expected_sha>"   # optional optimistic lock
```

Set `dry_run: true` first to preview the merge without executing — useful before destructive merges.

## Examples

### Open a PR and request a review

```
/manage-pull-requests
Open a PR from feat/new-auth into main titled "Add OAuth device flow" on repo platformUI,
and add user 12345 as a reviewer.
```

### Read all unresolved comments on a PR

```
/manage-pull-requests
Show me every inline code comment on PR 182 in repo harness-core so I can address them.
```

### Approve and merge

```
/manage-pull-requests
Approve PR 47 in repo mcp-server with a "LGTM" comment, then squash-merge it and delete the branch.
```

### Check CI before merging

```
/manage-pull-requests
List the checks on PR 99 in repo harness-cli. If they're all green, merge it with a squash.
```

### Close a stale PR

```
/manage-pull-requests
Close PR 22 in repo harness-skills with a comment explaining we're going in a different direction.
```

## Performance Notes

- **Always pass `repo_id` + `pr_number` together** except for `harness_list(pull_request)` which only needs `repo_id`. Missing `pr_number` on per-PR calls returns a helpful 400 from the server.
- **Read comments via `pr_activity`, never `pr_comment`.** The comments endpoint is POST-only. Use `kind=comment` for all discussion, `type=code-comment` for inline only.
- **Use `dry_run: true` on merge** before destructive squash/rebase merges — especially on main branches with required checks.
- **Prefer the URL shortcut** when the user pastes a PR link. `url="<PR URL>"` auto-extracts `org_id`, `project_id`, `repo_id`, and `pr_number` — fewer args to get wrong.
- **`pr_reviewer.submit_review`** records a review independently of the reviewer list. You don't need to call `harness_create(pr_reviewer)` first to submit a review — any user with access can review.
- **Cross-scope search**: `harness_search(query="<text>", resource_types=["pull_request"])` finds PRs across repos when you don't know which repo contains it.

## Troubleshooting

### "repo_id is required"

All PR operations are repo-scoped. Pass the repo identifier (not the repo name) — list repos first with `harness_list(resource_type="repository")` if you're unsure.

### Comments don't show up when I list them

`pr_comment` has no `list`/`get` operations. Use `harness_list(resource_type="pr_activity", kind="comment")` to read the discussion timeline.

### "GET /comments not found" / 404 on reading a comment

Same cause as above — the Harness Code API is POST-only for `/comments`. Read via `pr_activity`.

### Review decision rejected

Check the `decision` value — it must be exactly `"approved"` or `"changereq"`. The API does not accept `"approve"` (no `d`) or `"request_changes"`.

### Merge fails with "source SHA mismatch"

You passed `source_sha` and it no longer matches the branch head (someone pushed after you computed it). Drop `source_sha` or re-fetch the PR to get the current `source_sha`.

### Inline comment has no diff context

Inline code comments need both `source_commit_sha` and `target_commit_sha` in the body — without them the comment appears as a top-level comment. Get the SHAs from `harness_get(pull_request)` → `source_sha` / `target_sha`.

### Required checks aren't passing but merge succeeded anyway

`harness_execute(action=merge)` bypasses branch protection if the caller has admin rights. Use `harness_list(resource_type="pr_check")` first and fail fast in automation if any check is not `success`.
