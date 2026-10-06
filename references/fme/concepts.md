# FME Concepts

FME (Feature Management & Experimentation, formerly Split) semantics that skills most often get wrong. Read this before planning a flag write or explaining a flag's behavior. Exact tool names live in [tool-map.md](tool-map.md).

## Flag vs Definition

| | Feature flag | Definition |
|---|---|---|
| Scope | Once per project, all environments | Once per flag per environment |
| Holds | name, description, traffic type, tags, owners, rollout status, status (ACTIVE / ARCHIVED) | treatments, `defaultTreatment`, `defaultRule`, `rules`, individual targets, `trafficAllocation`, `baselineTreatment`, `isKilled`, `impressions.lastImpressionAt` |
| Write | metadata only | targeting |

A flag can exist with no definition in an environment. SDKs in that environment get `control` for it.

## Treatments, `control`, and Baseline

- **Treatments** are the named variants a definition can serve, for example `on`/`off` or `v1`/`v2`/`v3`. Each has a `name` and optional `configurations` (a JSON string that SDKs return from `getTreatmentWithConfig`). Names are case-sensitive and user-defined, so read them, never guess.
- **`control`** is reserved. The SDK returns it when it **can't evaluate**: the SDK isn't ready, the flag doesn't exist or is archived, the environment has no definition, or there's an error. Code must treat `control` as "fall back to the safe path". Never create a treatment named `control`.
- **`baselineTreatment`** is the treatment that experiments compare against. It has nothing to do with `control`.

## How a Definition Serves Traffic

Evaluate in this order and stop at the first step that applies:

1. **Killed**: everyone gets `defaultTreatment`.
2. **Individual targets**: listed keys (or segments) get their assigned treatment.
3. **Traffic allocation**: keys outside `trafficAllocation`% get `defaultTreatment`, and experiments don't count them.
4. **Targeting rules**, top to bottom. The first rule whose condition matches buckets the key by that rule's `{treatment, size}` percentages.
5. **Default rule**: everyone left is bucketed by `defaultRule` (`{treatment, size}` pairs summing to 100).

Consequences:
- `defaultTreatment` is **not** "what most users get". It's what killed traffic and excluded traffic get. The default rule decides the remaining population.
- `trafficAllocation` limits exposure. It is **not** the split between treatments, which is set by bucket `size`s.
- Bucketing is deterministic per key, so the same key gets the same treatment until the targeting changes.
- A single-environment read isn't enough to describe a flag. Read every environment's definition.

## Rule and Target Shapes: Round-Trip, Don't Compose From Memory

- A rule is `{ buckets: [{treatment, size}], condition: { combiner: "AND"|"OR", matchers: [...] } }`.
- Matcher types:
  - `IN_LIST_STRING` (`strings`)
  - `GREATER_THAN_OR_EQUAL_NUMBER` / `LESS_THAN_OR_EQUAL_NUMBER` (`number`)
  - `BETWEEN_NUMBER` (`between: {from, to}`)
  - `BOOLEAN` (`bool`)
  - `ON_DATE` (`date`, epoch ms)
  - `IN_SPLIT` (`depends: {splitName, treatment}`): a **flag dependency** on another flag's treatment
- Segment matchers and individual-target fields also exist. To change them, read the definition, edit the matching structure, and write it back unchanged everywhere else. Copy shapes from an existing definition in the project. If none uses the shape, validate with a non-production environment first.
- In updates, `rules`, `treatments` and `defaultRule` are arrays and are **replaced whole**. Always send the complete array.

## Kill, Restore, Reallocate, Archive, Delete

| Action | Scope | Effect |
|---|---|---|
| Kill | one environment | Serves `defaultTreatment` to **all** traffic. It's not "off" unless `defaultTreatment` is the off treatment, so say which treatment users will get. |
| Restore | one environment | Undoes a kill. The previous targeting resumes. |
| Reallocate | one environment | Re-hash traffic distribution without a full targeting update. Other semantics are unverified. Only use it when asked by name, and warn that keys may change treatment. |
| Archive | flag, all environments | Cascades to every definition. SDKs return `control` from then on. It's reversible with unarchive (409 if dependents block it). |
| Delete flag | flag | Hard delete. Also deletes every environment's definition. Fails (often with an unhelpful server error) if another flag depends on it or a change approval is pending. Prefer archive. |
| Delete definition | one environment | Removes targeting in that environment, so SDKs there get `control`. |

## Environments

Environments have an `isProduction` field. Treat any production environment as high-risk for writes (see [write-safety.md](write-safety.md)). Environment names are at most 15 characters, and most operations require the environment ID.

## Segments

- Types: `STANDARD` (key list), `LARGE` (key list at a larger scale), `RULE_BASED` (membership from rules, no key list). Most operations need segment type, and the type can't be changed after creation.
- Segment metadata is project-wide. Per-environment segment definitions hold the keys, managed with list/add/remove key operations. A segment does nothing in an environment until it has a definition there.
- Flags reference segments in their rules and targets. Before changing or deleting a segment, scan the definitions that use it, because there's no reverse-lookup API.

## Definition state checklist

Per-environment fields to read and describe:
- `isKilled` (boolean): whether all traffic gets `defaultTreatment`
- `defaultTreatment`: treatment served to killed traffic, excluded traffic, and fallback
- `treatments`: available treatment variants
- `defaultRule`: bucketing for traffic not matched by any targeting rule
- `rules`: top-to-bottom targeting rules (condition + buckets)
- Individual targets: keys/segments assigned specific treatments
- `trafficAllocation` (%): limits exposure; outside → `defaultTreatment`
- `baselineTreatment`: experiment baseline (not related to `control`)
- `impressions.lastImpressionAt` (ISO-8601, null = never, absent = unknown): last SDK evaluation
- `flagSets`: flag set membership for batch SDK calls

## Staleness and readiness

**Default threshold:** 30 days (user may override). Staleness buckets describe traffic per environment:
- **Stale:** `impressions.lastImpressionAt` exists and > threshold
- **Active:** within threshold
- **Unknown:** `impressions` field absent
- **Never evaluated:** `lastImpressionAt` is null

**Verdict labels** describe whether a flag is ready to **archive**:
- **ready**: every production env is stale (or never evaluated), and nothing blocks.
- **caution**: an env is unknown, a non-prod env is active, the user overrode the threshold, or a PAUSED experiment exists. Proceed only with explicit acknowledgement.
- **blocked**: an ACTIVE experiment, any production env active within the threshold, or a confirmed dependent (IN_SPLIT / segment) when that check was run.

Never infer "unused" from missing data. Archived flag with recent impressions = risk (code may still get `control`).

## Experiments and metrics

**Experiment statuses:** ACTIVE (running, don't change targeting), PAUSED (safe to change with explicit acknowledgement), COMPLETED (ignore), ARCHIVED (deleted-like).

**Parent types:** FEATURE_FLAG (common), AI_CONFIG (AI flags). CONFIG exists in the API but returns 404.

**Baseline vs comparison:** `baselineTreatment` is what the experiment compares against. Never call it `control` (that's the SDK fallback).

**Metric categories:**
- In experiment: `keyMetrics` (primary), `supportingMetrics` (secondary)
- In workspace: GUARDRAIL, ALERT (workspace-wide monitoring)

**Event types:** Event inventory covers the project's last 30 days across environments. **Get event type** uses the exact event name; check the returned `trafficTypes` too. A 200 is historical visibility, not proof of current flow, target-environment delivery, or experiment attribution. A 404 can mean wrong scope/name, no instrumentation, or an idle event; absence from a filtered or partial list is inconclusive. Confirm scope and recent application activity before handing off to `/instrument-metric` to investigate. See [tool-map.md](tool-map.md#fme_event_type) for transport details.

**Hypothesis form:** "If we \<change>, then \<metric> will \<direction> because \<reason>."

**Results:** count only impressions whose label matches the experiment's `rule` (normally `default rule`), so individual targets and other rules are excluded. SRM (sample ratio mismatch) not exposed by API. Avoid peeking before experiment completion.

**Metric design guidance:** see [metric-design.md](metric-design.md) for what makes a good metric and how to map intent to configuration.

## Other Things Code Search Can Miss

- **Flag sets**: SDKs can fetch flags by set (`getTreatmentsByFlagSet(s)`), so a flag in use may never appear by name in code.
- **Dependencies**: an `IN_SPLIT` matcher in another flag makes that flag depend on this one. Archiving or retargeting this flag changes the dependent flag's behavior.
- **Experiments**: an ACTIVE experiment on the flag means targeting changes affect the experiment's validity.

## Change Requests and Approvals

Governance policies (OPA) can block a write (409) or turn it into a pending approval. Report the response as-is. Never retry around it, never try another route, and never delete to work around a blocked archive.
