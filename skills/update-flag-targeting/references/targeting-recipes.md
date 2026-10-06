# Targeting Recipes

## Tools

| Operation | MCP | CLI |
|-----------|-----|-----|
| Update definition | `harness_update` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { <fields>, comment }` | `harness update feature_flag:definition <flag> --env <env-id> -f patch.json` |
| Create definition | `harness_create` · `fme_feature_flag_definition` · `params: { feature_flag_name, environment_id }` · `body: { treatments, defaultTreatment, defaultRule, ... }` | `harness create feature_flag:definition <flag> --env <env-id> -f def.json` |

Each recipe (except kill/restore) is a merge-patch for **Update definition**.

Rules for every patch:
- Start from the live definition. Copy shapes from it. Never compose them from memory.
- Put `comment` and any supported `title` inside the approved CLI patch file, just as in MCP `body`. File input takes precedence; a separate `--comment` flag is not merged into it.
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
- **Segment matcher**: copy a live matcher shape, resolve STANDARD/LARGE/RULE_BASED, then verify the target-environment definition through [that type's workflow](../../manage-segments/SKILL.md#phase-3-execute-operation). An unavailable tool operation means unverified, not missing. Never substitute a STANDARD definition lookup for another type.
- **Flag dependency**: `{ "type": "IN_SPLIT", "depends": { "splitName": "parent-flag", "treatment": "premium" } }`. Check that the parent flag has a definition in the target environment and serves that treatment.

## (d) Individual targets

The update schema doesn't document a standalone "targets" field. In the live definitions seen so far, individual-target membership is nested per treatment, inside each entry of the `treatments` array: fields such as `keys`, `segments`, `largeSegments`, and `ruleBasedSegments` hold the keys/segments assigned to that specific treatment. There is no supported top-level `targets` field; never add one to a JSON body.

1. Read the live `treatments` array and find which treatment(s) already carry `keys`/`segments`/`largeSegments`/`ruleBasedSegments` entries.
2. To add or remove individual targets, edit only the membership array(s) on the relevant treatment entry (by treatment name) and leave every other treatment's fields - including empty membership arrays, which mean "no individual targets", not "unknown" - byte-for-byte as read.
3. Send the whole `treatments` array back (arrays are replaced whole on update), so untouched treatments must be copied unchanged.
4. If this definition's treatments have no membership fields yet, copy the shape from another definition in the project that has them. If none exists, try the change in a non-production environment first.

Never invent the shape or a top-level `targets` key. Individual targets are evaluated before rules, so a targeted key ignores every rule.

## (e) Default treatment

```json
{ "defaultTreatment": "off" }
```

Killed traffic and traffic outside `trafficAllocation` get this treatment. It must be in `treatments`. If the flag is killed in that environment, the change hits everyone immediately, so say so.

## (f) Traffic allocation

```json
{ "trafficAllocation": 50 }
```

This limits exposure: keys outside the percentage get `defaultTreatment` and aren't counted in experiments. It doesn't set treatment allocation. Lowering it moves some keys to `defaultTreatment` immediately, so say so in the plan.

## (g) Treatments

- **Add**: send the full `treatments` array including the new one (`{ "name": "v3", "configurations": "{\"color\":\"blue\"}" }`). It serves no traffic until a bucket or target references it.
- **Rename or remove**: update every reference in the same patch (`defaultTreatment`, `baselineTreatment`, `defaultRule`, `rules`, targets). Warn that code comparing against the old name stops matching. Check experiments first, because an ACTIVE experiment may use it as baseline or comparison.
- **Configurations**: a JSON string returned by `getTreatmentWithConfig`. Keep it valid JSON and show the before/after of the config.
- Never name a treatment `control`.

## (h) Copy one environment to another

`treatments` entries are not just `{name, configurations}` - they can also carry per-treatment individual-target membership (`keys`, `segments`, `largeSegments`, `ruleBasedSegments`; see (d)). Copying `treatments` wholesale from the source would silently copy the source's memberships onto the target (or wipe the target's existing memberships if the source has none), neither of which the user asked for. Handle `treatments` separately from the rest of the body:

1. Read the source and target definitions.
2. Copy only approved source configuration fields (`defaultTreatment`, `defaultRule`, `baselineTreatment`, `trafficAllocation`). Preserve destination `rules` by default; copying/replacing rules must be an explicitly approved part of the plan. For a new destination use no rules unless approved. Drop response-only fields (IDs, timestamps, `lastImpressionAt`, killed state).
3. **Rebuild `treatments`, not copy it.** For each treatment **name** present in the source's `treatments`:
   - Copy `name` and `configurations` from the source (this is the part the user is actually asking to copy).
   - For membership fields (`keys`, `segments`, `largeSegments`, `ruleBasedSegments`): default to the **target's existing values** for that treatment name (unchanged), not the source's. Only copy the source's membership for a treatment if the user explicitly opts in to copying memberships too. An empty array in either side means "no members" and must be preserved as empty, not dropped or treated as "unset".
   - If the target has a treatment name with memberships that the source's `treatments` array no longer contains, the merge would drop that treatment (and its memberships) entirely. Stop and report the conflict; don't silently remove it. Proceed only with the user's explicit resolution (keep the target-only treatment, or confirm its removal).
4. Every referenced segment must have a target-environment definition verified through its STANDARD/LARGE/RULE_BASED workflow; every `IN_SPLIT` parent must also exist there. Stop on a missing or unverified dependency; do not validate LARGE/RULE_BASED with a STANDARD endpoint.
5. If the target has no definition, **Create definition**. Otherwise **Update definition** with the rebuilt body.
6. Killed state isn't copied. If the target is killed it stays killed, and a killed source doesn't kill the target. Say which applies.

Plan wording: "This copies the approved configuration into `<target>`, preserving its rules and individual/segment memberships unless you explicitly approved replacing them." Name every overwrite/removal. For production or changes to a killed flag's served default/configuration, disclose the immediate live impact before confirmation.

## (i) Initialize a definition where none exists

Use this when the flag exists but has no definition in the environment, so SDKs there get `control`. Reuse treatment names from another environment's definition if there is one, so code checks still match. Otherwise ask, defaulting to `on`/`off`. Create it with the same call as (h) step 4:

```json
{ "treatments": [ { "name": "on" }, { "name": "off" } ],
  "defaultTreatment": "off",
  "defaultRule": [ { "treatment": "off", "size": 100 } ] }
```

Plan wording: "`<env>` has no definition, so SDKs get `control`. After: everyone gets `off`." Ramp afterwards with (a).

## (j) Kill and restore

These are execute actions, not patches. Use the commands in the SKILL.md Tools table. The native API exposes kill and restore as two separate actions — there is no documented atomic "update targeting and un-kill in one call", so don't invent one.

- **Kill**: everyone in that environment gets `defaultTreatment`. Name the treatment in the plan.
- **Restore is not the first step when the goal is to change targeting on a killed flag.** Restoring immediately resumes whatever targeting was live *before* the kill, which is very often exactly the traffic pattern the kill was meant to stop. Safe order:
  1. Inspect the full patch. Killed traffic stays unchanged only if `defaultTreatment` and its configuration remain unchanged; recipes (e), (g) or (h) may affect everyone immediately. Disclose and explicitly approve that impact. Apply the approved targeting/allocation/rule changes while still killed.
  2. **Verify** the new definition is live (re-read it) before touching kill state at all.
  3. Only then, as a separate confirmed step, run the [experiment check](../../../references/fme/write-safety.md#experiment-check) again (restoring resumes live traffic, same risk class as any production targeting write) and **Restore**.
  4. Describe what resumes from the definition read in step 2, not from memory of the pre-kill state — the whole point of step 1 is that it's no longer the pre-kill state.
