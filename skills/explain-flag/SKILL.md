---
name: explain-flag
description: >-
  Explain a single FME feature flag in plain language: purpose, default rule,
  and per-environment targeting state, flagging inconsistencies across
  environments inline. A quick-lookup/explain capability, not a search across
  many flags - disambiguates when the name/key given is ambiguous. Doesn't
  create, kill, or modify anything - see update-flag-targeting for targeting changes,
  manage-flag-lifecycle for metadata/archive, discover-feature-flags for multi-flag questions,
  manage-experiments for experiments. Trigger phrases: what does this flag do,
  explain this flag, how is X configured, is X on in prod, what's targeted for X.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Explain Flag

Answer "what does this flag do right now" for one named flag: its purpose, what serves by default, and how targeting differs (or doesn't) across environments - without touching anything.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List flags | `harness_list` · `fme_feature_flag` · `filters: { name }` · `compact: false` | `harness list feature_flag --search <substring> --json` |
| Get flag | `harness_get` · `fme_feature_flag` · `params: { feature_flag_name }` | `harness get feature_flag <name> --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |
| List definitions | `harness_list` · `fme_feature_flag_definition` · `params: { feature_flag_name }` · `compact: false` | `harness list feature_flag:definition <flag> --json` |

## Instructions

### Step 1: Resolve scope

Get `org_id` + `project_id` if not already known. Don't use the deprecated `workspace_id`: the Step 4 definition list is Harness-native only.

**List environments** up front, since Step 4 needs every environment. Keep the full list with each environment's `isProduction`: Step 4 diffs against it for missing definitions, and Step 6 labels production environments ("is X on" questions almost always mean "in production").

### Step 2: Find the flag, disambiguating if needed

**Stop condition:** if the user hasn't given any identifier at all (no name, key, or tag to search on), ask for one rather than listing every flag in the project as a substitute.

**List flags** for the substring. The name filter is a substring match, so it often returns several candidates (e.g. searching `checkout` also returns `checkout_v2` and `new_checkout`).

**If exactly one candidate's `name` is an exact, case-sensitive match to what the user typed, use it without asking** - the other hits are substring noise. It's genuinely ambiguous only when no candidate is exact and several are plausible.

**Stop condition:** for genuine ambiguity, list the candidates (name, description, `rolloutStatus.name`, `createdAt`, `openInHarness` link) and ask which one - don't guess by recency. Near-identical flags often share copy-pasted descriptions and rollout status, so `createdAt` and the link may be the only distinguishing details.

Substring search can't surface a near-duplicate that differs from what the user typed by a transposition or an extra character - neither name contains the other, so each is invisible to the other's search. If the name looks generic (short, numbered, one of a family) or the user seems unsure of the spelling, run a second search on a shorter fragment of it before treating a single hit as certain.

### Step 3: Get flag metadata

**Get flag** for the name.

Read `description`, `tags`, `trafficType` (an object - use `.name`, don't print the raw object), `owners` (array of `{type, name}` - join names with commas), `rolloutStatus.name` (e.g. `Pre-Production`, `Killed`), and `openInHarness` (direct link). Treat a missing `description` the same as an empty one: "no description set".

`rolloutStatus` is a manually set, project-level lifecycle label, not live state - a flag labeled `Killed` can still be live (`isKilled: false`) in some environments. When it disagrees with Step 4's `isKilled`, say so and trust `isKilled`.

### Step 4: Get targeting for every environment

**List definitions** for the flag.

For each environment's definition, read `isKilled` (per environment - a flag can be killed in one and live in another), `treatments`, `defaultTreatment` (served when the flag is killed or the traffic isn't allocated), `defaultRule` (buckets served when no targeting rule matches), `rules` (each with `buckets` + a `condition`), `trafficAllocation`, and `impressions.lastImpressionAt` (most recent impression; `null` = never received traffic). If `impressions` is absent, report last impression as unknown, not as unused.

Diff the returned environments against Step 1's full list explicitly. An environment with no definition is "not configured in `<env>`" - a distinct state, not a copy of another environment's config.

### Step 5: Synthesize and flag inconsistencies

Compare across environments before writing the summary, not after - inconsistency-spotting is the point of this skill, not an afterthought:

- Is `isKilled` the same across environments? A flag killed in one environment and live in another is the single most important inconsistency to surface - it usually means a rollback happened in one place and never propagated, or was never meant to.
- Same `defaultTreatment` and `defaultRule` split, or does one environment default differently (e.g. prod at 30/70, staging at 50/50)?
- Same targeting `rules` (same conditions, same treatment splits), or does one environment have rules the others lack?
- Same `trafficAllocation`, or is one environment running a partial rollout while another is at 100%?

Call out every difference explicitly - a flag behaving differently between staging and prod is very often exactly what the user needs to know, not noise to summarize away.

### Step 6: Deliver the explanation

```
## <flag_name>
<description, or "no description set">

**Traffic type:** <trafficType>   **Owners:** <owners, or "none set">
**Rollout status:** <rolloutStatus.name>   **Link:** <openInHarness URL>

### Per-environment state
| Environment | Prod? | Killed | Default treatment | Rules | Traffic allocation | Last impression |
|---|---|---|---|---|---|---|
| <env> | yes/no | yes/no | <defaultTreatment> (<defaultRule split>) | <n> rule(s) - <one-line summary each> | <trafficAllocation>% | <lastImpressionAt, "never", or "unknown"> |

### Notable
<any cross-environment inconsistency from Step 5, or "consistent across all environments" if none>
```

One line per rule (condition -> treatment split); offer **Get definition** (from Tools table) for full matcher detail instead of dumping raw JSON. The `Prod?` column comes from Step 1's `isProduction`, never from the environment name (names like `env-7` or `blue` say nothing).

If no environment has a definition, skip the table:

```
## <flag_name>
<description, or "no description set">

**Traffic type:** <trafficType>   **Owners:** <owners, or "none set">
**Rollout status:** <rolloutStatus.name>   **Link:** <openInHarness URL>

This flag exists but has no targeting configured in any environment yet.
```

If the question was scoped ("is X on in prod?"), answer it in that case too rather than leaving the reader to infer it: with no definition there, the flag isn't serving anything in that environment and SDKs fall back to the control treatment - it's unconfigured, not on or off.

## Examples

- "What does the `new-checkout` flag do?" - Steps 2-3 for purpose, Step 4-6 for full per-environment breakdown.
- "Is `dark-mode` on in production?" - Steps 2-4, but answer can be scoped to just the production environment's default treatment/rules rather than full table.
- "explain checkout" (ambiguous) - Step 2 surfaces `checkout-v2` and `checkout-v2-mobile`; ask which one.
- "Why is `beta-banner` behaving differently in staging vs prod?" - Jump to Step 4 comparison and lead answer with Step 5 inconsistency.

## Performance Notes

- **List environments** once (Step 1) and **List definitions** once (Step 4) - don't get per environment when the list returns all of them.
- Read-only: never call create/update/delete/execute. If user asks to change something, route per description.

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Flag name matches nothing | Confirm `org_id`/`project_id` first - a flag in a different project looks nonexistent | Don't assume it was deleted |
| `isKilled` disagrees with what the default treatment looks like | Trust `isKilled` - a flag can default to `off` without being killed | Report `isKilled` as "is this live here" and the default rule/treatment separately |
| The definition list is empty for every environment | The flag exists (Step 3 succeeded) but was never configured anywhere, typical for flags created ahead of rollout planning | Say so; don't treat it as an error or retry |

Generic errors: see [tool-map.md](../../references/fme/tool-map.md#common-errors).

## References

- [tool-map.md](../../references/fme/tool-map.md) — tool names, params, common errors
- [concepts.md](../../references/fme/concepts.md) — treatments, evaluation order, killed state
