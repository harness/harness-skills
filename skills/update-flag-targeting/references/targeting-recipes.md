# Targeting Recipes

## Tools

| Operation | MCP | CLI |
|-----------|-----|-----|
| Update definition | `harness_update` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { <fields>, comment }` | `harness update feature_flag:definition <flag> --env <env-id> -f patch.json --comment "<text>"` |
| Create definition | `harness_create` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments, defaultTreatment, defaultRule, ... }` | `harness create feature_flag:definition <flag> --env <env-id> -f def.json` |

Each recipe (except kill/restore) is a merge-patch for **Update definition**.

Rules for every patch:
- Start from the live definition. Copy shapes from it. Never compose them from memory.
- Send only the top-level fields you change, but send each array (`treatments`, `rules`, `defaultRule`) **whole**.
- Keep untouched rules byte-for-byte as read, including fields not shown here (such as `negate`).
- Treatment names come from the live `treatments` array and are case-sensitive. In every `defaultRule` and rule, the bucket `size`s sum to 100.

Semantics (evaluation order, `defaultTreatment`, `control`) are in [concepts.md](../../../references/fme/concepts.md).

Operations:

## (a) Ramp the default rule

```json
{ "defaultRule": [ { "treatment": "on", "size": 10 }, { "treatment": "off", "size": 90 } ] }
```

Plan wording: "Everyone not matched by a target or rule: 10% `on` / 90% `off`."

## (b) Ramp one rule

Copy the full `rules` array and change only that rule's `buckets`:

```json
{ "buckets": [ { "treatment": "on", "size": 50 }, { "treatment": "off", "size": 50 } ],
  "condition": { ...unchanged... } }
```

## (c) Add, edit, remove, or reorder rules

A rule is `{ buckets: [{treatment, size}], condition: { combiner: "AND"|"OR", matchers: [{ type, attribute, ... }] } }`. Documented matcher types are listed in [concepts.md](../../../references/fme/concepts.md#rule-and-target-shapes-round-trip-dont-compose-from-memory).

```json
{ "buckets": [ { "treatment": "on", "size": 100 } ],
  "condition": { "combiner": "AND",
    "matchers": [ { "type": "IN_LIST_STRING", "attribute": "plan", "strings": ["enterprise"] } ] } }
```

- **Add**: rules match top to bottom and the first match wins, so position matters. If rules already exist, ask where the new one goes.
- **Remove**: keys it matched fall through to later rules or the default rule. Say where they land in the plan.
- **Reorder**: same rules in a new order. Say which keys change treatment.
- **Segment matcher**: copy the matcher shape from a live rule that already uses one. Check that the segment has a definition in the target environment.
- **Flag dependency**: `{ "type": "IN_SPLIT", "depends": { "splitName": "parent-flag", "treatment": "premium" } }`. Check that the parent flag has a definition in the target environment and serves that treatment.

## (d) Individual targets

The update schema doesn't document an individual-targets field, so round-trip it:

1. Find the individual-targets structure in the live definition.
2. Change only the keys and write the structure back with everything else unchanged.
3. If this definition has no targets yet, copy the shape from another definition in the project that has them. If none exists, try the change in a non-production environment first.

Never invent the shape. Targets are evaluated before rules, so a targeted key ignores every rule.

## (e) Default treatment

```json
{ "defaultTreatment": "off" }
```

Killed traffic and traffic outside `trafficAllocation` get this treatment. It must be in `treatments`. If the flag is killed in that environment, the change hits everyone immediately, so say so.

## (f) Traffic allocation

```json
{ "trafficAllocation": 50 }
```

This limits exposure: keys outside the percentage get `defaultTreatment` and aren't counted in experiments. It doesn't set the split between treatments. Lowering it moves some keys to `defaultTreatment` immediately, so say so in the plan.

## (g) Treatments

- **Add**: send the full `treatments` array including the new one (`{ "name": "v3", "configurations": "{\"color\":\"blue\"}" }`). It serves no traffic until a bucket or target references it.
- **Rename or remove**: update every reference in the same patch (`defaultTreatment`, `baselineTreatment`, `defaultRule`, `rules`, targets). Warn that code comparing against the old name stops matching. Check experiments first, because an ACTIVE experiment may use it as baseline or comparison.
- **Configurations**: a JSON string returned by `getTreatmentWithConfig`. Keep it valid JSON and show the before/after of the config.
- Never name a treatment `control`.

## (h) Copy one environment to another

1. Read the source and target definitions.
2. Build the body from **only** these source fields: `treatments`, `defaultTreatment`, `defaultRule`, `rules`, `baselineTreatment`, `trafficAllocation`. Copy individual targets only if the user asks, and round-trip them per (d). Drop everything else (IDs, timestamps, `lastImpressionAt`, killed state).
3. Every segment referenced in the copied rules or targets must have a definition in the target environment. Every `IN_SPLIT` parent must be defined there too. Stop and report if any is missing.
4. If the target has no definition, **Create definition**. Otherwise **Update definition** with the same body.
5. Killed state isn't copied. If the target is killed it stays killed, and a killed source doesn't kill the target. Say which applies.

Plan wording: "This overwrites targeting in `<target>`." For production: "This overwrites live production targeting in `<target>`. Apply?"

## (i) Initialize a definition where none exists

Use this when the flag exists but has no definition in the environment, so SDKs there get `control`. Reuse treatment names from another environment's definition if there is one, so code checks still match. Otherwise ask, defaulting to `on`/`off`. Create it with the same call as (h) step 4:

```json
{ "treatments": [ { "name": "on" }, { "name": "off" } ],
  "defaultTreatment": "off",
  "defaultRule": [ { "treatment": "off", "size": 100 } ] }
```

Plan wording: "`<env>` has no definition, so SDKs get `control`. After: everyone gets `off`." Ramp afterwards with (a).

## (j) Kill and restore

These are execute actions, not patches. Use the commands in the SKILL.md Tools table.
- **Kill**: everyone in that environment gets `defaultTreatment`. Name the treatment in the plan.
- **Restore**: the previous targeting resumes. Describe it from the live definition read before the restore.
