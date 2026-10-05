---
name: cleanup-feature-flags
description: >-
  Audit Harness FME feature flags and safely remove a flag from code while
  preserving production treatment. Use when asked to clean up stale flags,
  remove a feature flag from the codebase, hardcode the winning treatment after
  rollout, or archive a launched flag. Do not use for creating or killing flags
  (use manage-feature-flags). Trigger phrases: flag cleanup, stale flags, remove
  feature flag, archive flag, hardcode treatment, flag debt, FME cleanup.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Cleanup Feature Flags

Audit Harness FME flags and remove a launched flag from application code while preserving the treatment FME currently serves. Creating, killing, or archiving flags outside this workflow is `/manage-feature-flags`.

## Instructions

Follow ordered phases. Load [references/readiness.md](references/readiness.md) before any verdict and [references/sdk-patterns.md](references/sdk-patterns.md) before searching code.

**Do not invent MCP tools.** Compose `harness_list`, `harness_get`, `harness_execute`, and `harness_delete` plus local search.

**MCP resource types** (native FME — use `org_id` + `project_id`):

| Tool | `resource_type` | When |
|------|-----------------|------|
| `harness_list` | `fme_environment` | Phase 1 — discover envs |
| `harness_list` | `fme_feature_flag` | Phase 3 — list flags |
| `harness_list` | `fme_feature_flag_definition` | Phase 3/5/9 — definitions across envs (`params.feature_flag_name`, `compact: false`) |
| `harness_list` | `fme_experiment` | Phase 5/9 — active experiments on the flag |
| `harness_get` | `fme_feature_flag` | Phase 5/9 — flag metadata (`resource_id`) |
| `harness_get` | `fme_feature_flag_definition` | Phase 5 — one env (`resource_id: "<flag_name>"`, `params.environment_id`) |
| `harness_execute` | `fme_feature_flag` | Phase 9 — `action: "archive"` (`resource_id`, `confirm: true`) |
| `harness_delete` | `fme_feature_flag` | Phase 9 — only after archive and only when no active definitions remain |

**Parameters:** pass `feature_flag_name` inside `params` (or `filters`) on list calls. Use `resource_id: "<flag_name>"` for get, archive, and delete. Pass `compact: false` on definition lists so treatments, targeting, and traffic allocation are returned.

**Confirmation:** pass `confirm: true` on archive and delete only after the user has approved the plan.

**Never guess the forward treatment** from SDK defaults in source. Query FME definitions.

**Stop before mutating.** Do not edit application code, archive, or delete until the user explicitly confirms the cleanup plan.

Prefer **archive** over delete. Do not `harness_delete` an ACTIVE flag. Delete only works when the flag has **no active definitions**. “Delete” / “I insist” means archive first, then wait for a second explicit confirm after archive and definition removal.

### Phase 1: Establish scope

Reuse [scope-establishment.md](../../references/scope-establishment.md). Ask for `org_id` and `project_id` if missing.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_environment"
  org_id: "<org>"
  project_id: "<project>"
```

Identify **critical environments** with the user (Production-like first). Restate scope before proceeding.

### Phase 2: Choose mode

- **Audit** — inventory / flag debt. Run Phase 3. Do **not** edit code.
- **Remove** — named flag cleanup. Start at Phase 4 unless Phase 3 was already done.

### Phase 3: Audit candidates (audit mode)

Narrow the candidate set first — by tag, rollout status, or name prefix — before per-flag definition calls.

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag"
  org_id: "<org>"
  project_id: "<project>"
```

Filter by status from the returned flags:

- **ACTIVE** flags — primary audit candidates
- **ARCHIVED** flags — still report when grep finds code refs (archived-but-still-in-code)

For each candidate:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag_definition"
  org_id: "<org>"
  project_id: "<project>"
  compact: false
  params:
    feature_flag_name: "<flag_name>"
```

Read `lastImpressionAt` per environment from each definition.

Rank with [readiness.md](references/readiness.md) and grep the application repo per [sdk-patterns.md](references/sdk-patterns.md).

Present: flag, status (`ACTIVE` / `ARCHIVED`), verdict (`safe` / `caution` / `blocked`), winning treatment per critical env, `lastImpressionAt` summary, code-ref count. Ask which flag to remove, if any.

### Phase 4: Explore code (remove mode)

Identify the SDK family (see [sdk-patterns.md](references/sdk-patterns.md)). Search the flag key and relevant eval patterns in the **application** repo.

For each hit: file:line, which branch runs, side effects. Dynamic keys → stop (incomplete automation). Flag-set membership (`getTreatmentsByFlagSet`) may hide the key from a plain string search → **caution**.

### Phase 5: Readiness and forward treatment

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_feature_flag"
  org_id: "<org>"
  project_id: "<project>"
  resource_id: "<flag_name>"
```

List definitions across **every** critical environment:

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_feature_flag_definition"
  org_id: "<org>"
  project_id: "<project>"
  compact: false
  params:
    feature_flag_name: "<flag_name>"
```

Check for active experiments — **blocked** if any (`parent_type` is required; `status` defaults to ACTIVE):

```
Call MCP tool: harness_list
Parameters:
  resource_type: "fme_experiment"
  org_id: "<org>"
  project_id: "<project>"
  filters:
    parent_type: "FEATURE_FLAG"
    parent_name: "<flag_name>"
    status: "ACTIVE"
```

Apply [readiness.md](references/readiness.md) including dependent-flag matchers and `lastImpressionAt`. If **blocked**, stop.

Forward treatment comes from FME only — all critical envs must agree per the rules in readiness.md.

### Phase 6: Present the plan and wait

Show: forward treatment and why, code refs, planned keep vs delete, verdict and warnings, `lastImpressionAt` per critical env, archive-after-merge (not delete). If the flag is killed, say explicitly that hardcoding the default treatment usually removes the new code path.

**Do not proceed until the user explicitly confirms.**

### Phase 7: Remove from application code

Only after confirmation:

- Keep the branch matching forward treatment; remove the other
- Remove flag-only imports, constants, wrappers, tests, docs, and control branches
- Do not refactor unrelated code

Match the app’s SDK dialect ([sdk-patterns.md](references/sdk-patterns.md)).

```java
// Before
if ("on".equals(splitClient.getTreatment(key, "new-checkout-flow"))) {
  return renderNewCheckout();
}
return renderOldCheckout();

// After
return renderNewCheckout();
```

```javascript
// Node.js — Before
const treatment = splitClient.getTreatment(key, "new-checkout-flow");
return treatment === "on" ? renderNewCheckout() : renderOldCheckout();

// After
return renderNewCheckout();
```

### Phase 8: Verify

1. Re-search for the flag key — no leftovers (see sdk-patterns for batch/flag-set APIs)
2. Run existing build/test/lint
3. Open a PR using [references/pr-template.md](references/pr-template.md)

Archive in FME only after merge/deploy (or archive-only if code is already gone).

### Phase 9: Archive in FME

**Re-check readiness** (Phases 5 checks) immediately before archive. If anything changed — new impressions, active experiment, targeting — stop and ask the user.

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "fme_feature_flag"
  action: "archive"
  org_id: "<org>"
  project_id: "<project>"
  resource_id: "<flag_name>"
  confirm: true
  body:
    comment: "Cleanup PR merged/deployed — archive after code removal"
    title: "<cleanup PR title or URL>"
```

Verify archive succeeded:

```
Call MCP tool: harness_get
Parameters:
  resource_type: "fme_feature_flag"
  org_id: "<org>"
  project_id: "<project>"
  resource_id: "<flag_name>"
```

Confirm the flag is archived (`status: ARCHIVED`). If archive is blocked by governance (409), show the error — do not delete to bypass it.

Delete only after archive, no active definitions remain, and a **second** explicit user confirm:

```
Call MCP tool: harness_delete
Parameters:
  resource_type: "fme_feature_flag"
  org_id: "<org>"
  project_id: "<project>"
  resource_id: "<flag_name>"
  confirm: true
```

## What NOT to do

- Guess forward treatment from code
- Kill a flag as “cleanup”
- `harness_delete` an ACTIVE flag or a flag with active definitions
- Edit code or archive before confirmation
- Create, kill, or restore flags (use `/manage-feature-flags`)

## Examples

- "Clean up stale FME flags" — Audit mode; rank by `lastImpressionAt` and stop.
- "Remove `new-checkout-flow` from this repo" — Remove mode; plan, wait, code, verify, archive after merge.
- "Create a dark-mode flag" — Use `/manage-feature-flags`.

## Performance Notes

- Narrow audits with tags or `rollout_status_id` before calling `fme_feature_flag_definition` per flag — each definition list is one call per flag.
- Always pass `compact: false` on definition lists; the default omits targeting details.
- Grep the application repo before labeling a flag **safe** — flag sets and batch APIs can hide the key from a single-string search.
- Re-check readiness immediately before archive; impressions or experiments may have changed since the plan was confirmed.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Environments disagree | Do not pick a treatment; ask user to align or narrow critical envs |
| Missing `lastImpressionAt` | **Caution** — treat as unknown traffic, not proof of zero usage |
| Active experiment on flag | **Blocked** — end or promote the experiment first |
| `fme_experiment` not supported | **Caution** — verify experiments in Harness UI before proceeding |
| Dependent flags in other rules/segments | **Blocked** or **caution** — scan definitions or ask user |
| Archive blocked (409) | Show error; do not delete around governance |
| User insists on delete | Archive while ACTIVE; delete only when no active definitions and on later confirm |
| Flag not found | Confirm org, project, exact flag name |
| No code refs | Other repos, flag sets, or dynamic keys may still evaluate — do not archive as “unused” without user OK |
| Archived flag still in code | Report in audit; user may want code cleanup without unarchiving |
| Skill not in MCP tool list | Load this skill via `@` in chat; MCP exposes `harness_*` tools only |

## References

- [readiness.md](references/readiness.md) — verdict rules and forward treatment
- [sdk-patterns.md](references/sdk-patterns.md) — code search
- [pr-template.md](references/pr-template.md) — PR body
- `/manage-feature-flags` — create, kill, restore
