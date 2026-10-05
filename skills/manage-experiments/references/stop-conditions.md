# Stop conditions - option tables and rationale

Referenced from SKILL.md. Each is a point where a plausible-sounding guess is
available but wrong often enough that presenting real options (or pointing to
the owning skill) and waiting for a pick is required, instead of improvising.

## Step 2: baseline vs. variant is unclear

Never invent treatment names ("control", "treatment_a") that don't exist on the
flag - `baselineTreatment`/`comparisonTreatments` must match real
`treatments[].name` values from the flag's definition in the chosen environment.
If it's unclear which real treatment is the baseline:

| Option | Treatment | Notes |
|--------|-----------|-------|
| `<treatment 1>` | Use as baseline | Matches the definition's `baselineTreatment` |
| `<treatment 2>` | Use as the comparison variant | |
| `<treatment 3>` | Use as a second comparison variant | Only if the user wants a multi-variant test |

Fewer than 2 treatments → stop and route to
[update-flag-targeting](../../update-flag-targeting/SKILL.md) to add treatments
first, then return here.

## Step 3: hypothesis is missing or non-causal

A hypothesis without causal reasoning isn't usable for metric or treatment
decisions. Ask for the missing half:

| Missing piece | Ask for |
|----------------|---------|
| No metric named | "If this succeeds, what should move - which metric, up or down?" |
| No causal reasoning | "Why would this change move that metric?" (the "because" clause) |
| No change/variant named | "What's actually different in the variant vs. the baseline?" |
