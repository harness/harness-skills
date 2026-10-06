---
name: create-feature-flag
description: >-
  Create a new Harness FME feature flag and optionally its per-environment
  definitions with a safe default, following the project's existing naming and
  tagging conventions. Explore existing flags to infer patterns, then propose
  and create the flag with treatments, traffic type, and initial targeting
  (default: everyone gets the off/safe treatment). Use when asked to create a
  feature flag, add a flag, set up a new FME flag, or initialize flag targeting.
  Do not use for updating existing flag targeting (update-flag-targeting), deep
  analysis of a single flag (explain-flag), listing/discovering flags
  (discover-feature-flags), managing flag lifecycle operations like
  archive/delete (manage-flag-lifecycle), managing segments (manage-segments),
  creating experiments (manage-experiments), pipeline-driven rollouts
  (fme-pipeline), or removing flags from code (cleanup-feature-flags).
  Trigger phrases: create feature flag, add flag, new flag, set up flag, FME
  flag create, initialize flag.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp
license: Apache-2.0
compatibility: Requires the Harness MCP server or the Harness CLI
---

# Create Feature Flag

Create a new Harness FME feature flag and optionally its per-environment definitions with safe defaults, following the project's existing conventions. Related: `update-flag-targeting` (ramp), `manage-experiments` (A/B test).

## Tools

Works through the Harness MCP server or the Harness CLI; names are from [tool-map.md](../../references/fme/tool-map.md).

| Operation | MCP | CLI |
|-----------|-----|-----|
| List flags | `harness_list` · `fme_feature_flag` · `size: 50` · `compact: false` | `harness list feature_flag --json --limit 50` |
| Get flag | `harness_get` · `fme_feature_flag` · `params.feature_flag_name` | `harness get feature_flag <name> --json` |
| List environments | `harness_list` · `fme_environment` · `compact: false` | `harness list fme_environment --json` |
| List traffic types | `harness_list` · `fme_traffic_type` · `compact: false` | `harness list traffic_type --json` |
| Get definition | `harness_get` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` | `harness get feature_flag:definition <flag> --env <env-id> --json` |
| Create flag | `harness_create` · `fme_feature_flag` · `body: { name, trafficType, description?, tags?, owners? }` | `harness create feature_flag <name> --traffic-type <type> --set description="..."` plus `--add tags.<name>` per tag, or `-f flag.json` with the full approved body (CLI's `tags`/`owners` are collection fields — `--set tags=[...]` isn't valid syntax) |
| Create definition | `harness_create` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments, defaultTreatment, defaultRule, comment? }` | `harness create feature_flag:definition <flag> --env <env-id> -f def.json` |

## Instructions

### Phase 1: Scope

Follow [scope-establishment.md](../../references/scope-establishment.md). Restate: `Working in org=..., project=...`.

### Phase 2: Explore conventions

**List flags** (≤50) to infer naming pattern (kebab-case, prefixes), common tags, and usual traffic type. **List traffic types.** **List environments** and note isProduction. Optionally **get definition** from 1–2 similar flags to learn treatment names. Summarize conventions in 3 bullets.

### Phase 3: Propose

Based on conventions and user's purpose, propose:
- **Name:** Follow the convention (let API validate; don't invent character rules).
- **Traffic type:** Must exist in traffic types list.
- **Treatments:** Default `on`/`off` or user-specified. Never `control` (reserved; see [concepts.md](../../references/fme/concepts.md)).
- **Safe default:** See [targeting-recipes.md](../update-flag-targeting/references/targeting-recipes.md#i-initialize-a-definition-where-none-exists) for the definition body.
- **Environments to initialize:** Default = all non-production. Production only if asked.
- **Tags, description:** Follow the convention. Include linked ticket if provided.
- **Owners:** Never auto-pick from convention alone. Show the owners found on similar flags as candidates and ask the user to explicitly confirm who the owner(s) should be for this flag before including them in the plan.

**Name collision check:** **Get flag** (expect 404); if it exists, route to `/update-flag-targeting`.

### Phase 4: Plan and confirm

Follow [write-safety.md](../../references/fme/write-safety.md). Show the plan:
```
Plan: Create feature flag `<name>` — <purpose>
Flag metadata: name, traffic type, description, tags, owners
Initial definitions:
| Environment | isProduction | Targeting |
| <env-name>  | No           | 100% <defaultTreatment> (everyone gets safe/off treatment) |
Production: <"No definitions" or list production envs>
```
STOP and wait for explicit confirmation.

### Phase 5: Execute

**Create flag.** Then **create definition** for each environment (non-production first). Audit comment: `"create-feature-flag: initial definition with safe default — <ticket or purpose>"`.

If a definition create fails partway through, report exactly which environments succeeded and which failed — don't assume state; **get flag** and **get definition** for each target environment to read back what's actually live. Resume from that live state: create only the missing/failed definitions, don't delete and restart the whole flag. Only offer to delete the flag if the user asks for a clean restart. On 400 validation error, fix per [schema-validation-loop.md](../../references/schema-validation-loop.md).

### Phase 6: Verify

**Get flag** and **get definition** for each environment. Restate:
```
Created flag `<name>` (<trafficType>).
- In <env1>, <env2>: everyone gets `<defaultTreatment>`.
- Production / other environments: no definition, SDKs return `control`.
```

Link [sdk-patterns.md](../../references/fme/sdk-patterns.md) for adding the flag to code. Next steps: `/update-flag-targeting` (ramp), `/manage-experiments` (A/B test).

## Examples

- "Create a feature flag for the new checkout flow" — Infer conventions, propose name, create flag + non-prod definitions.
- "Add a dark mode flag for users in dev and staging" — Create flag, initialize dev and staging only.
- "Set up a flag for FME-1234 with treatments `v1` and `v2`" — Use ticket in tags/description, create flag with custom treatments.
- "I need a feature flag" — Ask for purpose, infer conventions, propose name and traffic type.

## Performance Notes

- Convention inference: ~3–5 read-only calls (flags list, traffic types, environments, optional definitions sample, collision check).
- Write calls: 1 flag create + N definition creates (sequential, not parallel).
- Pagination: See [tool-map.md](../../references/fme/tool-map.md#pagination).

## Troubleshooting

| Problem | Solution |
|---------|----------|
| 409 "flag already exists" | Name collision. Route to `/update-flag-targeting` or pick a different name. |
| 400 "invalid name" or "invalid traffic type" | Use the API message to correct. Don't invent character rules. |
| User wants to update existing flag | STOP. Route to `/update-flag-targeting`. |

See [tool-map.md](../../references/fme/tool-map.md#common-errors) for generic errors.
