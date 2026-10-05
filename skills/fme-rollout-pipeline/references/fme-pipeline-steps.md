# FME pipeline step catalog

Harness FME rollout pipelines use native FME steps (`FmeFlag*`, `FmeFlagset*`, `FmeSegment*`, `FmeMetricCheck`). Prefer these over `Run` / `ShellScript` steps that call FME APIs, and over classic **`FlagConfiguration`** steps (legacy Feature Flags).

FME steps are allowed on **both** `FeatureFlag` and `Custom` stages. Step YAML `type:` strings must match the exact identifiers in this document — do not confuse them with UI-only registration identifiers (e.g. use `FmeFlagSetIndividualTargets` not `FmeFlagSetTargets`, `FmeFlagAddRemoveIndividualTargets` not `FmeFlagAddRemoveTargets`, `FmeSegmentAddRemoveTargets` not `FmeSegmentAddRemoveKeys`).

## Stage type

| Stage `type` | Use for |
|--------------|---------|
| `FeatureFlag` | Dedicated FME flag/segment steps (default for this skill) |
| `Approval` | Human gate before promoting to the next environment or percentage (`type: HarnessApproval`) |
| `Custom` | Mix `FmeFlag*` with `Wait` soak timers, tests, or other non-FME work |
| `Pipeline` | Chain an existing pipeline (e.g. CD deploy then FME rollout) |

## Flag lifecycle steps

| Step `type` | Purpose | Typical rollout use |
|-------------|---------|---------------------|
| `FmeFlagCreate` | Create flag metadata + treatments | Bootstrap a new flag (usually off/killed in all envs first) |
| `FmeFlagUpdate` | Update flag metadata (description, tags, owners, rollout status) | Bookkeeping between phases |
| `FmeFlagDelete` | Delete flag | Avoid in rollout skills — prefer kill + archive |
| `FmeFlagArchive` | Archive launched flag | Post-launch cleanup — use `/cleanup-feature-flags`, not rollout |

## Targeting and traffic steps

| Step `type` | Purpose | Typical rollout use |
|-------------|---------|---------------------|
| `FmeFlagRestore` | Turn flag **on** in an environment (undo kill) | First step when enabling traffic in an env |
| `FmeFlagKill` | Emergency **off** / rollback | Failure strategy or explicit rollback stage |
| `FmeFlagDefaultAllocation` | Set default-rule percentage split across treatments | Progressive rollout (5 → 25 → 50 → 100) and full launch |
| `FmeFlagLimitExposure` | Cap exposure to a treatment (0–100) | Alternative to allocation for simple % caps |
| `FmeFlagSetTreatments` | Define treatment list + defaults | When treatments are not yet defined in the env |
| `FmeFlagSetTargetingRules` | Replace targeting rules | Beta cohorts, segment rules, prerequisites |
| `FmeFlagAddRemoveIndividualTargets` | Add/remove individual targets | Target specific users before percentage rollout |
| `FmeFlagSetIndividualTargets` | Replace individual target list | Same as above when replacing the full list |
| `FmeFlagPatchDefinition` | JSON Patch operations on a definition | Promote config between envs, surgical edits |
| `FmeFlagReallocateTraffic` | Re-bucket traffic after definition change | After large targeting edits |
| `FmeFlagSetDynamicConfigurations` | Attach dynamic config per treatment | Config-driven rollouts |
| `FmeFlagSetImpressionTracking` | Enable/disable impression tracking | Observability before progressive rollout |
| `FmeFlagDefinitionInstructions` | Apply multiple definition mutations atomically in one step | Batch restore + allocation + rules; env promotion when several fields change together |
| `FmeMetricCheck` | Evaluate FME metrics over a lookback window; fail the **step** if JEXL `failureCriteria` is true | Soak/gate between % increases — **not** auto-rollback |

## Flagset steps (when rollout uses flagsets)

Flagsets group related flags for governance and coordinated rollout. Create flagsets before associating them with flags.

| Step `type` | Purpose | Typical rollout use |
|-------------|---------|---------------------|
| `FmeFlagsetCreate` | Create a flagset | Bootstrap a flagset before associating rollout flags |
| `FmeFlagsetDelete` | Delete a flagset | Cleanup after launch — not typical mid-rollout |
| `FmeFlagAddRemoveFlagsets` | Add/remove flagset associations on a flag definition | Attach a flag to a release flagset in an environment |

## Segment steps (when rollout uses segments)

| Step `type` | Purpose |
|-------------|---------|
| `FmeSegmentCreate` | Create segment |
| `FmeSegmentUpdate` | Update segment |
| `FmeSegmentDelete` | Delete segment |
| `FmeSegmentAddRemoveTargets` | Mutate segment membership |
| `FmeSegmentSetTargetingRules` | Segment rule definitions |

## Evaluation order (FME/Split model)

When sequencing steps, remember how targeting is evaluated:

1. **Killed** → serves `defaultTreatment` only (flag is off)
2. **Individual targets** → highest priority
3. **Rules** → top-to-bottom, first match wins
4. **Default rule / allocation** → fallthrough percentage or single treatment

Implications:

- `FmeFlagRestore` alone does not change percentages — pair with `FmeFlagDefaultAllocation` or `FmeFlagLimitExposure`.
- Individual targets bypass percentage rollout — remove or narrow them before a full launch.
- Downstream env gating: keep prod **killed** (`FmeFlagKill`) until upstream env is verified at 100%.

## Required spec fields (common)

| Step | Required `spec` fields |
|------|----------------------|
| `FmeFlagDefaultAllocation` | `flagName`, `environment`, `allocation` (array of `{treatment, amount}` summing to 100) |
| `FmeFlagLimitExposure` | `flagName`, `environment`, `limit` (0–100) |
| `FmeFlagRestore` / `FmeFlagKill` | `flagName`, `environment` |
| `FmeFlagPatchDefinition` | `flagName`, `environment`, `operations` |
| `FmeFlagCreate` | `name`, `trafficType` (+ treatments if defining at create time) |
| `FmeMetricCheck` | `flagName`, `environment`, `lookbackWindow` (e.g. `24h`, `7d`), `failureCriteria` (`type: Jexl`, `spec.condition` true = fail) |
| `FmeFlagSetTargetingRules` | `flagName`, `environment`, `targetingRules` (array of rule objects; pass `[]` to clear all existing rules) |
| `FmeFlagSetIndividualTargets` | `flagName`, `environment`, `targets` (array of `{treatment, keys}`; pass `[]` to clear) |
| `FmeFlagAddRemoveIndividualTargets` | `flagName`, `environment`, `add` / `remove` (arrays of `{treatment, keys}`) |
| `FmeFlagSetTreatments` | `flagName`, `treatments` (array of `{name, configurations?}`), `defaultTreatment` |
| `FmeFlagsetCreate` | `name`; optional `description` |
| `FmeFlagsetDelete` | `name` |
| `FmeFlagAddRemoveFlagsets` | `flagName`, `environment`, `addFlagsets` / `removeFlagsets` (arrays of flagset names; either may be empty) |
| `FmeSegmentCreate` | `name`, `environment`, `trafficType` |
| `FmeSegmentUpdate` | `name`, `environment` |
| `FmeSegmentDelete` | `name`, `environment` |
| `FmeSegmentAddRemoveTargets` | `name`, `environment`, `add` / `remove` (arrays of keys; either may be empty) |
| `FmeSegmentSetTargetingRules` | `name`, `environment`, `rules` |
| `FmeFlagDefinitionInstructions` | `flagName`, `environment`, `instructions` (ordered array; each entry has `type` + `value`; each `type` at most once per step) |
| `HarnessApproval` | `approvers` (array of `userGroups` or `users`, `minimumCount`, and `disallowPipelineExecutor: true`) |
| `Wait` | `duration` (e.g. `45m`, `1h`) |

**`FmeFlagDefinitionInstructions` instruction types** (each appears at most once per step):

| Instruction `type` | `value` shape | Notes |
|--------------------|---------------|-------|
| `SetDefaultTreatment` | treatment name (string) | Quote `"on"` / `"off"` when YAML treats them as booleans |
| `SetBaselineTreatment` | treatment name (string) | |
| `SetTrackImpression` | boolean | |
| `SetLimitExposure` | integer 0–100 | |
| `UpdateIndividualTargets` | array of `{treatment, actions: [{action: AddKeys\|RemoveKeys\|AddSegments\|RemoveSegments, value: [...]}]}` | |
| `UpdateDynamicConfiguration` | array of `{treatment, configuration}` | JSON string per treatment |
| `SetTargetingRules` | rule array (pass `[]` to clear) | Same shape as `FmeFlagSetTargetingRules` |
| `SetDefaultAllocations` | array of `{treatment, amount}` summing to 100 | Same shape as `FmeFlagDefaultAllocation` |
| `SetTreatments` | treatments array (min 2) | |
| `SetRolloutStatus` | rollout status string | Flag-level metadata |
| `SetFlagKilled` | boolean | `true` = kill, `false` = restore in that environment |

Prefer dedicated single-purpose steps (`FmeFlagRestore`, `FmeFlagDefaultAllocation`, etc.) for simple rollouts. Use `FmeFlagDefinitionInstructions` when several definition fields must change atomically (for example env promotion copying multiple fields at once).

`environment` is FME environment **name or ID** (case-sensitive), not the Harness CD environment identifier unless they were named the same on purpose.

Soak between percentages without metrics: `Wait` step (`type: Wait`, required `spec.duration`) in a **Custom** stage. `Wait` is not on the FeatureFlag stage step list.

## Failure strategies

Every `FeatureFlag` stage should include `failureStrategies`. For rollout:

- **Non-production FME stages:** `MarkAsFailure` on `AllErrors` (stop the pipeline).
- **Production FME stages:** consider `StageRollback` **and** a documented manual `FmeFlagKill` rollback path.
- Pair critical prod stages with an explicit **rollback stage** (kill flag) the team can run independently.

## What Harness pipelines do NOT provide

- No automatic **metric rollback** that auto-rolls back the flag on metric regression. `FmeMetricCheck` fails the step; pair it with an explicit `FmeFlagKill` if the user wants rollback.
- No MCP tool to start a progressive rollout — compose pipeline YAML from the steps above.
- Do not use other FME MCP resource types in this skill. Live kill/allocation/rules come from `fme_feature_flag_definition`.
