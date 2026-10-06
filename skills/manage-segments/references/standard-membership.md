# Standard segment membership

Use these flows only for STANDARD segments. For metadata and RULE_BASED editor changes, follow [manage-segments](../SKILL.md). Use CLI or MCP with the same scope, approval and verification requirements; discover exact CLI action syntax through command help.

## Add keys

1. Parse the approved list/file (extract the key column for CSV), trim whitespace, deduplicate and count. Show count, segment, environment and redacted samples; do not expose raw keys by default.
2. Plan batches of at most 10,000 keys. Addition is append-only, so multiple sequential batches are allowed; confirm the batch plan and report partial completion on failure.
3. Complete the mandatory [usage gate](usage-check.md), including every project flag and environment plus indirect dependencies. Present affected consumers and apply the [production-aware confirmation gate](../../../references/fme/write-safety.md). Incomplete coverage blocks the write. STOP and wait for approval before writing.
4. Execute **Add keys** per environment with `replace` omitted/false. Include a meaningful supported audit comment; never assume a comment on an unsupported operation is recorded.
5. Fully paginate membership and verify every requested key is present. Report exact counts only from a complete inventory; otherwise report verification incomplete, not success.

## Remove keys

1. Parse and deduplicate as above. Show the removal count, segment, environment and redacted samples.
2. Complete the mandatory [usage gate](usage-check.md); incomplete coverage blocks the write. Explain how removing keys can change direct/indirect consumers, including negated or exclusion references. Do not claim keys necessarily stop matching an entire rule: other conditions and membership routes can still apply.
3. Apply the production-aware gate. STOP and wait for confirmation; batches must contain 1–10,000 keys. Report partial completion if a later batch fails.
4. Execute **Remove keys** with the confirmed keys and supported audit comment.
5. Fully paginate membership and verify every requested key is absent. A first-page miss does not prove removal; report unverified if pagination cannot finish.

## Replace all keys

1. Parse the new set. Fully paginate **List keys** so the current set/count is exact, not a first-page estimate.
2. **Stop if the replacement exceeds 10,000 keys.** Never chunk `replace=true` calls: each later chunk erases the earlier chunk. Do not silently substitute a non-atomic remove-then-add sequence; stop and report the 10,000-key replacement limit.
3. Show current/new counts and dropped-key count with redacted samples. Complete the mandatory [usage gate](usage-check.md); incomplete coverage blocks the write. Explain the destructive overwrite and direct/indirect production impact.
4. STOP and obtain explicit replacement approval. Empty replacement requires a separate explicit request to clear the segment and confirmation naming the segment/environment.
5. Execute **Add keys** once per approved environment with `params.replace: true`, `body.keys` and supported audit comment. `replace` is not a body field.
6. Fully paginate **List keys** and compare the complete returned set to the approved set, not just its count. Any missing or extra key is a mismatch; report incomplete verification rather than success.
