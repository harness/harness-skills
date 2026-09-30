# FME rollout patterns

Pick a pattern based on user intent, then wire `FeatureFlag` / `Approval` / `Custom` stages. These are **composable mix-ins**, not a single required pipeline. Mix freely (e.g. progressive % in staging, then approval, then full launch in prod).

LaunchDarkly guarded-rollout inspiration maps as follows — do not invent LD MCP tools:

| LD idea | Harness composition |
|---------|---------------------|
| `start-guarded-rollout` stages + weights | Sequential `FmeFlagDefaultAllocation` stages |
| Monitoring window | `Wait`, `Approval`, Custom tests, or `FmeMetricCheck` |
| Auto rollback on regression | Explicit `FmeFlagKill` (metric check only fails the step) |
| Flag must be on | `FmeFlagRestore` before allocation |

## Pattern selection

| User intent | Pattern | Primary steps |
|-------------|---------|---------------|
| "Roll out 10% then promote" | Progressive percentage (single env) | `FmeFlagRestore` → repeated `FmeFlagDefaultAllocation` |
| "Promote dev → staging → prod" | Environment promotion | One `FeatureFlag` stage per env + optional `Approval` between |
| "Don't touch prod until staging is 100%" | Staging gate | Staging at 100% + verify + `Approval` + prod `FmeFlagRestore` + allocation |
| "Keep prod off until we approve" | Downstream gating | `FmeFlagKill` in prod early; `Approval` before prod stage removes kill |
| "Beta users first, then everyone" | Cohort then percentage | `FmeFlagAddRemoveIndividualTargets` or segment rules → then `FmeFlagDefaultAllocation` |
| "Copy staging targeting to prod" | Config promotion | `FmeFlagPatchDefinition` or replay allocation/rules per env |
| "Ship the winning treatment everywhere" | Full launch | `FmeFlagRestore` + `FmeFlagDefaultAllocation` 100% on treatment |
| "Emergency stop" | Kill switch | `FmeFlagKill` (standalone stage or failure handler) |

## 1. Progressive percentage (single environment)

**When:** Same environment, increase traffic to the **test treatment** in steps.

**Typical sequence per step:**

1. `FmeFlagRestore` (if killed)
2. `FmeFlagDefaultAllocation` with amounts summing to 100

**Example percentages:** 5 → 25 → 50 → 100 (adjust per risk).

**Between steps:** insert `Approval`, `Wait`, `FmeMetricCheck`, and/or `Custom` (deploy, soak, tests).

**Rollback:** `FmeFlagKill` or allocation back to 0% on test treatment.

**YAML shape:** one `FeatureFlag` stage per percentage **or** one stage with sequential steps if no gate between them.

## 2. Environment promotion

**When:** Flag should reach 100% (or agreed %) in env N before env N+1.

**Stage order (example):**

```
FeatureFlag (dev) → FeatureFlag (staging) → Approval → FeatureFlag (prod)
```

**Per env stage (minimum):**

1. `FmeFlagRestore`
2. `FmeFlagDefaultAllocation` — 100% on test treatment (or agreed partial %)

**Promotion order:** list `fme_environment` via MCP; sort non-production before production (`isProduction` / name). **Confirm order with the user** — do not assume naming conventions.

**Downstream gating:** prod stage is skipped or starts with `FmeFlagKill` until upstream verification passes.

## 3. Staging gate before production

**When:** Ticket requirement — staging must be at 100% before prod changes.

**Sequence:**

1. Staging `FeatureFlag` stage: restore + 100% on test treatment
2. `Custom` stage (optional): run tests / verify metrics
3. `Approval` stage: human sign-off
4. Production `FeatureFlag` stage: restore + allocation

**Verification without a metric step:** `harness_list` `fme_feature_flag_definition` with `filters: { feature_flag_name: "..." }` (or `harness_get` with `params: { feature_flag_name, environment_id }` for staging) **before** generating prod YAML; confirm `isKilled` is false, `defaultRule` bucket `size` values sum to 100 with the test treatment at 100%, empty `rules`, and empty treatment targeting lists. Do **not** use `trafficAllocation` as proof of full rollout — it is experiment participation (0–100), not which treatment wins. Document the check in the plan. Prefer live MCP definitions over pipeline snapshot output.

## 4. Approval gate

**When:** Human must approve before the next percentage or environment.

**Use:** `Approval` stage with `HarnessApproval` (`disallowPipelineExecutor: true` required).

Insert **between** FME stages, not inside `FmeFlag*` steps.

## 5. Downstream environment gating

**When:** Prod (or next env) must stay **off** until explicitly promoted.

**Options:**

- **Omit** prod from the pipeline until a later run (safest hold).
- Early prod stage with only `FmeFlagKill` (ensures off), then a later pipeline/run promotes.
- `when` conditions on prod stages (expression-based) if the pipeline supports runtime inputs.

**Never** record prod as "released" in the plan if the user asked to hold it — omit the stage or keep kill.

## 6. Config promotion between environments

**When:** Staging targeting is validated; prod should match.

**Approaches:**

1. **`FmeFlagPatchDefinition`** — patch operations copied from staging definition (preferred for surgical sync).
2. **Replay steps** — same `FmeFlagDefaultAllocation` / `FmeFlagSetTargetingRules` YAML with prod `environment`.
3. **MCP-assisted design** — read staging definition via `harness_get` with `params: { feature_flag_name, environment_id }` (or list all envs via `filters: { feature_flag_name }`), translate to pipeline step spec for prod (do not execute MCP mutations during design unless user confirms).

There is no single "copy environment" pipeline step — compose from patch/allocation/rules steps.

## 7. Full launch

**When:** Ready to serve one treatment to everyone in an environment.

1. `FmeFlagRestore`
2. `FmeFlagDefaultAllocation` — 100% on winning treatment, 0% on others
3. Clear individual targets / narrow rules if needed (`FmeFlagSetIndividualTargets`, `FmeFlagSetTargetingRules`)

After full launch in all critical envs, flag cleanup is `/cleanup-feature-flags`, not this skill.

## 8. Kill-switch rollback

**When:** Pipeline failure or operator abort.

- Add `FmeFlagKill` in a dedicated rollback stage (or a failure-gated stage).
- For prod failure strategies, pair `StageRollback` with an explicit kill stage the team can run independently. Do not use MCP execute/kill in this skill.

## Combining with CD / CI

Common pipeline shape:

```
CI (build/test) → CD (deploy) → FeatureFlag (rollout %) → Approval → FeatureFlag (next %)
```

Use `/create-pipeline` for CI/CD stages; use this skill for the FME stages and gates. Chain with `Pipeline` stage type when reusing an existing deploy pipeline.

## Plan checklist (present to user before YAML)

1. Flag name and test/control treatments
2. Environment promotion order
3. Percentage schedule per env (if progressive)
4. Approval gates (who approves)
5. Hold vs release per environment
6. Rollback path (`FmeFlagKill` targets)
7. Whether impression tracking should be enabled first
8. New pipeline vs update existing (`harness_create` vs `harness_update`)
