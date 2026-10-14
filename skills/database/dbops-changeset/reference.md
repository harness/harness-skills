# DBOPS Liquibase YAML Rules

All Liquibase YAML generation rules for the DBOPS changeset skill. The
`**dbops_changeset` SKILL.md** handles schema/instance discovery, review UI,
and pipeline execution; this file defines **how** to write the YAML in Step 4.

Read this file in full before generating or refining any Liquibase changeset. Use the
exact path listed in the Skill tool result — do not search for skill files.

---

## Structure

Always wrap in `databaseChangeLog`. Each `changeSet` must contain **EXACTLY ONE**
change operation. Never combine multiple DDL operations (e.g., CREATE TABLE + ADD INDEX)
into a single `changeSet` unless they are inseparable.

Use **kebab-case** for `id` values (e.g., `add-users-email-index`).

**No inline YAML comments.** Do NOT add `# ...` comments anywhere in the generated YAML. The `comment:` field on each `changeSet` is the only place for descriptions — it is a Liquibase field, not a YAML comment.
Use `**${}`** parameterization (e.g., `${tableName}`) for table/column names when the
user's request implies the value should be an input variable rather than a hardcoded literal.

```yaml
databaseChangeLog:
  - changeSet:
      id: <kebab-case-descriptive-id>
      author: <display_name or "harness-ai">
      comment: <brief purpose — required>
      labels: ""
      changes:
        - <changeType>:
            ...
      rollback:
        - <inverse-change>:
            ...
```

---

## Required Fields on Every changeSet


| Field     | Rule                                                                                              |
| --------- | ------------------------------------------------------------------------------------------------- |
| `author`  | Use the Harness user `display_name` from context when available; otherwise `harness-ai`.          |
| `comment` | **Required.** One-line LLM-generated summary of what this changeset does (purpose of the change). |
| `labels`  | **Required.** Always present; use `labels: ""` by default so users can add labels later.          |


---

## Plan of Attack (Multi-Step Migrations)

Before generating YAML for a **multi-step** request (e.g., add column + backfill + triggers + zero-downtime):

1. Internally order work as: **schema change(s)** → **supporting objects** (indexes, triggers) → **batch data migration** (INSERT/UPDATE/DELETE affecting many rows) → **post-migration cleanup** (rebuild index, etc.).
2. Map each step to one or more `changeSet` blocks in that order.
3. Each `changeSet` still obeys **one primary change operation** per block (split DDL vs DML across separate changesets).

---

## Batch Data Migrations

When a data change may touch **more than ~1000 rows** (or the user asks for zero-downtime / no long-lived locks):

- Set `**runInTransaction: false`** on that changeset.
- Use **batched** SQL: commit per batch or idempotent small batches; do **not** wrap a multi-batch loop in a single `BEGIN TRAN` … `COMMIT` unless the user explicitly wants atomicity and accepts the risks.
- **MSSQL:** Prefer a short pause between batches, e.g. `WAITFOR DELAY '00:00:00.1'` where appropriate.
- **Rollback:** Prefer a batched or idempotent rollback; if a safe rollback is impossible, use `rollback: []` and comment why.

---

## Preconditions

Add `preConditions` when the user specifies conditional execution, to avoid double-applying a change, or for destructive/rename operations.

- Place `preConditions` **inside** the `changeSet`.
- Always set `**onFail`**: `HALT`, `WARN`, or `MARK_RAN` as appropriate.
- **addColumn:** prefer `**columnNotExists`** for the new column.
- **dropColumn:** prefer `**columnExists`** for the column.
- **Destructive ops (DROP, RENAME):** ensure table/column exists as needed.
- Combine preconditions with `**and`**, `**or`**, `**not**` when needed.

Common precondition checks: `tableExists`, `columnExists`, `indexExists`,
`dbms` (restrict to a specific engine), `runningAs` (restrict to a DB user),
`sqlCheck` (arbitrary SQL expression), `changeSetExecuted`.

Example with logical operators:

```yaml
preConditions:
  - onFail: HALT
  - and:
      - tableExists:
          tableName: my_table
      - not:
          - columnExists:
              tableName: my_table
              columnName: my_column
```

---

## Rollback

Always include a `**rollback**` block for every `changeSet`. Use the table below for common
change types. For any change type **not listed here**, fetch the Liquibase docs page for that
change type at `https://docs.liquibase.com/change-types/<change-type-name>.html` to confirm
the correct rollback — do not guess.


| Change                     | Rollback                                                        |
| -------------------------- | --------------------------------------------------------------- |
| `createTable`              | `dropTable`                                                     |
| `addColumn`                | `dropColumn`                                                    |
| `dropTable`                | `rollback: [] # irreversible — table structure not recoverable` |
| `dropColumn`               | `rollback: [] # irreversible — column data not recoverable`     |
| `createIndex`              | `dropIndex`                                                     |
| `dropIndex`                | `createIndex` (re-create with same definition)                  |
| `addForeignKeyConstraint`  | `dropForeignKeyConstraint`                                      |
| `dropForeignKeyConstraint` | `addForeignKeyConstraint` (re-create with same definition)      |
| `renameTable`              | `renameTable` (swap old/new names back)                         |
| `renameColumn`             | `renameColumn` (swap old/new names back)                        |
| `insert` / `insertMany`    | `delete` matching the inserted rows                             |
| `update`                   | `rollback: [] # irreversible unless original values are known`  |
| `delete`                   | `rollback: [] # irreversible — deleted data not recoverable`    |
| Truly irreversible change  | `rollback: [] # irreversible`                                   |


**Destructive operations that should use `rollback: []`** (do not attempt to generate a
complex rollback for these — the risk of a wrong rollback is worse than none):
`dropTable`, `dropColumn`, `delete`, `update` (when original values unknown), `truncateTable`.

---

## Database-Type Timestamp Rules

Use the correct timestamp type and default **per engine** for audit columns:


| Engine     | Type        | Default pattern                                                               |
| ---------- | ----------- | ----------------------------------------------------------------------------- |
| MySQL      | `TIMESTAMP` | `DEFAULT CURRENT_TIMESTAMP` / `ON UPDATE CURRENT_TIMESTAMP` where appropriate |
| PostgreSQL | `TIMESTAMP` | `DEFAULT NOW()`                                                               |
| Oracle     | `TIMESTAMP` | `DEFAULT SYSTIMESTAMP`                                                        |
| MSSQL      | `DATETIME2` | `DEFAULT GETDATE()`                                                           |
| Spanner    | `TIMESTAMP` | `DEFAULT (CURRENT_TIMESTAMP())`                                               |
| DB2        | `TIMESTAMP` | `DEFAULT CURRENT TIMESTAMP`                                                   |
| Sybase     | `DATETIME`  | `DEFAULT GETDATE()`                                                           |
| MongoDB    | N/A         | Documents, not SQL DDL columns                                                |


### createdAt / updatedAt on New SQL Tables

For **new table creation** (`createTable`) on SQL databases, **always** add `**createdAt`** and `**updatedAt`** (or project-standard naming) with types and defaults matching the engine row above, unless the user explicitly forbids them.

---

## MongoDB-Specific Rules

Liquibase MongoDB change types require **JSON strings** for document/command payloads — not YAML inline objects for those fields.

- **createIndex:** `keys` and `options` must be **JSON strings**; `**name` is required** inside `options`.
  - Example: `keys: '{"field1": 1, "field2": -1}'`, `options: '{"name": "idx_field1_field2", "unique": true}'`
- **insertOne:** `document` must be a **JSON string**.
  - Example: `document: '{"name": "John", "age": 30}'`
- **insertMany:** `documents` must be a **JSON string** array.
  - Example: `documents: '[{"name": "John"}, {"name": "Jane"}]'`
- **runCommand / adminCommand:** `command` must be a **JSON string**.
  - Example: `command: '{"createIndexes": "collection", "indexes": [...]}'`

Common types: `createCollection`, `dropCollection`, `createIndex`, `dropIndex`, `insertOne`, `insertMany`, `runCommand`, `adminCommand`. Use a document-oriented model; avoid relational constructs.

Clarify whether the user wants an **index**, **schema validation**, or **data migration** before generating.

---

## Common Change Types (SQL Examples)

```yaml
# Create table (always add createdAt/updatedAt per engine — example shows created_at)
- createTable:
    tableName: users
    columns:
      - column:
          name: id
          type: BIGINT
          autoIncrement: true
          constraints:
            primaryKey: true
            nullable: false
      - column:
          name: email
          type: VARCHAR(255)
          constraints:
            nullable: false
            unique: true
      - column:
          name: created_at
          type: TIMESTAMP
          defaultValueComputed: CURRENT_TIMESTAMP

# Add column
- addColumn:
    tableName: users
    columns:
      - column:
          name: phone
          type: VARCHAR(20)
          constraints:
            nullable: true

# Drop column
- dropColumn:
    tableName: users
    columnName: legacy_field

# Create index
- createIndex:
    indexName: idx_users_email
    tableName: users
    columns:
      - column:
          name: email

# Add foreign key
- addForeignKeyConstraint:
    baseTableName: orders
    baseColumnNames: user_id
    constraintName: fk_orders_users
    referencedTableName: users
    referencedColumnNames: id
    onDelete: CASCADE

# Rename column (use modifyDataType if just changing type)
- renameColumn:
    tableName: users
    oldColumnName: username
    newColumnName: user_handle
    columnDataType: VARCHAR(100)
```

Use native Liquibase change types from the official docs. Prefer change types over raw `sql`
unless the user supplies SQL or explicitly needs it. Always validate that all required parameters
are provided for each change type before emitting the YAML.

Default data types when not specified: `VARCHAR(255)` for name/title strings, `BIGINT` for
surrogate IDs, `INT` for counters. Apply `NOT NULL` on primary keys; use sensible defaults
for timestamps per engine table above.

---

## Snapshot Name Alignment

When snapshot metadata was fetched in Step 3-B of the skill, use it to **silently correct**
name mismatches before generating — do NOT ask for confirmation:

- **Typo in column/table name:** User says "stret", snapshot has "streets" → use "streets" directly.
- **Case mismatch:** User says "Country", snapshot has "country" → use "country" directly.
- **Close match exists:** If the user's input is close to exactly one name in the snapshot,
use the correct one silently. Mention the correction in your reply text.

**Ask for clarification only when:**

- Multiple snapshot names are equally close (genuine ambiguity — cannot resolve automatically).
- No close match exists at all and the operation requires an existing name.

**Example — DO NOT do this:**
❌ "I notice 'street' might be a typo for 'streets'. Would you like to use 'streets'?"

**Example — DO this instead:**
✅ Silently use "streets" and generate the changeset. State in your reply:
"Created index on columns 'country' and 'streets' in the batman table."

---

## Foreign Key Column Resolution

When adding or modifying a foreign key (`addForeignKeyConstraint`), resolve
`baseColumnNames` and `referencedColumnNames` using snapshot metadata fetched in
Step 3-B-4 when available. Apply snapshot name alignment to any user-provided names first.

### Column resolution

Snapshot fetch is performed in Step 3-B-4 (authoritative). This section covers
alignment and scoring only.

Score candidate pairs from snapshot metadata (columns, types, PK/unique/FK constraints).
Use the **highest-scoring** pair; ask only when multiple pairs tie at the top.

Generic names (`id`, `identifier`, `uuid`, `guid`, `pk`, `key`, `code`, `ref`,
`reference_id`) are weak same-name signals — most tables have them; do not pair on
generic name alone.

| User provides | Action |
| ------------- | ------ |
| Both `baseColumnNames` and `referencedColumnNames` | Apply snapshot name alignment to both; use corrected names directly — no scoring needed. |
| Only base column | Apply snapshot name alignment to the base column; score referenced columns against it. |
| Only referenced column | Apply snapshot name alignment to the referenced column; score base columns against it. |
| Neither column | Score all cross-table pairs from the snapshots fetched in Step 3-B-4. |

| Signal | Score | Notes |
| ------ | ----- | ----- |
| User explicitly named this column | Highest | Always honor the provided side. |
| Semantic FK name on base table | High | e.g. `user_id` on `orders` → `users.id`; derive from referenced table name (singular/plural). |
| Existing FK in snapshot with same pairing | High | Reuse the same column pattern already in the schema. |
| Referenced column is PK **and** semantic name matches | High | e.g. `user_id` → PK `id` on `users` — not bare `id` → `id`. |
| Compatible data types | Medium | Required for a valid pair; does not alone pick among candidates. |
| Same non-generic column name on both tables | Medium | e.g. `customer_code` ↔ `customer_code`. |
| Same **generic** name on both tables | Low | e.g. `id` ↔ `id` — only if no higher-scoring pair exists and user named one side. |
| Referenced column is PK with no semantic match | Low | Only when no `<table>_id`-style column exists on the base table. |

**When to ask vs proceed:** Proceed silently when one pair clearly wins. If snapshot
metadata is unavailable or stale, proceed using user-provided names (per Step 3-B-4).
Ask only when top-scoring pairs tie after scoring. State the inferred mapping in your
reply, e.g. "Linked `orders.user_id` → `users.id`."

---

## Clarifying Questions Policy

**Always ask** before generating when:

1. **Missing identifiers** — table/collection name, column(s) for the operation, or FK targets are not stated.
  - Example: "Add index in collection person" → Ask: "Which fields should be indexed in the person collection?"
  - Example: "Drop column from users" → Ask: "Which column should be dropped from the users table?"
2. **Destructive operations** — drop/rename table or column without a clear target mapping.
3. **Incomplete index ops** — index requested but indexed fields/columns not specified.
4. **Missing constraint details** — FK without referenced table, or FK column mapping that cannot be
   resolved automatically (see **Foreign Key Column Resolution → Column resolution** above); unique constraint without target column(s).
5. **Conflicting context** — mixed SQL vs MongoDB expectations or contradictory requirements.

**Ask if risky** (judgment):

- Ambiguous column types, enums, or business-specific defaults.
- Operations that may be unsupported on the target engine.

**Proceed with sensible defaults** when standard additions are clear:

- Typical string/name columns: `VARCHAR(255)` unless specified.
- Surrogate IDs: `BIGINT` with auto-increment where appropriate.
- Timestamps: per engine table above.
- **Do not** ask about rollback strategy — always include rollback per rules above.
- **Do not** ask about bare Liquibase syntax — infer from docs.

---

## Author, Update Mode, and Error Recovery

- **New YAML (first turn):** Include all required fields (`author`, `comment`, `labels`).
- **Multi-turn accumulation:** On every follow-up turn, treat the most recent generated
  `databaseChangeLog` YAML in the conversation as the **running baseline** and produce the
  full accumulated changelog. See the accumulation rules in SKILL.md Step 4 for the four
  intent types (add / modify / drop / undo) and their merge behaviour. Never emit only the
  delta changeSet — always present the complete merged `databaseChangeLog`.
- **Update mode (single-changeSet refinement):** When the user explicitly refines or corrects
  one specific existing `changeSet` (e.g., fixes a column type), preserve that changeSet's
  `id` and `author` and apply only the requested modifications. Maintain YAML indentation and
  structure. Still present the full accumulated changelog.
- **Error recovery (Liquibase or OPA):** Identify the root cause, patch the YAML to fix it,
preserve structure, and explain the fix **before** presenting the revised YAML.

Common root causes to look for:

- Missing `rollback` block
- Illegal or reserved table/column name for the target engine
- Wrong data type for the target engine (e.g., `DATETIME2` vs `TIMESTAMP`)
- Duplicate `changeSet` id within the changelog
- Invalid precondition syntax or missing `onFail`
- **OPA policy violation** — extract the policy's error text verbatim (e.g., "Index creation
does not follow naming convention"), correct the changeset to satisfy the policy (rename the
index, change the operation, etc.), and explain what was changed and why before presenting.

---

## When in Doubt — Look It Up, Never Guess

**Do not guess Liquibase syntax, parameters, or behavior.** If you are uncertain about
anything — a change type, a parameter name, rollback behavior, YAML structure, engine-specific
restrictions, precondition syntax, or MongoDB extension support — look it up first.

**Use `webFetch` with this URL pattern:**

`https://docs.liquibase.com/change-types/<change-type-name>.html`

Examples:
- `https://docs.liquibase.com/change-types/add-column.html`
- `https://docs.liquibase.com/change-types/create-index.html`
- `https://docs.liquibase.com/change-types/home.html` (full index)

**If `webFetch` fails**, use `webSearch` instead — do not guess.

Use this for any of the following — not just change types:

- Rollback definition for a specific change type
- Required vs optional parameters on any change type
- Correct YAML syntax or nesting for a feature
- Engine-specific restrictions or unsupported operations
- Precondition types and their parameters
- MongoDB extension change types and JSON string format requirements

