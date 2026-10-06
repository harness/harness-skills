# Standard segment membership

Use these flows only for STANDARD segments. For LARGE bulk operations or RULE_BASED rules/exclusions, follow the type-specific workflow in [manage-segments](../SKILL.md). These key actions require MCP in the audited tool versions; discover installed support and never invent a CLI action.

## Add keys

1. Parse the approved list/file (extract the key column for CSV), trim whitespace, deduplicate and count. Show count, segment, environment and redacted samples; do not expose raw keys by default.
2. Plan batches of at most 10,000 keys. Addition is append-only, so multiple sequential batches are allowed; confirm the batch plan and report partial completion on failure.
3. Apply the [production-aware confirmation gate](../../../references/fme/write-safety.md). STOP and wait for approval before writing.
4. Execute **Add keys** per environment with `replace` omitted/false. Include a meaningful supported audit comment; never assume a comment on an unsupported operation is recorded.
5. Fully paginate membership and verify every requested key is present. Report exact counts only from a complete inventory; otherwise report verification incomplete, not success.

## Remove keys

1. Parse and deduplicate as above. Show the removal count, segment, environment and redacted samples.
2. Run the [usage check](../SKILL.md#usage-check). Warn that removed keys stop matching every flag rule/treatment membership that references this segment in the affected environment.
3. Apply the production-aware gate. STOP and wait for confirmation; batches must contain 1–10,000 keys. Report partial completion if a later batch fails.
4. Execute **Remove keys** with the confirmed keys and supported audit comment.
5. Fully paginate membership and verify every requested key is absent. A first-page miss does not prove removal; report unverified if pagination cannot finish.

## Replace all keys

1. Parse the new set. Fully paginate **List keys** so the current set/count is exact, not a first-page estimate.
2. **Stop if the replacement exceeds 10,000 keys.** Never chunk `replace=true` calls: each later chunk erases the earlier chunk. Do not silently substitute a non-atomic remove-then-add sequence; ask for a supported bulk-administration workflow.
3. Show current/new counts and dropped-key count with redacted samples. Run the [usage check](../SKILL.md#usage-check) and explicitly warn about the destructive overwrite and production impact.
4. STOP and obtain explicit replacement approval. Empty replacement requires a separate explicit request to clear the segment and confirmation naming the segment/environment.
5. Execute **Add keys** once per approved environment with `params.replace: true`, `body.keys` and supported audit comment. `replace` is not a body field.
6. Fully paginate **List keys** and compare the complete returned set to the approved set, not just its count. Any missing or extra key is a mismatch; report incomplete verification rather than success.
