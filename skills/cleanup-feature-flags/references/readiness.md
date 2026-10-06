# Code removal readiness

Rules for deciding which branch of the code to keep and whether it's safe to remove the flag from code. The source of truth is the flag's live definitions in FME — never the default or fallback written in the code. Field names are the definition fields from [concepts.md](../../../references/fme/concepts.md#definition-state-checklist).

**Critical environments** default to every environment marked `isProduction`. The user may add others. **The critical set must be non-empty and must be explicitly stated back to the user before any verdict is given.** If **List environments** returns no environment marked `isProduction` and the user hasn't named any critical environments, STOP: do not default to "ready" or treat an empty critical set as vacuously safe. Ask the user which environments are critical (production, or the closest equivalent) before proceeding.

## Forward treatment (per environment)

Work out what each critical environment actually serves today:

| Definition state | Forward treatment |
|---|---|
| Flag is archived, or the environment has no definition | `control`. SDKs return `control`, so the code's fallback branch is what runs. |
| `isKilled` is true | `defaultTreatment` |
| Not killed, `trafficAllocation` is 100 (or absent), no `rules`, no individual targets, and `defaultRule` is a single treatment at 100 | That treatment |
| Anything else (allocation across multiple treatments, rules, targets, traffic allocation below 100) | None: the environment is still mixed |

If the code reads the treatment config (the `WithConfig` calls in [sdk-patterns.md](../../../references/fme/sdk-patterns.md)), resolve and compare **both** the forward treatment name **and** that treatment's `configurations` value across every critical environment. Two critical environments that agree on the treatment name but carry different `configurations` are NOT the same forward state — hardcoding one environment's config value into the code would silently change behavior in the other. Treat a name match with a configuration mismatch as **blocked** (same severity as a treatment-name mismatch), not caution. Only hardcode the config value once the name and the configuration are identical across every critical environment.

## Verdict

| Verdict | When |
|---|---|
| **blocked** | Critical environments resolve to different forward treatments, or any critical environment is mixed. Critical environments agree on the treatment name but differ in that treatment's `configurations` value (when `WithConfig` is used). An ACTIVE experiment runs on the flag. Dynamic flag keys were found in code. The flag's rollout status marks it as permanent (rollout status names are workspace-defined, e.g. `Permanent`, `Kill switch`, `Do not remove`; if unsure, ask). No critical environment could be identified (empty critical set) — stop and ask rather than defaulting to ready. |
| **caution** | The forward treatment is `control` (archived flag or missing definition). Non-critical environments differ. A PAUSED experiment exists. No call sites were found in this repo. The flag is only referenced through a flag set. |
| **ready** | Every critical environment resolves to the same forward treatment, no caution applies, and all call sites are static. |

**blocked** stops the skill. **caution** needs the user's explicit acknowledgement for each reason before any code is edited.

Impressions don't change the verdict. Traffic is expected until the removal deploys. Record `impressions.lastImpressionAt` per critical environment for the PR. The staleness check happens at archive time in `manage-flag-lifecycle`, and so does the dependent-flag check: other flags' IN_SPLIT rules are evaluated by FME, not by this code.

## Multi-repo / multi-service coverage

A clean search in one repo only proves the flag is unused **in that repo**. It does not prove the flag is safe to archive, and it does not by itself justify a "ready" verdict for the flag as a whole:

- Always record, in the PR description and in the summary to the user, which repo(s)/service(s) were searched.
- If the user doesn't confirm this is the only repo/service that evaluates the flag, treat unknown coverage as **caution** and say so explicitly — do not imply the flag is fully removed from the codebase.
- `manage-flag-lifecycle`'s archive-time check still applies across whatever it can see; it does not substitute for confirming all repos that call this flag have had this cleanup PR merged and deployed.
