# FME Language & Integration Guidance

Shared workflow for detecting an application's stack and deciding how feature-flag evaluation code should be structured, before writing any SDK call or asking the user something detection could answer instead. Used by [`/instrument-feature-flag`](../../skills/instrument-feature-flag/SKILL.md) and [`/feature-flag-onboarding`](../../skills/feature-flag-onboarding/SKILL.md). SDK detection signals and illustrative call shapes live in [sdk-patterns.md](sdk-patterns.md); FME semantics live in [concepts.md](concepts.md).

## Phase 1: Detect before asking

Read the application repository first. Do not ask the user anything detection can answer:

- **Language/runtime**: manifest files (`package.json`, `requirements.txt`/`pyproject.toml`, `go.mod`, `pom.xml`/`build.gradle`, `*.csproj`, `Gemfile`, `composer.json`) and lockfiles for the actual installed version, not just a declared range.
- **Existing FME/OpenFeature/Classic FF usage**: grep signals in [sdk-patterns.md](sdk-patterns.md#sdk-detection) — an existing dependency or call site is ground truth over any assumption.
- **Client vs. server context**: entry point (browser bundle, CLI, backend service, serverless function) and framework (React, Express, Django, Spring, etc.).
- **Monorepo signals**: workspace roots (`pnpm-workspace.yaml`, `turbo.json`, `nx.json`, multiple `package.json`/`go.mod` under one repo). Identify which app/package is in scope from the user's request or files already under discussion — don't scan the whole monorepo speculatively.
- **Existing wrapper/facade**: see [Reuse before building](#reuse-before-building-a-wrapper).

State what was detected (language, SDK/provider, version, client-or-server, wrapper present/absent) in one short summary before proceeding, so the user can correct a wrong inference cheaply.

## Phase 2: Ask only what detection left ambiguous

Typical open questions, asked together once detection is done — never ask about something the repo already shows:

- **Which app/package** is the target, if a monorepo has more than one plausible candidate.
- **Evaluation identity**: which key (user ID, account ID, device ID, anonymous ID) and traffic type the flag should evaluate against, when more than one candidate identity exists (session user vs. tenant vs. request-scoped actor).
- **Treatment-to-behavior mapping**: which treatment name(s) map to which code path, when the flag isn't a plain on/off pair.
- **Fallback behavior**: what the application should do when the SDK returns `control` or isn't ready yet — a product decision, not something to infer.
- **Extension needs**: whether the wrapper should expose hooks for logging, caching, or analytics beyond evaluation (see [Extension points](#extension-points)).

Don't re-ask something already pinned by an existing wrapper, config, or a prior answer in this conversation.

## Phase 3: SDK / provider identification

Once language and runtime are known, confirm which contract applies — the three are not interchangeable:

| Contract | Signal | Evaluation shape |
|---|---|---|
| FME native SDK | Language-specific Split/FME dependencies from the detection reference | Treatment values are **names**, not booleans; batch, config and asynchronous APIs have their own result shapes |
| OpenFeature + FME provider | `@openfeature/*` plus a Split/FME provider package | `getBooleanValue`/`getStringValue`/etc., each typed, with OpenFeature's own default/`ERROR` reason semantics |
| Classic Harness FF | `@harnessio/ff-*`, `boolVariation`/`stringVariation`/`numberVariation`/`jsonVariation` | Typed variation call with an explicit **default value** argument; a different product and contract from FME |

Verify the exact method, arguments, synchronous/asynchronous behavior and result shape against the installed package's version/types and official docs — don't assume a shared signature or return type. For OpenFeature, verify that the actual configured provider targets the intended FME project/environment; the generic API alone is not evidence. Classic FF is a different product: stop and clarify rather than modifying its integration under an FME workflow.

## Reuse before building a wrapper

Search for an existing application-owned abstraction before touching the SDK directly (see [sdk-patterns.md](sdk-patterns.md#wrapper-detection-reuse-before-building) for grep signals).

- **Wrapper exists** → extend it. Add the new flag/call through the existing pattern; don't bypass it with a direct SDK call alongside it.
- **No wrapper exists** → recommend a thin, idiomatic, app-owned facade scoped to this application (a plain service/module for most backends, a custom hook for React, the equivalent per-language idiom) and confirm with the user before creating it. Its job is to isolate call sites from the raw SDK so the team can extend it later — it is not a generic cross-project framework, and must not be copied verbatim from another language's pattern.
- **Direct integration instead of a wrapper** is an exception, not the default: if the language/framework or existing conventions make a wrapper impractical, explain the tradeoff and obtain the user's explicit choice before using direct calls.

### What the wrapper centralizes

- **Initialization and readiness**: reuse the existing factory/client lifecycle appropriate to the SDK, environment and identity; don't instantiate clients per evaluation. Follow documented readiness/loading behavior, including framework hook ordering and subscription cleanup. Do not destroy a shared client to complete one check.
- **Identity and traffic type resolution**: resolve the evaluation key and traffic type in one place, matching the Phase 2 answer. Don't store it in a single mutable value shared across concurrent requests on a server — scope it per request/session the way the runtime already does.
- **Evaluation delegation**: preserve the installed SDK/provider's treatment/config and asynchronous semantics. Never treat a nonempty treatment string as enabled. A boolean facade is appropriate only with an explicitly approved mapping from named treatments; expose details when callers need them.
- **Configuration**: preserve the documented config result shape. Parse/validate only where the application's contract calls for it; handle absent or malformed config through the agreed error/fallback behavior rather than introducing an uncaught parse failure.
- **Fallback**: confirm behavior for `control`, unexpected treatments, not-ready/error states and missing/malformed config. Some SDK versions support configured fallback treatments: inspect that configuration's non-secret metadata and verify its contract. A plausible treatment from fallback, cache, offline mode or a mock is not proof of live evaluation.

### Extension points

Only implement extensions (logging, metrics, caching, feature-usage analytics) that the user explicitly requests and approves; do not build a plugin framework speculatively. Tracking belongs to `/instrument-metric`, not an unannounced wrapper side effect. Never expose secrets or SDK keys through logs, caches or extension payloads. Keep subject identifiers and PII out of diagnostic output by default; use non-sensitive status metadata. Any proposed telemetry must have an explicit privacy-reviewed contract, and caching must preserve the SDK's freshness and evaluation semantics.

## Credentials and dependencies

Server-side SDK keys never belong in a browser bundle; browser/mobile SDKs use their own client-side key type. SDK keys are not Harness admin API tokens. Reuse the existing environment-variable or secret-manager reference; never print, request, pass through tool arguments, or hardcode its value. Inspect only non-secret configuration metadata, not credential-file contents. The declared FME tools do not retrieve SDK keys; an authorized user provisions missing credentials through the supported UI/admin flow. Confirm environment and endpoint metadata without guessing custom hosts. Detect the package manager from lockfiles and obtain approval before adding/changing dependencies or configuration; preserve unrelated settings.

## Stop conditions

- Can't determine the installed SDK/provider version or its real method signature from types/docs/existing calls → ask or stop; don't guess a shape from another language.
- More than one plausible identity/traffic type with no existing convention to settle it → ask (Phase 2), don't default to an anonymous key.
- Monorepo with multiple candidate apps and no indication which one the user means → ask which app before touching any file.
- No application source access at all → stop at guidance; label implementation unverified.

## Official references

- [FME documentation hub](https://developer.harness.io/docs/feature-management-experimentation/)
- [FME client-side SDKs](https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/client-side-sdks/)
- [FME server-side SDKs](https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/server-side-sdks/)
- [FME React SDK](https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/client-side-sdks/react-sdk/)
- [FME fallback treatments](https://developer.harness.io/docs/feature-management-experimentation/feature-management/setup/fallback-treatment/)
- [FME OpenFeature providers](https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/openfeature/nodejs-sdk/)
- [OpenFeature provider concept](https://openfeature.dev/docs/reference/concepts/provider)
- [Classic Harness Feature Flags SDK reference](https://developer.harness.io/docs/feature-flags/use-ff/ff-sdks/server-sdks/node-js-sdk-reference/)
