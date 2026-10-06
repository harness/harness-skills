# Segment Usage Gate

Required before **every segment mutation**, not just deletion. The gate identifies configuration dependencies, not observed traffic or application-code usage. Apply the same requirements through CLI, MCP and the Harness rule editor.

## Operation coverage

| Mutation | Required impact review |
|----------|------------------------|
| Create metadata, including a new name | Confirm exact name/type uniqueness and scan for pre-existing references; a new metadata record does not prove no rule already mentions it |
| Update description, tags or owners | Complete the reference check; distinguish metadata-only edits from evaluation changes |
| Create or update an environment definition | Complete the project scan and highlight references in the affected environments |
| Add, remove or replace STANDARD keys | Show direct/indirect consumers and the membership effect before approving the key changes |
| RULE_BASED rules, exclusions or enabled state | Trace dependent segments and flags; preserve unrelated configuration and show the exact editor change |
| Delete a definition | Block for direct or indirect references in that environment; resolve them under separate approval and rerun the gate |
| Delete segment metadata | Block for any remaining reference or active environment definition; resolve dependencies separately before deletion |

For all rows: resolve native account/org/project, exact segment name **and type**, traffic type, environment IDs and production markers. Approval for the intended payload does not waive this gate.

## 1. Inventory before definition reads

1. Fully paginate **all project flags**, including ACTIVE and ARCHIVED. Remove name, tag, owner, traffic-type and rollout-status filters. Explicitly include both statuses if the selected list form filters status. Deduplicate by stable identity only after advancing offsets by the raw page length.
2. Fully paginate environments and segment metadata for **every type and every status, including ACTIVE and ARCHIVED**. Confirm status coverage rather than accepting a default ACTIVE-only list. Keep exact case-sensitive name/type identities; STANDARD `beta` and LARGE `beta` are different segments.
3. Apply [pagination completeness checks](../../../references/fme/tool-map.md#pagination). A full page with a page-length `total` still needs another request, including an empty page for exact multiples. Any failed, skipped or non-advancing page makes coverage incomplete.
4. If **more than 50 flags**, STOP **before any flag-definition reads** and ask approval for the full cost: one paginated definition inventory per flag, pre-write revalidation, and applicable experiment checks, potentially more requests. **Do not offer narrowing for a pre-write gate.** Declined cost approval blocks the mutation. A filtered read-only usage report must never be reused as write clearance.

## 2. Direct flag references

For every flag, fully paginate definitions across **all environments**, using the resource-specific pagination parameters in the tool map. The requested target-environment subset does not narrow this inventory.

Inspect both locations in every definition:
- Segment matchers under `rules[].condition.matchers`, preserving rule index, combiner and any negation. Use the actual verified matcher layout, not a raw JSON substring search.
- Each treatment's `segments`, `largeSegments` and `ruleBasedSegments` arrays, mapped respectively to STANDARD, LARGE and RULE_BASED. Resolve returned element shapes explicitly; unrelated text in descriptions/configurations is not a reference.

Match exact segment name **and type**. Retain negated references, killed definitions and ARCHIVED flags: inactive configuration is still a dependency and can be restored. A recognized absence is different from an unparsed rule shape or a missing page. Unknown relevant fields, nesting, identity or type make the gate incomplete; never silently classify them as no match.

## 3. Indirect RULE_BASED dependencies

Use the complete RULE_BASED metadata inventory to determine which rule configurations must be inspected. If the project has none, record that complete-inventory finding rather than assuming it.

For every RULE_BASED segment and relevant environment, obtain authoritative current rules/exclusions and enabled state through the confirmed read workflow or user-provided saved rule-editor configuration. Ask for redacted personal keys, not credentials; preserve segment names, types and scope identifiers needed for the check. Verify coverage against the metadata/environment inventory; an unsaved draft or a sample of matching users is not dependency evidence.

Build type-aware edges for segment references in conditions and exclusions. Trace reverse dependencies transitively: if segment B excludes A and flag F targets B, changing A can affect F. Include segment consumers even when no flag directly targets them. Use a visited set keyed by scope, environment, name and type to terminate cycles; report cycles and their consumers rather than dropping those edges. Disabled and ARCHIVED segment configurations remain potential dependencies; include their references and consumers even when they are not currently active.

Any unresolved definition, reference shape or dependency chain is **incomplete** and blocks the write. Request the required saved configuration; never substitute missing evidence with an acknowledgement or an "unused" verdict.

## 4. Present impact and approve

Report `Usage: checked — N of M flags; all environment pages complete` only when the direct and indirect checks have finished. Otherwise report `Usage: incomplete — checked N of M flags`, identify unresolved environments/segments, and **STOP**. If the flag inventory itself is unfinished, use an unknown total or a lower bound rather than inventing M.

Show a concise impact table: `| Consumer flag/segment | Env | Direct or via segment | Rule/treatment/exclusion location | State |`. Redact personal keys. A reference is not proof that users match it.

- For membership/rule/enable-state changes, explain the effect on each consumer and run the [experiment check](../../../references/fme/write-safety.md#experiment-check) for every affected flag/environment, including indirect consumers. Complete ACTIVE/PAUSED pages and apply the targeting-change acknowledgement policy before approval; metadata-only edits do not need this experiment check.
- For metadata-only changes, state that membership/targeting is unchanged; do not invent a live-traffic effect.
- For deletion, **references block the delete before execution**. Use `update-flag-targeting` or the rule-editor workflow under separate approval to resolve them, then rerun the gate. No automatic cascade or deletion workaround.
- Apply the [write-safety protocol](../../../references/fme/write-safety.md), with explicit production wording for evaluation-affecting changes. User confirmation must cover this exact plan and its affected environments.

## 5. Revalidate and verify

Immediately before writing, re-read the affected segment state and re-list the complete flag, segment (all types/statuses) and environment inventories. Compare identities and relevant state with the approved scan. To detect a new reference inside an existing flag, also re-read all flag-definition pages and authoritative RULE_BASED configurations unless a documented definition-level revision mechanism establishes that those exact configurations are unchanged; metadata update timestamps alone are not sufficient. Recheck applicable experiment state as well.

If revalidation cost is declined or current evidence cannot be obtained, STOP the write; never silently skip revalidation. Any changed inventory, definition or experiment state invalidates the gate: rebuild the impact report and obtain approval for the revised plan. Do not claim offset scans are atomic. Re-reading only previously found consumers cannot establish that no new consumer exists.

For a multi-step approved plan, retain inventory evidence only while scope, plan and dependency state remain unchanged; revalidate before dependent writes. After a failure, concurrent change or separate targeting edit, rerun the gate before resuming. Do not continue on an old approval with a changed payload.

Verify the actual mutation separately: complete STANDARD membership readback, saved RULE_BASED configuration, metadata readback or a confirmed deletion. Report partial completion honestly. A completed usage scan is not evidence that the write succeeded, and a successful write is not evidence of complete usage coverage.

Even a clean scan supports only "no configuration references found in project P at scan time". It does not establish account-wide absence, application-code absence or lack of live use.
