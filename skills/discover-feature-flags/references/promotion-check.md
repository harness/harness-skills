# Promotion Check Reference

Reference for discover-feature-flags **rollout-report** promotion analysis. Covers required inputs, comparability criteria, stalled detection, divergence reporting, and edge cases. Never derive environment order or infer treatment names from definitions or timestamps.

## Required Inputs

Collect all of the following before comparing any definitions. Without confirmed inputs, output neutral per-environment state differences only (no stalled/ahead/divergence classifications).

| Input | How to collect | Notes |
|-------|----------------|-------|
| Environment IDs | From Phase 3 environment list; show name + ID for user to select | Never infer order from `isProduction` or display position |
| Promotion sequence | User confirms ordered list, e.g. `dev-id → staging-id → prod-id` | At least two environments required |
| Intended target treatment per flag | Ask per flag or confirm for a group | Never infer; treatment names are user-defined and case-sensitive |
| Intended differences | User declares which (flag, env-pair) are expected to differ | Mark these before generating any alerts |

## Classification Order

For each adjacent confirmed pair: exclude ARCHIVED flags; require both confirmed order and target; check read completeness and required fields; record confirmed missing definitions; match any specific intended exception against known state; then handle killed definitions using the table below. Only non-killed, present definitions proceed to percentage comparability and stalled detection. Unknown state never becomes an intended exception or an `ok` result.

## Comparability Criteria

A definition pair (upstream env U, downstream env D) is **comparable** only when all hold for **both** definitions:

- `isKilled: false`
- `rules` array is empty
- No individual target memberships: `treatments[].keys` empty or absent; `treatments[].segments`, `treatments[].largeSegments`, `treatments[].ruleBasedSegments` all empty or absent
- `trafficAllocation` is 100
- `defaultRule` is well-formed: finite numeric bucket `size` values are in 0–100, unique treatment buckets sum to 100, and every referenced name exists in `treatments`. Duplicate treatment buckets are malformed; do not silently aggregate them
- The confirmed target treatment exists in both treatment sets; other treatment names and configurations match, so the same label is not hiding a different configuration. If treatment semantics differ, report not comparable rather than assuming equivalence
- Both definitions are present after complete inventory reads; required fields have known values, not unknown/malformed state. Treat omitted optional target arrays as empty only when that omission is established by the response schema
- Flag global status is ACTIVE

Check completeness first: unread state or unresolved required fields is **unknown**, never aligned or intended. A confirmed absent definition is **missing**, distinct from an unread definition. If another comparability criterion fails, report **not comparable** with the reason; do not classify as stalled or ahead. When the confirmed target is in both treatment sets but omitted from an otherwise valid bucket list, its configured default-rule share is zero.

## Stalled Detection

Apply only to comparable pairs with a confirmed sequence and intended target treatment T (user-supplied name).

| Upstream T% in defaultRule | Downstream T% in defaultRule | Classification |
|----------------------------|------------------------------|----------------|
| 100 | < 100 | **`stalled?`** — snapshot candidate |
| < 100 | > upstream | **`ahead`** — downstream is further along |
| Equal | Equal (either value) | **`ok`** — aligned |
| < 100 | < upstream | **`behind (no alert)`** — report configured values; no stalled classification |

"Potentially stalled" is a **snapshot observation**, not a confirmed duration or confirmation that promotion was attempted. Never compute or imply duration from `lastImpressionAt`, `updatedAt`, or any other timestamp.

## Killed and Missing Definitions

Report without implying live exposure or treatment received:

| Scenario | Promotion column |
|----------|-----------------|
| Upstream killed, downstream not | `divergence` — killed upstream / active downstream |
| Downstream killed, upstream not | `divergence` — active upstream / killed downstream |
| Both killed, same known fallback/configuration | `both killed` — report observed fallbacks; no claim that restored targeting is aligned |
| Both killed, different known fallback/configuration | `divergence` — report the configured fallback difference; do not classify as stalled |
| Both killed, fallback/configuration unresolved | `unknown` — cannot compare configured fallbacks |
| Definition confirmed missing in upstream | `missing` — upstream definition absent after complete inventory |
| Definition confirmed missing in downstream | `missing` — downstream definition absent after complete inventory |
| Partial page failure either side | `unknown` — incomplete coverage |

Show a killed definition's configured `defaultTreatment` from readback; distinguish that configured fallback from observed traffic or the user's intended target.

## Archived Flags

Flags with global `status: ARCHIVED`:
- Include in the rollout-report table as an `archived` row.
- Do **not** generate stalled, ahead, or divergence alerts.
- Archived flags serve `control` from SDKs; definition state is historical only.

## Intended Differences

Before generating alerts, verify that the complete observed state matches the user's **specific** intended difference for that flag/environment pair (for example, downstream held at 50%, not a blanket permission for any discrepancy).
1. Only an actual match to that confirmed exception is `intended ✓`; suppress its alert.
2. A different discrepancy still requires comparison; do not suppress it merely because some difference was expected.
3. Unknown or unread state stays unknown. If the actual states are identical, note "declared intended difference but definitions are identical" rather than treating the exception as evidence.

## Structural Comparison Only

Comparisons are between definition structures (allocation, defaultRule bucket sizes, isKilled). They do not represent actual traffic distribution, user exposure, or rollout effectiveness. Do not phrase results as "users are getting treatment X" based on definition state alone.

## History Caveat

Include in every promotion-check summary:

> **Snapshot only:** This reflects definition state at scan time. No history of when changes were applied is available. "Potentially stalled" means the snapshot shows a discrepancy; it does not confirm how long the discrepancy has existed or whether a promotion was attempted.

## Output Examples

### Rollout-Report Table with Promotion Column

```
| Flag    | staging  | prod *   | Promotion   | Notes                                      |
|---------|----------|----------|-------------|--------------------------------------------|
| flag-a  | on 100%  | on 75%   | stalled?    | on at 100 upstream, 75 downstream          |
| flag-b  | on 50%   | on 100%  | ahead       | prod ahead of staging                      |
| flag-c  | on 100%  | on 100%  | ok          | aligned                                    |
| flag-d  | killed→off | on 100% | divergence | staging killed, prod active                |
| flag-e  | missing  | on 100%  | missing     | confirmed absent staging definition        |
| flag-f  | on 100%  | on 80%   | intended ✓  | user declared prod intentionally at 80%    |
| flag-g  | archived | archived | archived    | globally archived; excluded from alerts    |
| flag-h  | targeted | on 100%  | not comparable | has rules; show per-environment state   |
```

(* = production environment)

Snapshot only: [history caveat]

### Summary Block

```
Promotion summary (staging → prod):
  Aligned (ok):           1
  Potentially stalled:    1  ← flag-a
  Ahead downstream:       1
  Divergence:             1
  Missing definition:    1
  Both killed:           0
  Behind (no alert):     0
  Unknown:               0
  Intended differences:   1
  Not comparable:         1
  Archived (excluded):    1
```

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Order-only or target-only input | Neutral differences only until both are confirmed for the flag and pair |
| Three-env chain | Evaluate each consecutive pair only with confirmed order and target; an unconfirmed hop stays neutral, never inferred from the other hops |
| Multiple flags, same intended treatment | Confirm once for the group; note per-flag exceptions |
| Incomparable: rules present | `not comparable (has rules)` — show per-env state only |
| Incomparable: targets present | `not comparable (has targets)` |
| defaultRule sums ≠ 100 | `not comparable (malformed defaultRule)` |
| Treatment name not in `treatments` | `not comparable (unresolved treatment)` |
| env in lookup but not in user's sequence | Include in table; no Promotion column entry |
| isProduction = true but not in confirmed sequence | Show in table; exclude from promotion analysis |
