# Code removal readiness

Rules for deciding which branch of the code to keep and whether it's safe to remove the flag from code. The source of truth is the flag's live definitions in FME — never the default or fallback written in the code. Field names are the definition fields from [concepts.md](../../../references/fme/concepts.md#definition-state-checklist).

**Critical environments** default to every environment marked `isProduction`. The user may add others.

## Forward treatment (per environment)

Work out what each critical environment actually serves today:

| Definition state | Forward treatment |
|---|---|
| Flag is archived, or the environment has no definition | `control`. SDKs return `control`, so the code's fallback branch is what runs. |
| `isKilled` is true | `defaultTreatment` |
| Not killed, `trafficAllocation` is 100 (or absent), no `rules`, no individual targets, and `defaultRule` is a single treatment at 100 | That treatment |
| Anything else (split buckets, rules, targets, allocation below 100) | None: the environment is still mixed |

If the code reads the treatment config (the `WithConfig` calls in [sdk-patterns.md](../../../references/fme/sdk-patterns.md)), the forward value is that treatment's config from `treatments`. Hardcode the config value, not just the treatment name.

## Verdict

| Verdict | When |
|---|---|
| **blocked** | Critical environments resolve to different forward treatments, or any critical environment is mixed. An ACTIVE experiment runs on the flag. Dynamic flag keys were found in code. The flag's rollout status marks it as permanent (rollout status names are workspace-defined, e.g. `Permanent`, `Kill switch`, `Do not remove`; if unsure, ask). |
| **caution** | The forward treatment is `control` (archived flag or missing definition). Non-critical environments differ. A PAUSED experiment exists. No call sites were found in this repo. The flag is only referenced through a flag set. |
| **ready** | Every critical environment resolves to the same forward treatment, no caution applies, and all call sites are static. |

**blocked** stops the skill. **caution** needs the user's explicit acknowledgement for each reason before any code is edited.

Impressions don't change the verdict. Traffic is expected until the removal deploys. Record `impressions.lastImpressionAt` per critical environment for the PR. The staleness check happens at archive time in `manage-flag-lifecycle`, and so does the dependent-flag check: other flags' IN_SPLIT rules are evaluated by FME, not by this code.
