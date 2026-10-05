# 409 retry protocol, troubleshooting, anti-patterns

Referenced from SKILL.md Phase 9.

## Full 409 retry protocol

A 409 means the payload you just got confirmed collided with an existing metric. Before drafting a revised payload:

1. Name the specific conflicting metric (id + name) that this attempt collided with — the 409 response or Phase 2's list tells you which.
2. If the fix changes what the metric actually measures (different `aggregation` or `baseEventTypes` than what the user asked for — e.g. pivoting from `RATE` to `COUNT`, or from `checkout_completed` to a different event to dodge the conflict), that is a new decision, not a retry of the old one. Show the user the specific existing metric it collided with and the revised draft, and wait for confirmation again before calling **Create metric**.
3. Never loop through create attempts autonomously and report the conflicts afterwards — each conflict is a checkpoint, not a line in the final summary. Approving one retry is not permission for the next; every attempt is its own decision, however many 409s precede it.
4. If a revised draft would reuse a `baseEventTypes` / `filterEventType` entry or owner already found invalid or nonexistent in this conversation (Phase 4, Phase 6) — including one copied from the conflicting metric's own definition — re-run the resolving list call first rather than justifying the reuse.

## Anti-patterns (do not do this)

| Anti-pattern | Correct behavior |
|--------------|-------------------|
| Search existing metrics/events, then silently pick one yourself | Turn search results into a concrete option list/table and let the user choose ([stop-conditions.md](stop-conditions.md)) |
| Substitute a different real event for a missing one without asking | Present the real event list and let the user pick (Phase 4) |
| Fill in a plausible owner because "no owner specified" was in the request | Treat a missing owner as a stop condition — ask for a `USER` email or `GROUP` identifier (Phase 6) |
| Substitute a plain `filterEventType` when the user asked for a before/trigger ordering | Use `triggerEventType` (HAS_DONE_BEFORE) — it drops the ordering otherwise (Phase 7) |
| Retry create after a 409 without a new confirmation | Every revised draft goes back through Phase 8, on every attempt |
| Change `aggregation` / `baseEventTypes` to dodge a 409 and only mention it in a final summary | Name the specific conflicting metric and show the revised draft *before* retrying |
| Draft a payload, then send a different one to create | The confirmed draft and the request body must match field-for-field |
| Report a create as successful without an independent get on the returned id | Always run Phase 10 before telling the user it's done |

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| 409 on create | Duplicate name or duplicate definition under a different name | Re-run Phase 2's list with broader filters, name the specific conflicting metric, get confirmation on the revised draft before retrying — see retry protocol above |
| 400 "Owners cannot be empty" | Owners are required until the deprecation ships | Ask for a `USER` email or `GROUP` identifier (not display name) |
| 400 on `name` with no field named | `^[A-Za-z][-_A-Za-z0-9]*$` pattern violation (no spaces/leading digit) | Suggest a valid `name` and confirm before retrying |
| Metric created but never computes | `baseEventTypes[].eventTypeId` is a typo or not-yet-instrumented event (existence isn't validated at create time) | Check event type via **Get event type**; route to `/instrument-metric` |
| Need to remove a metric | Hard delete, no undo | Check metric usage first (see [tool-map.md](../../../references/fme/tool-map.md#reverse-lookup-scans)); confirm explicitly before **Delete metric** |
