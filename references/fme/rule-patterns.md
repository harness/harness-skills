# Rule Pattern Search Reference

Reference for discover-feature-flags **pattern-search** mode. Covers predicate types, structural matching, segment resolution, coverage output, and edge cases. Do not substitute a string grep on raw JSON.

## Clarification Protocol

Before fetching any definitions, confirm with the user:

1. **Predicate type(s)** — one or more of:
   - Attribute name (case-sensitive; exact by default, substring only if explicitly requested)
   - Matcher type (exact string, e.g. `IN_LIST_STRING`, `BETWEEN_NUMBER`, `IN_SPLIT`)
   - Literal value (typed: string list member, number, boolean, date epoch-ms, or between-range bounds): exact and case-sensitive by default, with no type coercion or regex interpretation. `ent.*` means that literal string. Substring matching requires an explicit request; numbers match stored operands/bounds, not every range containing the number, unless range containment is explicitly requested.
   - Segment reference (segment name + segment type: STANDARD / LARGE / RULE_BASED)
   - Flag dependency (flag name, and optionally a required treatment)

2. **Conjunction scope** when the user gives multiple predicates — confirm which applies:
   - *Within-matcher* (default for attribute + value pairs): both predicates must be in the **same matcher object**.
   - *Within-rule*: predicates must appear in the same rule's `condition.matchers[]`, but not necessarily the same matcher object. State this explicitly.
   - *Definition-wide*: predicates may appear in different rules. State this explicitly; never apply silently.

3. **Flag scope** — ACTIVE only (default), ARCHIVED only, or both. Collect explicitly; do not assume.

Cross-matcher matches on `(attribute, value)` pairs produce false positives. If the user's intent is ambiguous, confirm before proceeding.

## Predicate Field Locations

| Predicate | Fields to inspect | Notes |
|-----------|-------------------|-------|
| Attribute name | `rules[].condition.matchers[].attribute` | Not in `description` or `configurations` |
| Matcher type | `rules[].condition.matchers[].type` | Known types listed below; unknown type → unparsed |
| String value | `rules[].condition.matchers[].strings[]` | For `IN_LIST_STRING` |
| Number value | `rules[].condition.matchers[].number` | For `GREATER_THAN_OR_EQUAL_NUMBER`, `LESS_THAN_OR_EQUAL_NUMBER` |
| Between range | `rules[].condition.matchers[].between.from`, `.to` | For `BETWEEN_NUMBER` |
| Boolean value | `rules[].condition.matchers[].bool` | For `BOOLEAN` |
| Date value | `rules[].condition.matchers[].date` | Epoch-ms; for `ON_DATE` |
| Flag dependency | `rules[].condition.matchers[].depends.splitName`, `.depends.treatment` | For `IN_SPLIT` |
| Segment (in rule) | Read the actual field name from the returned matcher object | Do not fabricate segment matcher field names; if shape is unrecognized, mark unparsed |
| Segment (in treatment) | `treatments[].segments[]`, `treatments[].largeSegments[]`, `treatments[].ruleBasedSegments[]` | Type must match STANDARD / LARGE / RULE_BASED respectively |

**Established field layouts:** the table covers `IN_LIST_STRING`, `GREATER_THAN_OR_EQUAL_NUMBER`, `LESS_THAN_OR_EQUAL_NUMBER`, `BETWEEN_NUMBER`, `BOOLEAN`, `ON_DATE` and `IN_SPLIT`. For another type, including a segment matcher, establish its discriminator, operand shape and segment-type mapping from the operation schema or authoritative current project configuration before matching it. A similar-looking string alone does not establish a reference. A type or layout that remains unfamiliar is unparsed.

## Structural Matching per Definition

For each flag and each environment definition (all pages fetched):

1. **Archived flag (global `status: ARCHIVED`):** if included by the requested status filter, scan normally and annotate matches `inactive (archived)`; no live-exposure claim.
2. **`isKilled: true`:** scan rules normally; annotate any matches `inactive (killed)` — rules exist but are not evaluated for live traffic.
3. Walk `rules[]` in index order (0-based). For each rule:
   - Read `condition.combiner` (`AND` / `OR`) and `condition.matchers[]`.
   - For each matcher: if shape is unrecognized (unknown `type`, or expected value fields absent) → mark that matcher **unparsed**; continue scanning remaining matchers and rules.
   - Apply confirmed predicates at confirmed conjunction scope. Record: rule index, combiner, `negate` value (preserve; do not invert predicate logic).
4. For segment-reference predicates, also inspect `treatments[].segments`, `treatments[].largeSegments`, `treatments[].ruleBasedSegments`. Report rule-matcher hits and treatment-level hits separately.
5. Do **not** scan `description`, `configurations`, `defaultRule` buckets, or `defaultTreatment` for attribute/value predicates.

## Segment Name Resolution

When the user provides a segment name without type:
- Fully paginate all three types (STANDARD, LARGE, RULE_BASED), explicitly covering ACTIVE and ARCHIVED metadata with declared status filters as needed. Show exact-name matches with their type and status; an ACTIVE-only lookup cannot rule out an archived segment.
- Ask the user to confirm which type(s) to match.
- Reuse the segment lists across all flags — do not re-fetch per flag.
- A name match with the wrong type is **not** a predicate match; report the type mismatch in Notes.

## Coverage Output

Append to every pattern-search result:

```
Coverage: matched N · no-match M · unparsed P · unchecked U
```

- **matched**: at least one rule or treatment match found.
- **no-match**: definition fully parsed, no match found. Only valid when all matchers were recognized.
- **unparsed**: at least one unrecognized/malformed matcher; known matches retained but coverage is incomplete for that flag.
- **unchecked**: some requested flag/environment coverage was not read (fetch error, page failure, or cost-guard stop). Retain any already-observed matches and label that flag's remaining coverage incomplete.

Count distinct flags within each category, not result rows. A flag may be both **matched** and **unparsed** or **unchecked**; disclose overlaps rather than summing these into a unique total. A **no-match** verdict requires every requested environment to be read and all relevant structures parsed, including treatment memberships. An unknown relevant combiner or malformed rules/membership collection is unparsed, not empty.

## Unparsed Shapes

Mark a matcher unparsed when: `type` is absent or unknown; expected value fields for the declared type are absent; or the object contains nesting not described by the known schema. Record the rule index and matcher index. Do not abort the flag scan — continue remaining matchers and rules.

## Killed and Archived Handling

| Global status | `isKilled` | Action |
|---------------|-----------|--------|
| ACTIVE | false | Normal scan |
| ACTIVE | true | Scan; annotate matches `inactive (killed)` |
| ARCHIVED | any | Scan when requested; annotate `inactive (archived)`; no live-exposure statement |

## Output Example

```
| Flag      | Env     | Rule # | Combiner | Negated | Matcher type   | Predicate match                    | Status              | Notes                        |
|-----------|---------|--------|----------|---------|----------------|------------------------------------|---------------------|------------------------------|
| flag-a    | prod    | 0      | AND      | no      | IN_LIST_STRING | attribute=country, value=US        | matched             |                              |
| flag-a    | staging | 0      | AND      | no      | IN_LIST_STRING | attribute=country, value=US        | matched             |                              |
| flag-b    | prod    | —      | —        | —       | —              | segment beta-users (STANDARD) in treatments[0].segments | matched | treatment-level |
| flag-c    | prod    | 1      | OR       | yes     | BETWEEN_NUMBER | —                                  | unparsed            | missing 'between' field      |
| flag-d    | prod    | 0      | AND      | no      | IN_LIST_STRING | attribute=country, value=US        | matched             | inactive (archived)          |

Coverage: matched 3 · no-match 0 · unparsed 1 · unchecked 0
```

## Edge Cases

| Scenario | Handling |
|----------|----------|
| Match in some envs, not others | One row per env; flag counts once as matched |
| Segment name found in two types | Report both; ask user which type was intended |
| `negate: true` on a rule or matcher | Preserve in Negated column; do not invert match logic |
| Flag dependency — treatment unspecified | Match on `depends.splitName` only; note treatment not checked |
| Flag has no rules | no-match (if all treatment arrays also checked and empty) |
| >50 flags — cost guard fires | Stop before any definition fetch; report flag count; ask to narrow |
| Partial page failure | Retain observed matches; mark remaining flag coverage unchecked, not no-match |
