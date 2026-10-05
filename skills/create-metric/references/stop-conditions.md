# Stop conditions — option tables and rationale

Referenced from SKILL.md Phases 2, 4, 6, 7. Each is a point where a plausible-sounding guess is available but wrong often enough that the skill requires presenting real options and waiting for a pick instead.

## Phase 2: vague request against existing metrics

If the request is vague (e.g. "track checkouts" with no aggregation
specified), don't silently pick one existing metric or attribute
combination yourself. Turn the Step 1 search result into a concrete option
table and let the user pick - one decision, one turn:

| Option | Shape |
|--------|-------|
| `<existing metric name>` | `<aggregation>` on `<event>` (reuse this) |
| `<existing metric name>` | `<aggregation>` on `<event>` (reuse this) |
| `new` | Define a new metric with a different shape |

A search result is not itself a decision — show the user what was found instead of picking the most relevant hit yourself.

## Phase 4: event not in the resolved list, or several near-matches

If the event the user wants to measure isn't in the list, don't invent an ID and don't silently substitute the closest-looking real event either — both are guessing on the user's behalf. The same applies when the list comes back with several plausible matches and none is exact: a substring search on a word like `purchase` routinely returns a dozen variants, and picking the shortest or cleanest-looking one is still a guess. Present the real event list as options:

| Option | Event |
|--------|-------|
| `<real event 1>` | Use this event instead |
| `<real event 2>` | Use this event instead |
| `not_listed` | The event exists but hasn't fired in the last 30 days (confirm exact spelling) |
| `instrument` | Doesn't exist yet — hand off to `/instrument-metric` first |

If they pick `instrument`, creating the metric now is *allowed* (the backend does not validate `eventTypeId` existence by design) but the metric will silently never compute until the event flows — make sure the user understands that tradeoff if they want to proceed anyway.

## Phase 6: missing or invalid owner

"No owner specified" in the request is not permission to pick one yourself — it means this decision hasn't been made yet. Ask for a `USER` email or `GROUP` identifier before drafting Phase 8, the same way a missing event or aggregation choice would stop you. Filling in a plausible-looking owner (your own account, an org admin, the first user in a list) to keep moving is guessing on the user's behalf. Prefer a `USER` owner by email when unsure — a `GROUP` owner's `identifier` must be the group's **identifier** (the `id` field), not its display name.

The same rule applies if an owner turns out to be invalid rather than missing (e.g. a 400 on create) — stop and ask for a real replacement, don't silently substitute one.

## Phase 7: "before"/trigger relationship vs a plain filter event

A base event can be scoped by another event in two conceptually different
ways:

| Concept | Meaning | Field |
|---------|---------|-------|
| Filter event (`HAS_DONE`) | Only count units that did this event at all | `filterEventType` with `filterAggregation: "RATE"` |
| Trigger event (`HAS_DONE_BEFORE`) | Only count units that did this event *before* the base event | `triggerEventType: {eventTypeId}` |

If the request is ambiguous between the two, ask which the user means
before drafting the payload - using `filterEventType` when they meant
ordering (or vice versa) silently changes which units get counted.
