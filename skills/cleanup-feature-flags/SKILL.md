---
name: cleanup-feature-flags
description: >-
  Remove a launched Harness FME feature flag from application code, keeping the treatment FME
  serves today, and open a pull request. Use when asked to remove a flag from code, hardcode the
  winning treatment after a rollout, or pay down flag debt for a specific flag. Do not use for
  finding stale flags (discover-feature-flags) or archiving and deleting flags in FME
  (manage-flag-lifecycle). Trigger phrases: remove flag from code, hardcode treatment, flag
  cleanup, flag debt, clean up feature flag.
metadata:
  author: Harness
  version: 1.1.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Cleanup Feature Flags

Remove one launched FME flag from application code and keep the branch FME serves today. The work ends with a PR. FME is read-only here; archive happens later in `manage-flag-lifecycle`.

Related: `discover-feature-flags` finds candidates (stale audit); `manage-flag-lifecycle` archives after the change deploys.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| Get flag | `harness_get` · `fme_feature_flag` · `params: { feature_flag_name }` | `harness get feature_flag <flag> --json` |
| List flag definitions | `harness_list` · `fme_feature_flag_definition` · `params: { feature_flag_name }` · `compact: false` | `harness list feature_flag:definition <flag> --json` |
| List experiments | `harness_list` · `fme_experiment` · `filters: { parent_type: "FEATURE_FLAG", parent_name, status: ["ACTIVE", "PAUSED"] }` · `compact: false` | `harness list experiment --parent-type FEATURE_FLAG --parent-name <flag> --status ACTIVE --json`, then again with `--status PAUSED` |

## Instructions

Load [readiness.md](references/readiness.md) before giving a verdict. Load [sdk-patterns.md](../../references/fme/sdk-patterns.md) before searching code.

### Phase 1: Establish scope

Follow [scope-establishment.md](../../references/scope-establishment.md). **List environments** and confirm the critical environments: by default those with `isProduction`, plus any the user adds.

### Phase 2: Pick the flag

If the user named a flag, **Get flag** to confirm it exists and note its `status` and `rolloutStatus`. If they want candidates instead, hand off to `discover-feature-flags` (stale audit) and come back with one flag.

### Phase 3: Forward treatment and verdict

1. **List flag definitions** for the flag. Resolve the forward treatment for each critical environment per [readiness.md](references/readiness.md#forward-treatment-per-environment).
2. Run the [experiment check](../../references/fme/write-safety.md#experiment-check) with **List experiments**. Here ACTIVE means **blocked**: code removal ends the experiment. PAUSED means **caution**.
3. Give the verdict per [readiness.md](references/readiness.md#verdict). Stop on **blocked**.

Never infer the forward treatment from the code's default or fallback value.

### Phase 4: Find call sites

In the application repo, identify the SDK and search for the flag key, batch calls, flag sets, config-file entries and tests per [sdk-patterns.md](../../references/fme/sdk-patterns.md). For each hit, record `file:line`, which branch is the forward one, and any side effects (tracking, metrics, logging).

- If you find **dynamic keys** (`"prefix-" + id`, `` `flag-${id}` ``), the verdict is **blocked**. Stop and ask the user how to proceed; automated removal can't be complete.
- If you find no hits, the flag may live in another repo or only in a flag set. That is **caution**.

### Phase 5: Present the plan and wait

Show:
- the forward treatment for each critical environment and why;
- each call site with the branch to keep and the code to delete;
- the verdict, with every caution reason;
- the last impression for each critical environment.

If the forward treatment is `control` or a killed `defaultTreatment`, say plainly that the newer code path will be deleted. Edit nothing until the user explicitly confirms this plan.

### Phase 6: Edit and verify

1. Work on a new branch in the application repo.
2. At each call site, keep the forward branch and inline the config value if `WithConfig` is used. Remove the dead branches, plus any flag-only constants, wrappers, imports, tests, fixtures, localhost or offline entries, and docs. Don't refactor unrelated code.
3. Search again for the key and for the batch and flag-set patterns. Any remaining hits must be explained: homonyms, other services, or fixtures the user wants to keep.
4. Run the repo's own build, lint and tests. Fix any failures before moving on.

### Phase 7: Open the PR

Confirm with the user before pushing or opening the PR. Use the repo's normal tooling and its own PR template and conventions (for example `.github/pull_request_template.md` or CONTRIBUTING). Don't impose a format. Whatever the template, the description must capture:

- the flag key and the treatment (or config value) that was kept;
- the FME evidence: org and project, critical environments checked, the forward treatment in each, the verdict and any caution the user acknowledged, the experiment check result, and the last impression in each critical environment;
- what was removed: branches, tests, config, imports;
- how it was verified: the clean search and the build and test run;
- the follow-up: archive the flag with `manage-flag-lifecycle` once this change is deployed everywhere the flag is evaluated, plus any other repos or services that may still reference it.

### Phase 8: Hand off

Report the PR link and the follow-up: "After this deploys, use `manage-flag-lifecycle` to archive `<flag>`." Don't archive or delete here.

## Examples

- "Remove `new-checkout-flow` from this repo": verdict, plan, confirm, edit, verify, PR, then the archive hand-off.
- "Hardcode the winning treatment for `dark-mode`": resolve the forward treatment from the live definitions, not from the code.
- "This flag is killed in prod, clean it up": the forward treatment is `defaultTreatment`; warn that the new path is deleted.
- "Which flags can we clean up?": hand off to `discover-feature-flags` (stale audit).
- "Archive the flag too": PR here first, then `manage-flag-lifecycle` after the deploy.

## Performance Notes

- One **List flag definitions** call covers every environment. Don't fetch definitions one environment at a time.
- Search the flag key first, then the batch and flag-set patterns. Wrappers often hide the literal key.
- Keep the diff to the flag. Unrelated refactors make the PR harder to review and revert.

## Troubleshooting

| Issue | Action |
|-------|--------|
| Critical environments disagree | **blocked**. Ask the user to align targeting (`update-flag-targeting`) or narrow the critical set. |
| An environment has no definition | Its forward treatment is `control`, so the fallback branch is live there. Treat it as **caution** and confirm. |
| Flag is already archived but still in code | Allowed. The forward treatment is `control`; confirm the fallback branch is what users get today. |
| ACTIVE experiment on the flag | **blocked**. Finish it first (`manage-experiments`). |
| Code uses `WithConfig` | Hardcode the treatment's config value from the definition, not just the name. |
| Dynamic flag keys | **blocked**. Stop and ask the user. |
| No call sites found | **caution**. Check other repos and flag sets before claiming the flag is unused. |
