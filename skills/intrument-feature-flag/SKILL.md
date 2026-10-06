---
name: intrument-feature-flag
description: >-
  Gate application code behind an existing Harness FME feature flag. Detect the
  app's language, framework and any existing flag wrapper first; ask only what
  that can't resolve (target app, subject identity, gating point,
  treatment/config/fallback names, extension needs). Prefer an existing
  wrapper; otherwise propose a thin, customer-extensible facade or hook —
  never a new framework or second SDK client — approved before editing. Map
  named treatments to branches with a safe, non-boolean-coerced fallback,
  then add tests at the wrapper and call-site boundary. New flags delegate to
  create-feature-flag with the one environment actually selected; missing
  targeting delegates to update-flag-targeting under fresh approval. Not for
  flag creation alone, metrics (choose-metric, create-metric,
  instrument-metric), or first-time onboarding (feature-flag-onboarding).
  Trigger phrases: gate this code behind a flag, add flag check, wire up
  getTreatment, add SDK evaluation call.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI for flag reads, plus local application code access to make edits; guidance-only (no edits) if application access is unavailable
---

# Instrument Feature Flag

Skill identifier: `intrument-feature-flag`. Gate application code behind an existing FME flag: inspect the real app first, prefer or design a small customer-extensible wrapper, get it approved, implement the minimal edits, and test at the wrapper and call-site boundary. Related: `/create-feature-flag` (new flag), `/update-flag-targeting` (missing/insufficient targeting), `/feature-flag-onboarding` (first-time setup, which delegates here for code).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md). This skill only reads Harness flag state for the selected environment — flag/definition writes are delegated to `/create-feature-flag` and `/update-flag-targeting`.

| Operation | MCP | CLI |
|-----------|-----|-----|
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `compact: false` | `harness list feature_flag --json --limit 50` |
| Get flag | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name> --json` |
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List traffic types | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |

## Instructions

### Phase 1: Scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Carry confirmed account/org/project, transport and application target from the request/caller; ask only for missing context before API calls. Keep Harness scope separate from the application repo/runtime — never derive one from the other. See [mcp-setup.md](../../references/mcp-setup.md) for a supported CLI or MCP choice. **List environments** and require **one explicitly confirmed environment** before any flag/definition handoff. Resolve its ID and `isProduction`; if none is selected or the choice is ambiguous, ask and STOP—never inherit an all-environments default. This selection does not authorize a write.

### Phase 2: Detect the codebase before integration questions

Inspect the real application: language/framework/runtime and package manager (lockfiles/manifests), which app/package in a monorepo is plausible, the installed FME/OpenFeature/Classic-FF SDK and its version, and any existing flag wrapper/facade (grep flag-adjacent helper names, not only raw SDK calls). See [sdk-patterns.md](../../references/fme/sdk-patterns.md) for detection signals and [language-guidance.md](../../references/fme/language-guidance.md#phase-3-sdk--provider-identification) for the native-FME/OpenFeature/Classic-FF contract table — FME native treatments are **names**, not booleans, and batch/config/async evaluation calls have their own result shapes; never assume a signature shared across them. **Stop:** Classic FF-only repo with no matching FME flag; or an OpenFeature provider whose configured target (FME project/environment) is unverified — confirm it before treating `getBooleanValue`/etc. as evidence about this flag. Summarize detected facts in 3–5 bullets before asking integration questions. With no application access, ask for the missing non-secret context and provide guidance only: no invented file locations, edits or test success. An absent SDK is a setup case, not an unknown-signature exception: propose a runtime-appropriate package from verified official docs, and include installation/version changes in the approval plan.

### Phase 3: Ask only what inspection didn't resolve

Ask only for facts Phase 2 left open, and never re-ask a fact already confirmed by inspection or already supplied by a calling skill (e.g. `/feature-flag-onboarding`):
1. Target app/package, if a monorepo has more than one plausible target.
2. Evaluation subject key source and traffic type, if more than one identity candidate exists (user vs. account vs. anonymous).
3. Exact gating point — candidate `file:line` if more than one placement is plausible.
4. Named treatments/config this call site must branch on, and the safe fallback for `control`/errors.
5. Extension needs — will the app or its customers add treatments/branches later without touching this call site again?

### Phase 4: Resolve the flag definition

**Get flag** using the confirmed name and scope. A 404 is not proof a new flag is needed: recheck the identifier, scope and access per [tool-map.md](../../references/fme/tool-map.md#common-errors). Only after resolving genuine absence and the user's intent to create, load [create-feature-flag](../create-feature-flag/SKILL.md) with confirmed scope/transport, name/purpose, traffic type, treatment names/config/safe default, known description/ticket and **one selected environment**; carry user-confirmed facts rather than deriving new defaults. Its own approved plan controls creation. Disclose that approving resource creation does not approve later app edits; cancellation leaves a resource to report, not automatically delete. Require returned readback/IDs to match that contract, then resume here without creating again. An archived flag is not an active integration target: stop and clarify; any lifecycle change is a separate request.

For an existing flag, confirm the returned `trafficType` against **List traffic types** and the approved evaluation-subject source. A user/account/device identity mismatch is a STOP-and-clarify condition—do not infer semantic compatibility from the key's format or silently change it. **Get definition** in that environment and reconcile Phase 3 with the exact case-sensitive treatment names and config. Missing definitions or requested treatment changes go to [update-flag-targeting](../update-flag-targeting/SKILL.md) only after confirming that intent, under its separate approval. A treatment not currently allocated traffic does **not** require a targeting change merely to write/test its code branch. Never expand the rollout as a side effect of instrumentation.

### Phase 5: Design the integration

**Prefer an existing wrapper/facade** found in Phase 2 — extend it, don't create a second one. If none exists, default recommendation: a thin, idiomatic, **application-owned** facade (a module/service function for server code, a domain-specific custom hook for a component framework) that:
- Owns the SDK client's readiness and the one evaluation call for this flag.
- Exposes an idiomatic application-facing contract that preserves the needed treatment/config and asynchronous semantics. Preserve an existing typed provider/wrapper contract; a boolean helper requires an explicit approved treatment mapping, never string truthiness.
- Keeps customer-specific behavior extendable without scattering raw SDK calls. Agree the needed extension points; do not build a plugin framework or assume future treatment names. Adding a live treatment remains a separate approved definition change.

Never introduce a new universal/cross-flag framework, a second SDK client, or a guessed cross-language signature — verify against the installed SDK's types/version or an existing call. A direct SDK call without a wrapper is an exception, not a default: propose it only when the language/framework makes a wrapper impractical, explain the tradeoff, and get explicit approval for that specific choice. Inspect only non-secret configuration/credential references (see [language-guidance.md](../../references/fme/language-guidance.md#credentials-and-dependencies)) — never print, request, or hardcode a credential value. Show the proposed interface/location, call sites, treatment-to-branch map, readiness/error/configured-fallback behavior, dependency/configuration changes and focused test plan. Verify installed signatures and confirm missing SDK/credential prerequisites through [language guidance](../../references/fme/language-guidance.md#credentials-and-dependencies); no declared tool retrieves SDK keys. **STOP and wait for explicit approval of these edits and any dependency/version changes**. Reconfirm a changed plan; a resource-create approval is not approval to edit the app.

### Phase 6: Implement

Make the smallest edits: SDK init/wrapper only if missing, the wrapper's evaluation call, and call sites that use the wrapper. Reuse the SDK's existing client/factory lifecycle for this environment and identity — don't instantiate a client per evaluation — but this isn't a universal one-client-ever rule; follow the installed SDK's documented pattern. Map every named treatment explicitly; route `control` and any unmapped/unexpected value to the agreed safe fallback — never treat a non-empty treatment string as "enabled" by truthiness. A configured fallback treatment is a safety behavior, not proof the flag evaluated live — never report a fallback/offline/mocked result as a successful evaluation. Handle not-ready states, unexpected treatments and missing/malformed config using the approved contract; preserve framework hook ordering and cleanup. Do not add logging, analytics, caching or PII capture that wasn't requested and approved.

### Phase 7: Test

Add/update focused tests in the app's existing framework at two boundaries: (1) the wrapper — each approved treatment, identity isolation, readiness/error/configured-fallback and malformed-config behavior; (2) the call site's branches and safe fallback. Run the safe focused tests; do not install a new test framework without approval. If tests cannot run, say why and mark them **not run**, not passed. Mocks verify code behavior, not live evaluation. Live proof belongs to the calling onboarding workflow or a separately authorized runtime check; never automatically start onboarding, deploy, commit or open a PR.

### Phase 8: Summarize and handoff

Report application/revision, flag and selected environment IDs, approved subject-source/traffic-type contract (no sensitive values), edited locations, treatment/fallback mapping, dependency/config changes, delegated resource readbacks and tests (passed/failed/not run). Report live behavior separately as verified with named evidence or unverified. In guidance-only mode, list proposed steps and limitations instead of claiming edits. Return evidence to the caller without recursively invoking it or re-asking confirmed facts.

## Examples

- "Gate the new checkout flow behind the `checkout-v2` flag" — detect and clarify, read its live definition, then propose the wrapper integration; an existing flag does not justify skipping those steps.
- "Add a flag check for this feature, there's no flag yet" — Phase 4 delegates creation to `/create-feature-flag` with the one chosen environment, then resumes at Phase 5.
- "Wire up `v1`/`v2`/`v3` treatments with per-treatment config and a safe fallback" — confirm each treatment's config shape and the fallback explicitly; never assume `off`.
- "Build a customer-extensible wrapper so merchants can add their own treatment later" — Phase 5 proposes a facade with a treatment-to-handler map extension point; approve, implement, then add wrapper-level and call-site tests for each handler.
- "I don't have access to the app repo right now" — ask for necessary non-secret context and give guidance only; implementation, exact locations and tests remain unverified.
- "This repo only has Classic FF, not FME" — stop per Phase 2.

## Performance Notes

- Phase 2 detection substitutes for several Phase 3 questions; keep inspection proportional — stop once the gating point and SDK are identified, don't exhaustively grep the whole repo.
- Lists use `compact: false`; all reads carry explicit scope. Tools-table list rows are page requests, not full inventories: follow [pagination](../../references/fme/tool-map.md#pagination), using CLI `--offset`/`--limit` until completeness is established. Use **List flags** only for approved discovery when the flag identity is unknown; prefer confirmed IDs/direct gets.
- Delegated creates/updates carry their own confirm/approval and audit comment; this skill doesn't duplicate that protocol.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 404 on Get flag | Recheck scope, identifier and access first. Only confirmed absence plus an explicit creation request can hand off to `/create-feature-flag` |
| Definition missing or targeting insufficient for the agreed treatments | Delegate to `/update-flag-targeting` with a fresh approval |
| Treatment name in code doesn't match the live `treatments` array | Re-read the definition; fix the code reference, never rename the live treatment to match the code |
| Can't tell which app/package is the gating target | Ask — don't guess from the flag's name or traffic type |
| Repo uses Classic FF only, or an OpenFeature provider of unknown origin | Stop; confirm the actual flag system before writing any evaluation code |

## References

- [language-guidance.md](../../references/fme/language-guidance.md) — stack detection, wrapper reuse/extension points, SDK/provider contracts, credentials
- [sdk-patterns.md](../../references/fme/sdk-patterns.md) — evaluation/tracking call signatures and search patterns
- [concepts.md](../../references/fme/concepts.md) — treatments, `control`, killed state
- [mcp-setup.md](../../references/mcp-setup.md) — MCP/CLI transport selection
- [tool-map.md](../../references/fme/tool-map.md#common-errors) — tool names, params, generic Harness API errors
