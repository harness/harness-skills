---
name: feature-flag-onboarding
description: >-
  Orchestrate first-time Harness FME onboarding for one application. Confirm
  an already-enabled FME account/project, then pick one verified
  non-production environment; if none exists, hand off to an admin, not
  creating one. Detect the codebase's language and framework, then delegate
  code integration to intrument-feature-flag — never duplicating its wrapper
  design or creating the same flag twice. Verify two distinct named-treatment
  outcomes live through separately approved targeting changes when needed,
  not just default/fallback responses.
  Resumes from live state and a non-secret progress summary instead of a
  checkpoint file; never recreates a flag from uncertain absence or reuses a
  stale approval. Use when asked to onboard FME for an app, set up feature
  flags end-to-end, or prove a flag works live. Not for flag creation alone
  (create-feature-flag), code gating alone (intrument-feature-flag),
  targeting alone (update-flag-targeting), or metric/experiment setup.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI, plus local application code access and (for live proof) runtime/build access; guidance-only or partial if application/runtime access is unavailable
---

# Feature Flag Onboarding

Orchestrate a new application's first end-to-end FME setup: confirm scope, pick a safe environment, detect the codebase, delegate code integration, then prove two distinct treatments actually run live. This skill sequences and verifies; it does not re-implement flag creation, code wiring, or targeting changes — those live in `/create-feature-flag`, `/intrument-feature-flag`, and `/update-flag-targeting`.

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md). All writes are delegated to the linked skills — this skill only reads.

| Operation | MCP | CLI |
|-----------|-----|-----|
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `compact: false` | `harness list feature_flag --json --limit 50` |
| Get flag | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name> --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |

## Instructions

### Phase 1: Scope and account check

Follow [scope-establishment.md](../../references/scope-establishment.md), separating confirmed account/org/project from the application repository. Establish the supported CLI or MCP transport per [mcp-setup.md](../../references/mcp-setup.md) before API calls; CLI users need not configure MCP. This workflow starts with an existing FME-enabled account/project. Verify the needed read capability in that scope. A 401/403, missing tool or empty inventory does not by itself prove missing entitlement: diagnose the actual error without changing scope/transport to bypass it. Missing account/project/enablement prerequisites go to the authorized user/admin, not automatic provisioning.

### Phase 2: Resume check (no checkpoint file)

Use any non-secret progress summary to identify scope/app/flag, then re-read current state; a summary is context, not proof or approval. Ask about ambiguous identities before choosing a candidate. Prefer **Get flag/definition** for confirmed IDs; use paginated discovery only when needed. A 404 requires scope/identifier/access checks, not automatic creation. Do not infer application integration or live success from a flag merely existing.

Track transport, environment, SDK/configuration, flag/definition, app integration/tests, outcomes A/B and final state as **verified / incomplete / unknown**, with evidence. During Phase 4/6 inspect the actual app revision, SDK initialization/wrapper and tests as well as remote state. Resume the first incomplete phase without repeating completed mutations; revalidate proof if revision, environment, identity, treatments or targeting changed. Never reuse stale approval. Guidance-only/missing runtime access remains partial.

### Phase 3: Select one non-production environment

Reuse a complete **List environments** inventory and verify the explicitly selected environment's ID and `isProduction: false`; do not ask again when selection is already clear. Otherwise recommend an isolated/test environment and confirm it. Follow [pagination](../../references/fme/tool-map.md#pagination) before concluding none exist. With no non-production environment, stop for an admin handoff—never create one or silently use production.

### Phase 4: Detect the codebase, then clarify

Make this sequence visible: **detect → clarify → delegate the wrapper plan.** Do a light detection pass per [language-guidance.md](../../references/fme/language-guidance.md#phase-1-detect-before-asking) (language/framework/runtime, monorepo layout, existing FME/OpenFeature/Classic-FF usage) — enough to pick the target app and know whether `/intrument-feature-flag` will find an existing wrapper. If the installed flag system can't be identified (Classic FF only, or an unverified OpenFeature provider), stop and resolve that before delegating. Summarize what was detected, then ask only for unresolved choices: target app/service, purpose and candidate gating point, evaluation identity/traffic type, intended treatment outcomes/fallback and customer extension needs. Existing definitions constrain valid treatment names; for a new flag, propose names such as `on`/`off` only for explicit confirmation, never silently assume them. Do not design the wrapper, SDK recipe, or treatment mapping here — that belongs entirely to `/intrument-feature-flag` in Phase 6. Carry every confirmed fact forward so delegated skills never re-ask them.

### Phase 5: Agree the onboarding contract

Confirm reuse of the identified flag or the intention to create one, one environment, two distinct intended outcomes, an authorized isolated test subject and desired final state (including removal/retention of temporary targeting). These decisions describe the plan, not blanket write approval. Creation belongs to the instrumentation handoff in Phase 6; do not create the flag separately here. Never select an unrelated existing flag merely because its name looks plausible.

### Phase 6: Delegate code integration (architecture owned by the callee)

Load [intrument-feature-flag](../intrument-feature-flag/SKILL.md) with confirmed scope/transport, app/revision, detected stack/wrapper, existing flag or proposed creation intent, **one selected environment**, identity/traffic type, intended outcomes, fallback and extension needs. It validates the contract, owns the approved abstraction/code edits/tests and delegates any creation to [create-feature-flag](../create-feature-flag/SKILL.md), then returns here—no duplicate creation or recursive handoff. Carry confirmed facts; clarify only new gaps.

Require returned resource IDs/readback, approved treatment/identity mapping, edited revision, SDK/configuration readiness and test status. Missing SDK credentials require an authorized provisioning handoff, never a fabricated retrieval tool or admin-token substitution. If code tests fail or source/setup is incomplete, resolve or report partial and stop before live targeting changes. No runtime access means code-tested/configuration-verified at most, not completed onboarding.

### Phase 7: Prove treatment A live

Before a test-targeting mutation, require Phase 6's verified integration/mapping and passing focused app-test evidence; a guidance-only proposal or flag existence is insufficient. If the user ran the tests, explicitly attribute their reported results rather than claiming tool execution. Confirm the running app contains that revision, uses the selected environment's credential **reference**, and has completed the installed SDK's real readiness path. Ask the user to perform/authorize any necessary build, restart or runtime check; never deploy automatically. If prerequisites or evidence access are missing, stop at partial without changing targeting merely to attempt a test.

Read the current definition. If a change is needed, load [update-flag-targeting](../update-flag-targeting/SKILL.md) under fresh approval to serve A to the agreed isolated subject; preserve other audiences. Its experiment/governance checks and killed-state ordering apply—never restore stale targeting or use kill as a generic off toggle. Verify definition readback, then have the authorized user/runtime check trigger the real path. Record revision, flag/environment, a non-sensitive subject reference, observed treatment and application behavior. For each outcome, establish that this invocation came from a real flag decision rather than fallback: use the installed SDK's supported evaluation details/reason, correlated impression metadata, or an authorized integration check that distinguishes fallback. Readiness alone is insufficient. Do not invent a telemetry API, enable sensitive logging, change fallback semantics merely to pass, or count a mock/offline/default response as proof. If the available evidence cannot distinguish the result, mark it unverified and stop before B.

### Phase 8: Prove treatment B live

Repeat Phase 7's read/approve-change/readback/observe sequence for B using the **same flag, environment, app revision and evaluation identity**, so the results are comparable. Reuse already-valid evidence instead of repeating a mutation. If interrupted or verification fails, report the actual current state and pending cleanup; do not kill or restore a snapshot automatically. Follow [write-safety.md](../../references/fme/write-safety.md) for every pending mutation.

### Phase 9: Agree final state and summarize

Re-read current state and reconcile it with Phase 5's agreed final state, including temporary test targeting. Delegate only the necessary changes under a fresh approved diff, preserving concurrent unrelated changes; never restore an entire old definition snapshot. Verify final readback. If the user declines or cleanup cannot complete, report what remains and keep onboarding partial.

Summarize per [operation-summary.md](../../templates/operation-summary.md): configuration readback; code tests (passed/failed/not run); observed live A/B behavior (verified/unverified with evidence); final state/cleanup; and the next incomplete phase. Full completion requires valid app tests, both real outcomes and verified agreed final state. Supply this non-secret progress summary for resume, not a mandatory repository checkpoint file.

## Examples

- "Onboard FME for the checkout service" — fresh run through Phases 1-9.
- "Continue the onboarding we started yesterday" — Phase 2 resume from live state, no checkpoint file needed.
- "Set this up with the CLI only, no MCP" — same phases via the CLI tool-map rows; MCP is never mandatory.
- "There's no non-production environment yet" — stop at Phase 3, admin handoff.
- "The SDK credentials aren't configured" — resolve the credential reference during integration; stop before test-targeting mutations until the authorized user provisions it. Never substitute an admin API token.
- "I don't recognize this SDK/language" — stop and ask rather than guessing a cross-language pattern.

## Performance Notes

- Tools-table list rows fetch pages, not full inventories. Reuse confirmed IDs and follow [pagination](../../references/fme/tool-map.md#pagination), including CLI `--offset`/`--limit`, before absence claims. Remote flag existence cannot establish SDK, code-test or runtime completion.
- Delegated phases (6-9) carry their own confirm/approval and audit protocol; this skill sequences them, it doesn't duplicate them.
- Treat Phases 7 and 8 as two separate approvals even when back-to-back — a single confirmation doesn't cover both.

## Troubleshooting

| Problem | Solution |
|---------|----------|
| FME not enabled for this org/project | Stop; hand off to an admin — this skill doesn't provision accounts/projects |
| No non-production environment | Stop; hand off to an admin to create one — never default to production |
| Flag/app ambiguous on resume | Ask which flag/app, using live state as context, instead of guessing or recreating |
| Treatment A/B looks the same as before the change | Check runtime revision, environment/identity, SDK readiness/propagation, targeting precedence and fallback before proposing any authorized restart or new change |
| Only mock/fallback responses observed | Not proof — SDK may be unready or disconnected; verify readiness and credentials before re-testing |

## References

- [language-guidance.md](../../references/fme/language-guidance.md) — detect-before-ask, wrapper reuse, SDK/provider contracts (owned by `/intrument-feature-flag`, read here for orchestration awareness only)
- [write-safety.md](../../references/fme/write-safety.md) and [concepts.md](../../references/fme/concepts.md) — kill/restore ordering, experiment checks
- [mcp-setup.md](../../references/mcp-setup.md) — MCP/CLI transport selection
- [operation-summary.md](../../templates/operation-summary.md) — structured completion summary
- [tool-map.md](../../references/fme/tool-map.md#common-errors) — tool names, params, generic Harness API errors
