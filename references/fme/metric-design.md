# FME Metric Design

Guidance for creating FME metrics that measure what matters: what makes a metric reliable, how to map intent to configuration, naming conventions, auto-created metrics, and how to suggest metrics from application code. Shared by `/create-metric`, `/choose-metric`, and `/instrument-metric`.

## What makes a good metric

| Criterion | Check | Red flag |
|-----------|-------|----------|
| Tied to a decision | Completes "if this works, X will increase/decrease" | Metric is topically related but wouldn't move from the change |
| Right unit | Flag's traffic type; same key as `getTreatment` uses | Different traffic type; key mismatch breaks attribution |
| Fires where the outcome happens | Server-confirmed success, not the click that starts the flow | Fires on optimistic UI update before real confirmation |
| Sensitive | Moves within the experiment's run; enough units for minimum sample size | Long-horizon outcomes like 90-day retention make poor primaries |
| Low noise | Cap unbounded TOTAL/AVERAGE values (revenue, durations) | Heavy users dominate; RATE resists this better than COUNT |
| Clear direction | `isPositive` unambiguous — no "it depends" | If direction depends on context, it's a supporting signal, not primary |
| Hard to game | Pair primary with counter-metric (conversion ↔ order value) | A metric that can be gamed without hurting the real outcome |
| Healthy and unique | Event type and intended traffic type visible in last 30 days; not a duplicate shape | 404 = absent in this scope/window or idle; visibility alone doesn't prove current delivery |

Event discovery is a prerequisite check, not evidence of sufficient sample size or statistical power. Confirm recent activity and the experiment's data-quality checks before treating a metric as decision-ready.

## Intent to configuration

Start with three plain questions:
- "How many times?" → COUNT
- "Did they at least once?" → RATE
- "How much / how long?" → TOTAL (sum per unit) or AVERAGE (typical size per event)

For `TOTAL`/`AVERAGE`, also agree the measurement units and whether the source is the numeric event value or a named numeric `propertyForValue`. Carry required property names and filters into the instrumentation handoff.

Then the configuration table:

| Intent | Example | aggregation | format | isPositive | Notes |
|--------|---------|-------------|--------|------------|-------|
| Conversion rate | Did user sign up? | RATE | PERCENTAGE | true | Share of units with ≥1 event |
| Events per user | Searches per user | COUNT | NUMBER | true | Event count per unit |
| Revenue per user | Revenue per user | TOTAL | DOLLAR | true | Sum per unit; cap recommended |
| Average order value | Typical purchase size | AVERAGE | DOLLAR | true | Mean event value per unit; cap; pair with conversion |
| Latency / load time | Page load time | AVERAGE | MILLISECONDS or SECONDS | false | Match value units sent; cap; check auto-created first |
| Error rate — % of users | Share of users who hit an error | RATE | PERCENTAGE | false | |
| Errors per user | Error events per user | COUNT | NUMBER | false | |
| Ratio of two events | Checkout / cart view | COUNT + filter event COUNT | NUMBER | true | Average of per-unit ratios |
| Conversion among filtered users | Purchased among those who added to cart | RATE + filter event RATE | PERCENTAGE | true | HAS_DONE filter (when order doesn't matter) |
| Conversion among users who did prior step | Completed step 2 among those who did step 1 first | RATE + trigger event | PERCENTAGE | true | HAS_DONE_BEFORE (when order matters) |

**Computation semantics:**
- RATE = share of units with ≥1 event
- COUNT = events per unit
- TOTAL = sum of event values per unit
- AVERAGE = mean event value per unit, then averaged across units
- Attribution: an event counts toward a flag's results only if its key (and traffic type) received an impression for that flag, and only when the event falls inside the experiment's time window. So `track()` must use the same key that `getTreatment` uses.

## Naming, description and tags

- Follow naming conventions visible in existing metric inventory: case style (camelCase, snake_case, kebab-case), prefixes, unit suffixes like `_ms`.
- `description` states what is counted, where the event fires, and which direction is good (e.g. "Share of users who completed checkout after payment confirmation; higher is better").
- Reuse existing tags rather than inventing new ones — check the existing metric list first.

## Auto-created metrics

When the FME RUM agent (browser) sends events, FME automatically creates metrics whose names end in ` - Split Agents` for a configurable `split.rum.*`-prefixed event family (e.g. `split.rum.page.load.time`, `split.rum.error` — prefix is configurable per the browser RUM agent docs, so don't treat these as fixed literals). Mobile/server equivalents aren't documented here — don't invent event-type IDs for them; resolve the real ones via **List event types** / **Get event type** against the actual project before assuming a name.

Check existing RUM-derived metrics (name ending ` - Split Agents`) before creating a duplicate latency or error metric. Inspect initialization, identity, and any consent gates, then use **List metrics** / **Get event type** to check the actual definition and traffic type. An installed dependency isn't evidence of delivery; the project's 30-day inventory is historical, cross-environment evidence, not proof of current flow.

These metrics are ready-made engineering guardrail candidates. Users can't toggle this auto-creation. See the [browser RUM configuration](https://developer.harness.io/docs/feature-management-experimentation/sdks-and-infrastructure/client-side-agents/browser-rum-agent/#configuration) for event-prefix settings.

Events can also arrive from existing integrations, not only `track()` calls. No local `track()` does not prove an event is missing. Creating an FME metric does not itself establish URL or CSS-selector tracking: resolve a real FME event or instrument and verify its producer first.

## Suggest metrics from code

When the user doesn't know what to measure or asks for suggestions, run this procedure in the **application** repo (not the skills repo):

1. **Find outcome signals:** FME `track()` calls (see [sdk-patterns.md](sdk-patterns.md#tracking-calls-track)), other analytics calls (see [sdk-patterns.md](sdk-patterns.md#other-analytics-calls)), and untracked outcome points (payment/order confirmation, signup/onboarding completion, error handlers, request timers).

2. **If a flag is under test,** read the code behind its treatments: which outcome would the change move?

3. **Cross-reference with event types and existing metrics** (**List event types** / **List metrics**) into a coverage table:

| Outcome found | Local FME call | FME event visible (30 days) | Metric exists | Suggestion |
|---------------|----------------|----------------------------|---------------|------------|
| yes | yes | yes | no | Candidate for `/create-metric`; confirm traffic type and definition |
| yes | yes | no | either | Check scope, deployment, recent activity, and SDK config before changing code |
| either | no | yes | yes | Investigate RUM/integration/another service as producer; consider reusing metric, not duplicate tracking |
| yes | no | yes | no | Confirm the existing producer matches this outcome; then create a metric |
| yes | no | no | no | Check other analytics/integrations; instrument if needed, then create |
| either | either | unknown | either | Lookup unavailable or incomplete; mark unverified, don't infer absent |

Record the actual outcome/event name and producer evidence alongside this table. Other analytics calls are placement clues, not proof that those events reach FME. Use exact event lookup and check `trafficTypes`; a filtered or partial list can't establish absence.

4. **Rank by the good-metric checklist** (table above). Propose 3–5 candidates with intent-table config. **Create nothing until the user picks** — show the coverage table and let them choose one metric per pass.
