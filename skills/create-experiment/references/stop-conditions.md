# Stop conditions - option tables and rationale

Referenced from SKILL.md Steps 2, 3, and 4. Each is a point where a
plausible-sounding guess is available but wrong often enough that the skill
requires presenting real options (or pointing to the skill that owns the
decision) and waiting for a pick, instead of improvising.

## Step 2: baseline vs. variant is unclear, or the flag has too few treatments

Never invent treatment names ("control", "treatment_a") that don't exist on
the flag - `baselineTreatment`/`comparisonTreatments` must match real
`treatments[].name` values from `fme_feature_flag_definition` in the chosen
environment. If it's unclear which real treatment is the baseline:

| Option | Treatment | Notes |
|--------|-----------|-------|
| `<treatment 1>` | Use as baseline | Matches the definition's `baselineTreatment` |
| `<treatment 2>` | Use as the comparison variant | |
| `<treatment 3>` | Use as a second comparison variant | Only if the user wants a multi-variant test |

If the definition has only one treatment, there's nothing to compare
against - say so and stop. A flag with two treatments such as `on`/`off` is
a valid experiment. Adding a
treatment is a flag-definition change, not something this skill performs;
point to whichever skill/flow owns flag/definition edits and re-run Step 2
once it exists.

## Step 3: hypothesis is missing or non-causal

A hypothesis that states an outcome without a reason isn't a hypothesis this
skill can use to drive metric or treatment decisions - "conversion will go
up" doesn't say why, so it can't be checked against the actual change being
tested. Ask for the missing half rather than filling in a plausible-sounding
mechanism yourself:

| Missing piece | Ask for |
|----------------|---------|
| No metric named | "If this succeeds, what should move - which metric, up or down?" |
| No causal reasoning | "Why would this change move that metric?" (the "because" clause) |
| No change/variant named | "What's actually different in the variant vs. the baseline?" |

Don't infer the hypothesis from the flag's name or description - a flag
named `new-checkout-flow` says nothing about which metric it's expected to
move or by what mechanism.

## Step 4: primary vs. secondary metric assignment

This is `/choose-metric`'s decision, not this skill's. Don't rank candidate
metrics into primary/guardrail/counter/supporting here even when the
inventory check (Step 4) surfaces a single obvious-looking candidate - state
that healthy candidates exist and hand off to `/choose-metric` for the actual
assignment, the same way `/create-metric` hands off attachment decisions to
`/choose-metric` rather than deciding them itself.
