# FME Write Safety Protocol

Every FME skill that creates, changes, kills, archives or deletes anything follows these steps, in order. Tool names are in [tool-map.md](tool-map.md); semantics are in [concepts.md](concepts.md).

## 1. Resolve scope

Follow [scope-establishment.md](../scope-establishment.md). Confirm organization and project identifiers before the first write. Never use deprecated workspace identifiers.

## 2. Read current state

Read everything the write will touch (see [tool-map.md](tool-map.md) for operations):
- **Environments:** resolve each name to an ID and note `isProduction`.
- **Definitions:** for each target environment, read the current treatments, rules, default rule, allocation and killed state.
- **Dependents:** check experiments, dependent flags, and segments in use per the skill's protocol.

Never guess treatment names, environment IDs, or current percentages.

## Experiment check

Before targeting changes or archive, **list experiments** for the flag filtering to parent type FEATURE_FLAG, parent name, and status ACTIVE and PAUSED. See [tool-map.md](tool-map.md#fme_experiment).

Policy:
- **ACTIVE**: gate per skill (targeting: require explicit acknowledgement; archive: blocked).
- **PAUSED**: warn user: "Experiment `<name>` is PAUSED on this flag. Targeting changes may invalidate results. Proceed?" Require explicit acknowledgement; user may proceed.
- **COMPLETED**: ignore (completed experiments don't block changes).

## 3. Present the plan, then STOP (after experiment check if applicable)

Show a before → after for each environment, in plain language:

```
Plan: <operation> <resource> — <reason>
1. <env name> (<Production | Non-production>)
   Before: <current behavior, e.g. "100% off; not killed">
   After:  <new behavior, e.g. "10% on / 90% off for users in segment beta">
Not changed: <other environments / fields>
```

Then stop and wait. The wording depends on the risk:

| Change | Ask |
|---|---|
| Non-production create/update | "Apply this?" |
| Any **production** write | "This changes live production traffic in `<env>`. Apply?" |
| **Kill** | "Everyone in `<env>` will get `<defaultTreatment>`. Kill?" |
| **Archive** | "This archives `<flag>` in **all** environments. SDKs will return `control`. Archive?" |
| **Delete** | "This permanently deletes `<resource>`. This can't be undone. Delete?" |

Rules:
- Only an explicit yes to *this* plan counts. Silence, "looks good" about a different step, or an earlier approval doesn't carry over.
- One confirmation can cover several environments only if every environment is listed in the plan. Put production environments last, and show them separately.
- If the user changes the plan, show the revised plan and ask again.
- A user decline is final.

## 4. Execute

- Run environments one at a time, non-production first. Stop at the first failure and report what succeeded and what didn't.
- Add an audit comment (and title where supported) on every write. Use the format `"<skill>: <what> — <why>"`, e.g. `"update-flag-targeting: ramp new-checkout to 25% in staging — FME-123"`. Exception: deletes take no body, so no comment is sent; record the reason in the plan/summary instead.
- **Errors:**
  - 400: fix the field the message names and retry once (see [schema-validation-loop.md](../schema-validation-loop.md)).
  - 404: re-check the identifiers. Never create something to fill the gap.
  - 409 or a governance/approval response: report it as-is and stop. Never retry around it, never try another route, and never delete to work around a blocked archive.

## 5. Verify and restate

Re-read each changed resource, then describe the **live** state in plain language. For example: "staging now serves `on` to 25% of users in segment beta and `off` to everyone else. Not killed." If the live state doesn't match the plan, say so and run no further writes.

End with the operation summary from [operation-summary.md](../../templates/operation-summary.md), plus a Harness UI link when available.
