# Stop conditions — option tables and rationale

Supporting decisions for the [create-metric workflow](../SKILL.md#instructions), not a separate numbered sequence. Present real options and wait for the user's choice at each applicable stop.

## Ambiguous metric intent

If the request is vague (e.g. "track checkouts" with no aggregation
specified), don't silently pick one existing metric or attribute
combination yourself. Turn the existing-metric search result into a concrete option
table and let the user pick - one decision, one turn:

| Option | Shape |
|--------|-------|
| `<existing metric name>` | `<aggregation>` on `<event>` (reuse this) |
| `<existing metric name>` | `<aggregation>` on `<event>` (reuse this) |
| `new` | Define a new metric with a different shape |

A search result is not itself a decision — show the user what was found instead of picking the most relevant hit yourself.

## Missing or ambiguous event

If the event the user wants to measure isn't in the list, don't invent an ID and don't silently substitute the closest-looking real event either — both are guessing on the user's behalf. The same applies when the list comes back with several plausible matches and none is exact: a substring search on a word like `purchase` routinely returns a dozen variants, and picking the shortest or cleanest-looking one is still a guess. Present the real event list as options:

| Option | Event |
|--------|-------|
| `<real event 1>` | Use this event instead |
| `<real event 2>` | Use this event instead |
| `not_listed` | The event exists but hasn't fired in the last 30 days — not the same as never instrumented; confirm exact spelling and recent activity, don't assume it's missing from a near-match guess |
| `instrument` | Doesn't exist yet |

**Default:** check exact spelling, scope, traffic type, pagination and recent activity before inferring absence. If instrumentation or investigation is needed, first settle the metric's aggregation, units, numeric-value versus property source and required filters/properties. Hand that contract to `/instrument-metric`, then resume creation with the agreed event and separate code-test, historical inventory and live-delivery evidence. An idle event alone does not justify new tracking. Don't create against an unverified event by default.

**Explicit exception:** if the user explicitly wants to create the metric now against an event that will be instrumented later, require the *exact* event name string from the user (not a guess), read it back verbatim for confirmation, and warn clearly that the metric will silently never compute until that exact event starts flowing — the backend doesn't validate `eventTypeId` existence by design, so this won't surface as an error later.

## Missing or invalid owner

"No owner specified" in the request is not permission to pick one yourself — it means this decision hasn't been made yet. Ask for a `USER` email or `GROUP` identifier before drafting the payload, the same way a missing event or aggregation choice would stop you. Filling in a plausible-looking owner (your own account, an org admin, the first user in a list) to keep moving is guessing on the user's behalf. Prefer a `USER` owner by email when unsure — a `GROUP` owner's `identifier` must be the group's **identifier** (the `id` field), not its display name.

The same rule applies if an owner turns out to be invalid rather than missing (e.g. a 400 on create) — stop and ask for a real replacement, don't silently substitute one.

## Filter versus ordered trigger

A base event can be scoped by another event in two conceptually different
ways:

| Concept | Meaning | Field |
|---------|---------|-------|
| Filter event (`HAS_DONE`) | Only count units that did this event at all | `filterEventType` with `filterAggregation: "RATE"` |
| Trigger event (`HAS_DONE_BEFORE`) | Only count units that did this event *before* the base event | `triggerEventType: {eventTypeId}` |

If the request is ambiguous between the two, ask which the user means
before drafting the payload - using `filterEventType` when they meant
ordering (or vice versa) silently changes which units get counted.
