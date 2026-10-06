# 409 retry protocol, troubleshooting, anti-patterns

Referenced from SKILL.md Step 8.

## Full 409 retry protocol

A 409 means the payload you just got confirmed collided with an existing
metric. Before drafting a revised payload:

1. Name the specific conflicting metric (id + name) that this attempt
   collided with - the 409 response or Step 1's list tells you which.
2. If the fix changes what the metric actually measures (different
   `aggregation` or `baseEventTypes` than what the user asked
   for - e.g. pivoting from `RATE` to `COUNT`, or from `checkout_completed`
   to a different event to dodge the conflict), that is a new decision,
   not a retry of the old one. Show the user the specific existing metric
   it collided with and the revised draft, and wait for confirmation again
   before calling `harness_create`.
3. Never loop through `harness_create` attempts autonomously and report
   the conflicts afterwards - each conflict is a checkpoint, not a line in
   the final summary. Approving one retry is not permission for the next;
   every attempt is its own decision, however many 409s precede it.
4. If a revised draft would reuse a `baseEventTypes`/`filterEventType`
   entry or owner already found invalid or nonexistent in this conversation
   (Step 3, Step 5) - including one copied from the conflicting metric's
   own definition - re-run the resolving list call first rather than
   justifying the reuse.

## Anti-patterns (do not do this)

| Anti-pattern | Correct behavior |
|--------------|-------------------|
| Search existing metrics/events, then silently pick one yourself | Turn search results into a concrete option list/table and let the user choose (Step 1, Step 3) |
| Substitute a different real event for a missing one without asking | Present the real event list and let the user pick (Step 3) |
| Fill in a plausible owner because "no owner specified" was in the request | Treat a missing owner as a stop condition - ask for a `USER` email or `GROUP` identifier (Step 5) |
| Substitute a plain `filterEventType` when the user asked for a before/trigger ordering | Use `triggerEventType` (HAS_DONE_BEFORE) - it drops the ordering otherwise (Step 6) |
| Retry `harness_create` after a 409 without a new confirmation | Every revised draft goes back through Step 7, on every attempt (Step 8) |
| Change `aggregation`/`baseEventTypes` to dodge a 409 and only mention it in a final summary | Name the specific conflicting metric and show the revised draft *before* retrying (Step 8) |
| Draft a payload, then send a different one to `harness_create` | The confirmed draft and the request body must match field-for-field |
| Report a create as successful without an independent `harness_get` on the returned id | Always run Step 9 before telling the user it's done |

## Troubleshooting

### 409 on create
Either a duplicate name or a duplicate on the same attribute combination
under a different name - re-run Step 1's list with broader filters, name
the specific conflicting metric to the user, and get confirmation on the
revised draft before retrying. Don't treat this as a loop to resolve
autonomously - see the retry protocol above.

### 400 "Owners cannot be empty"
Owners are required until the deprecation ships. Ask the user for a `USER`
email or a `GROUP` name that matches an actual Split Team.

### 400 on `name` with no field named in the message
Almost certainly the `^[A-Za-z][-_A-Za-z0-9]*$` pattern (no spaces/leading
digit). Suggest a valid `name` and confirm before retrying.

### Metric created but never computes
Check `fme_event_type` for the metric's `baseEventTypes[].eventTypeId` -
existence isn't validated at create time, so a typo or not-yet-instrumented
event silently produces a metric with no data. Route to
`/instrument-metric`.

### Need to remove a metric
`fme_metric.delete` is a **hard delete**, not an archive - there is no
undo. Confirm explicitly before calling it, and check the metric isn't
still referenced by an experiment's `keyMetrics`/`supportingMetrics` first.
