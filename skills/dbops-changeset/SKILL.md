---
name: dbops-changeset
description: >-
  Generates Liquibase database changesets via a structured workflow:
  resolve schema+instance (from context or via API discovery),
  confirm DB engine type, generate Liquibase YAML, and present for
  HITL review with Accept / Deny / Accept & Commit actions.
  Supports update mode (refine existing changeset) and error-recovery
  mode (fix a failed migration).
metadata:
  author: Harness
  version: 2.1.0
  mcp-server: harness-mcp-v2
  module: DBOPS
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 `dbops` toolset
  (resource types: database_schema, database_instance, database_default_authoring_instance,
  database_snapshot_object, database_execute_llm_authoring_pipeline). Connector lookup uses
  the `connectors` toolset `connector` resource. Review is done in chat (Accept / Deny /
  Accept & Commit) because `present_for_review` is not available.
---

# DBOPS Changeset Generation

Generate Liquibase database changesets from natural language descriptions,
anchored to a real schema and instance from the Harness DBOPS service.

## When to Use

When the user asks to:

- Create, add, modify, or drop tables, columns, indexes, constraints, or views as Liquibase changeset operations
- Generate a database migration or changeset
- Fix a failed migration or update an existing changeset
- Apply schema changes as Liquibase YAML

## Prerequisites

The Skill tool loads this file (SKILL.md) automatically — do not Read it again.

Before generating Liquibase YAML, Read `reference.md` using the exact path listed in
the Skill tool result. It contains all Liquibase YAML rules, change types, rollback
patterns, batch migration guidelines, MongoDB JSON string requirements, and the
clarifying questions policy. Apply those rules in Step 4 when generating the changeset.

## Full Workflow

### Step 0: Check for Pre-Seeded Context (ALWAYS do this first)

At conversation start, the initial message may contain a JSON block with
pre-selected identifiers injected by the Harness frontend UI:

```json
{
  "dbops_schema_id": "users-schema",
  "dbops_instance_id": "prod-instance"
}
```

**Read this JSON block** (if present) before doing any tool calls.


| What's in context                       | What to do                                            |
| --------------------------------------- | ----------------------------------------------------- |
| `dbops_schema_id` + `dbops_instance_id` | Skip Steps 1 AND 2 — but **immediately fetch instance metadata** via `harness_get(resource_type="database_instance", resource_id="<dbops_instance_id>", dbschema_id="<dbops_schema_id>")` to obtain `connector` (needed in Step 3) and check `hasSnapshot` (needed in Step 3-B). |
| Only `dbops_schema_id`                  | Skip Step 1 — use this schema ID. Then go to Step 2-A |
| Neither                                 | Full Steps 1 and 2                                    |


### Step 1: Discover Database Schemas (skip if `dbops_schema_id` is in context)

Call `harness_list` for the available schemas:

```
harness_list(resource_type="database_schema")
```

The response is a plain JSON array of objects. Each object has:

- `identifier` — used as the schema ID in subsequent calls
- `name` — human-readable name
- `migrationType` — `"Liquibase"` or `"Flyway"` (only Liquibase supported)
- `instanceCount` — number of linked instances
- `primaryDbInstanceId` — the designated instance for LLM authoring (may be empty). If non-empty, Step 2-A uses this directly as the `instance_id` without further discovery.

**Disambiguation:**

- If the array has **one schema**, select it automatically.
- If the array has **multiple schemas**, use `AskUserQuestion` (selection mode):
Show: `[<name> (<identifier>) — <migrationType>, <instanceCount> instances]` for each.
- If the array is **empty**: "No database schemas found in this project. Create one in Harness DBOPS first."
- If `migrationType` is `"Flyway"`: "This skill supports Liquibase schemas only."

### Step 2-A: Resolve Instance from Schema (when only `dbops_schema_id` is known)

When you have a `schema_id` but no `instance_id` (from context OR after Step 1 selection):

1. Call `harness_get` to fetch the full schema:
  ```
   harness_get(resource_type="database_schema", dbschema_id="<schema_id>")
  ```
2. Check the `primaryDbInstanceId` field in the response:
  - **If set**: use it as the `instance_id`. Inform the user:
   "Using primary instance `<primaryDbInstanceId>` for schema `<name>`."
   Then fetch the instance to obtain the `connector` field needed in Step 3:
   ```
   harness_get(resource_type="database_instance", resource_id="<primaryDbInstanceId>",
               dbschema_id="<schema_id>")
   ```
   Read `connector` from the response.
  - **If empty or missing**: fall through to Step 2-B.

### Step 2-B: Auto-select Best Instance (when `primaryDbInstanceId` is empty)

Use the `database_default_authoring_instance` resource to let the server pick the best
instance (oldest with a metadata snapshot; falls back to oldest overall):

```
harness_get(resource_type="database_default_authoring_instance", dbschema_id="<schema_identifier>")
```

The response is `{ identifier: string, name: string, hasSnapshot: boolean, connector: string }`.

**Handling the response:**

- **If the tool call returns results:** Use `identifier` as the `instance_id` and `connector` as the
connector identifier for Step 3 (no separate instance detail fetch needed). Inform the user:
"Using instance `<name>` (`<identifier>`) for schema `<schema_name>`."
If `hasSnapshot` is `true`, the instance has metadata available for snapshot lookups — proceed
to Step 3-B for **any** changeset intent (create, modify, or drop). If `false`, skip Step 3-B entirely.
- **Not found (404 OR empty result):** Reply: *"No instances found for schema `<schema_name>`. Please add an instance in Harness DBOPS first — open **Harness → DBOPS → Schemas → `<schema_name>` → Add Instance**."* — STOP. Do NOT prompt the user for a connector identifier. Do NOT proceed to Step 3. Do NOT generate a changeset.

### Step 3: Resolve Database Engine Type from Connector

**Invariant.** By this point you MUST have a non-empty `connector` value from Step 0 (fast-path
instance fetch), Step 2-A, or Step 2-B — whichever applied. If you do not — for any reason —
STOP and surface the Step 2 "instance not found" message to the user. Never ask the user to
provide a connector identifier directly; connectors are always derived from an existing DBOPS
instance.

Use the `connector` field obtained in Step 0, Step 2-A, or Step 2-B (whichever ran). Fetch the
connector to determine the engine type:

```
harness_get(resource_type="connector", resource_id="<connector>",
            org_id="<org_id>", project_id="<project_id>")
```

The connector is always a JDBC connector. Read `connector.spec.url` and map the prefix:


| `connector.spec.url` prefix          | Engine     |
| ------------------------------------ | ---------- |
| `jdbc:mysql://` or `jdbc:mariadb://` | MySQL      |
| `jdbc:postgresql://`                 | PostgreSQL |
| `jdbc:oracle:thin:`                  | Oracle     |
| `jdbc:sqlserver://`                  | MSSQL      |
| `jdbc:mongodb://`                    | MongoDB    |
| `jdbc:cloudspanner:`                 | Spanner    |
| `jdbc:db2://`                        | DB2        |
| `jdbc:sybase:`                       | Sybase     |
| `jdbc:sqlite:`                       | SQLite     |


**If the URL prefix is unrecognised**, proceed with generic ANSI SQL. Do NOT ask the user.

### Step 3-B (Optional): Snapshot metadata check

Run this step for **any** changeset intent (create, modify, or drop) when `hasSnapshot` is `true`.

**Purpose:**
- For **CREATE** intents: verify the target object does not already exist (conflict check).
- For **modify/drop** intents: align names with the latest snapshot.
- For **foreign key** intents: resolve column mappings from snapshot metadata (Step 3-B-4).

#### 3-B-1: List existing object names

Call with `dbschema_id`, `dbinstance_id`, and the relevant `object_type` (`"Table"`, `"Index"`, `"View"`, etc.):

```
harness_list(
  resource_type="database_snapshot_object",
  filters={
    dbschema_id: "<schema_id>",
    dbinstance_id: "<instance_id>",
    object_type: "Table"
  }
)
```

Returns `{ data: string[] }` — names of objects of that type in the current snapshot.

**If the list API errors or returns an empty `data` array**, treat the snapshot as stale — proceed to Step 4 without blocking the user (stale-snapshot tolerance).

#### 3-B-2: Conflict check for CREATE intents

If the user's intent is to **create** an object (new table, index, view, etc.) and the target name
appears in the `data` list returned above:

- **Do NOT generate a CREATE changeset.**
- Inform the user clearly:
  > "The `<object_type>` `<name>` already exists in the current snapshot for instance `<instance_name>`.
  > A CREATE changeset would fail. Did you mean to modify it instead?
  > I can generate an **ALTER TABLE** (add column / modify column / add index / add constraint)
  > changeset if you describe the change you need."
- **Stop and wait for the user's response.** Resume from Step 4 once the user clarifies.

If the name is **not** in the list (expected case for a genuine new object), proceed to Step 4.

#### 3-B-3: Fetch full metadata for modify/drop intents

When modifying or dropping an **existing** object, fetch its full metadata (columns, indexes, etc.) — requires **non-empty** `object_names`:

```
harness_get(
  resource_type="database_snapshot_object",
  resource_id="<instance_id>",
  params={
    dbschema_id: "<schema_id>",
    object_type: "Table",
    object_names: ["<table_name>"]
  }
)
```

If the target name is **not** in the snapshot list for a modify/drop intent, proceed anyway — the snapshot may be stale; do not block the user.

#### 3-B-4: Resolve foreign key column mappings

Run when the intent involves adding or modifying a foreign key (`addForeignKeyConstraint`),
including FK constraints added during `createTable`.

Fetch snapshot metadata in one `harness_get` call. Which tables to include depends on intent:

- **`addForeignKeyConstraint` on an existing table:** fetch **both** `baseTableName` and
  `referencedTableName` — needed for snapshot name alignment and column scoring on both sides.
- **`createTable` with inline FK constraints:** fetch **only** `referencedTableName` — the
  new base table is not in the snapshot yet; base columns come from the changeset definition.

```
harness_get(
  resource_type="database_snapshot_object",
  resource_id="<instance_id>",
  params={
    dbschema_id: "<schema_id>",
    object_type: "Table",
    object_names: ["<base_table>", "<referenced_table>"]
  }
)
```

For `createTable` with inline FK, use `object_names: ["<referenced_table>"]` only.

Apply column-resolution rules in `reference.md` → **Foreign Key Column Resolution** →
**Column resolution**. If snapshot metadata is unavailable, proceed using user-provided
names only.

**Canonical DBOPS `resource_type` values** (see `dbops` toolset): `database_schema`, `database_instance`, `database_default_authoring_instance`, `database_snapshot_object`, `database_execute_llm_authoring_pipeline`.

### Step 4: Generate the Changeset

Produce a valid Liquibase YAML changeset. All YAML generation rules (structure,
required fields, rollback, preconditions, timestamps, batch migrations, MongoDB
formats, clarifying questions) are in `**reference.md`** in this directory — follow
them exactly.

**Changeset author:** Derive the author name from `.harness_context/user_context.json` (if present) or the `## User Context:` block in the conversation. Apply these rules in order:

1. **Check for username:** Look for `user.display_name`, `uid`, or `username` in the user context.
2. **Normalize the username:** Apply these transformations in order:
  - Convert to lowercase
  - Remove extra spaces
  - Convert internal spaces into `-` (hyphen)
  - Remove all special characters (keep only `a-z`, `0-9`, and `-`)
3. **Fallback to email:** If no username is available, extract from the `email` field:
  - Take the part before the `@` symbol (e.g., `john.doe@harness.io` → `johndoe`)
  - Apply the same normalization rules above
4. **Final fallback:** If neither username nor email is available, use `harness-ai`.

**Examples:**


| Context Value                                 | Derived Author   |
| --------------------------------------------- | ---------------- |
| `display_name: "John Doe"`                    | `john-doe`       |
| `display_name: "Jane_Smith-123"`              | `jane-smith-123` |
| `email: "dev.user@company.com"` (no username) | `devuser`        |
| Neither available                             | `harness-ai`     |


**Multi-turn accumulation (follow-up prompts):** If the conversation already contains a
previously generated `databaseChangeLog` YAML (from any prior turn, whether accepted, denied,
or still pending review), that YAML is the **running baseline**. On every follow-up turn you
MUST produce the **full accumulated changelog** — not just the delta for this turn.

Classify the user's intent and merge accordingly:

| Intent | Merge behaviour |
|---|---|
| **Add** a new object (new table, column, index, etc.) | Append one or more new `changeSet` blocks to the end of the baseline `databaseChangeLog` |
| **Modify** an object that already has a `changeSet` in the baseline | Update the matching `changeSet` block in-place; preserve its `id` and `author` |
| **Drop / remove** an object that has a `changeSet` in the baseline | Remove or replace the matching `changeSet` block with the appropriate `dropTable` / `dropColumn` etc. changeSet |
| **Undo / clear / start over** | Discard the entire baseline; generate a fresh `databaseChangeLog` |

Always present the **complete, merged `databaseChangeLog`** (all accumulated `changeSet` entries)
for review — never only the new delta.

**Update mode (refining a single changeSet):** If the user is explicitly refining or correcting
one specific changeSet from the baseline (e.g., "change the column type in the dog table
changeset"), apply the modification to that `changeSet` block in-place. Preserve the `id` and
`author` from that changeSet and apply the requested modifications. Still present the full
accumulated changelog.

**Error recovery mode:** See **Error Recovery Mode** section below.

---

## Step 5: Present for Review

The `present_for_review` tool is **not available**. Present the change for review in chat:

1. Show the full generated Liquibase YAML in a fenced `yaml` code block.
2. Clearly ask the user to choose **one** of these three options:
   - **Accept** — save the changeset only (do not execute a pipeline)
   - **Accept & Commit** — save and execute the DBOPS authoring pipeline
   - **Deny** — discard / request changes and regenerate

Example prompt after the YAML:

> Please review the changeset above and reply with one of:
> **Accept**, **Accept & Commit**, or **Deny**.

**CRITICAL:**

- Always present all three options: Accept, Accept & Commit, Deny.
- Always present the complete, merged `databaseChangeLog` — never only the new delta.
- Wait for the user's choice before proceeding to Step 6.
- If the user edits the YAML before choosing, **always use their edited YAML**, not your original generation.

---

## Step 6: Handle the User's Action

### `"accept"` — Save only

Confirm the changeset is saved. Do NOT execute any pipeline. Reply with a short confirmation message referencing the schema and instance names.

### `"deny"` — Discard

Ask what they want to change and regenerate from Step 4. DO NOT re-run the schema/instance discovery — the schema and instance are already selected.

### `"accept_commit"` — Save + Execute Pipeline

After the user accepts:

**IMPORTANT — use already-resolved identifiers:** The `schema_id`, `instance_id`, and the
instance's `connector` were resolved in Steps 1–2 and are still in context. **Do NOT re-list
schemas, re-fetch instances, or list connectors** — use the values you already have.

**IMPORTANT — changeset encoding:** Send the `changeset` field as **PLAIN-TEXT YAML**, exactly as
the user accepted it. **Do NOT base64-encode it.**.

**IMPORTANT — `conversation_id` (REQUIRED before `harness_execute`):** Always pass `conversation_id` explicitly when calling `harness_execute` for the `database_execute_llm_authoring_pipeline` resource. Resolve it from agent context in this order:

1. `conversation_id`
2. `session_id` (use the session ID as the `conversation_id` value)

It is a **hard requirement** before making the execute-pipeline tool call. Never fabricate or generate a conversation ID — it is the billing dedup key and must come from the platform. If neither `conversation_id` nor `session_id` is present in agent context, STOP — do **not** call `harness_execute`. Tell the user pipeline execution cannot proceed without a conversation/session ID.

**IMPORTANT — chat runner gate protocol.** The user already consented via
**Accept & Commit**, but the chat runner may render a separate permission
prompt before forwarding `harness_execute`. Handle it deterministically:

| Tool response or system event contains… | What to do |
|---|---|
| `waiting for user to confirm` / `waiting for user to review` / `awaiting confirmation` / `pending user approval` (case-insensitive) | Reply EXACTLY: *"Pipeline execution is awaiting your approval — please approve the permission prompt to trigger the run. I will not call additional tools until you do."* Do NOT call any tool. Each retry stacks another prompt. |
| `user confirmed` / `user approved` / `run approved` (case-insensitive) | Re-issue `harness_execute` ONCE with the EXACT same args you used pre-gate (same `schema_id`, `instance_id`, `changeset`, `conversation_id`, branch flag). Do NOT re-walk Steps A–E. If a duplicate confirmation event arrives before the call returns, ignore it. After `harness_execute` returns, treat any further confirmation events for this turn as no-ops — do NOT call `harness_execute` a third time. |
| `user declined` / `user cancelled` / `request cancelled` (case-insensitive) | Do NOT call `harness_execute`. Reply: *"Pipeline trigger cancelled. Click Accept & Commit again to retry, or ask me to modify the changeset first."* |

**Branch-lock.** Once Step A picks custom vs default, the decision is locked
until `harness_execute` returns a result or the user cancels — never re-evaluate
it after a gate event, even if the NG setting could have changed.

**Args lost to context compaction.** If a `user confirmed` event arrives but
your context no longer holds the original `harness_execute` args, reply:
*"Approval received but I need to regenerate. Can you re-confirm Accept & Commit on the changeset?"* — do NOT speculatively reconstruct args.

**Post the success message ONLY** after `harness_execute` returns a non-empty
`executionId`.

#### Step A — Read the NG setting to pick the branch

```
harness_list(resource_type="setting", filters={ category: "DBOPS", scope: "project" }, compact=false)
```

Find the entry with `identifier == "dbops_llm_authoring_pipeline"`. Read its `value` field.

- If `value` is a **non-empty string** → **custom-pipeline branch** (continue to Step B).
- If `value` is **empty** or the setting is **absent** → **default-pipeline branch** (skip to Step E).

---

#### Step B — Fetch the pipeline's runtime-input template (custom-pipeline branch only)

```
harness_get(
  resource_type="runtime_input_template",
  resource_id="<value from Step A>",
  account_id="<account>", org_id="<org>", project_id="<project>"
)
```

The response's `inputSetTemplateYaml` lists every `<+input>` token the admin's pipeline
declares. The skill is responsible for these three reserved tokens (the server expects these
EXACT YAML keys — see the dbops `database_execute_llm_authoring_pipeline` resource schema):

- `dbSchema` — auto-filled with `schema_id`.
- `dbInstance` — auto-filled with `instance_id`.
- `changeset` — auto-filled with the PLAIN-TEXT changeset YAML.

The pipeline's `stepGroupInfra.spec.connectorRef` is also a `<+input>` token but is filled
**server-side** from the DBOPS instance — the skill never sends a value, never asks the user
for it.

**If a template field's name does not match any of the canonical names or aliases above, treat
it as non-reserved and elicit it in Step C.** Do NOT silently auto-fill it from a similarly-named
context value (e.g. a template field called `schema` or `db_schema` is non-reserved — ask the user).

#### Step C — Diff and elicit the remaining required inputs (custom-pipeline branch only)

> **Server-side note (current state):** the db-devops-service execute endpoint currently
> rejects any non-empty `runtime_inputs` map with the error `"custom runtimeInputs are not yet supported (pipeline-service contract pending)"`. Until that contract lands, **if the
> template declares any required field outside the reserved set, stop and tell the user
> the configured pipeline is incompatible with chat execution**. Skip the elicitation loop
> below entirely. Once the server lands custom-input support, remove this note and follow
> the loop as documented.

For every non-reserved template field, ask the user for a value via `AskUserQuestion` —
treat all such fields as required (we cannot reliably infer optionality from the template).

- Use the raw field name as the prompt label.
- One question per field — `AskUserQuestion` is single-question by design; do not batch.
- Do not attempt to parse default values from the template; always elicit fresh.

Collect responses into a `runtime_inputs` map.

**Cancellation rule.** Stop and do NOT call Step D if any of these hold:

- `AskUserQuestion` returns cancelled (no answer, user dismissed the prompt).
- The response is empty or whitespace-only.
- The response matches `cancel`, `skip`, `stop`, or `abort` (case-insensitive whole word).

Any other freeform text is a real answer — copy verbatim into the `runtime_inputs` map.
Do not proceed to Step D with a partial map.

#### Step D — Trigger the pipeline (custom-pipeline branch)

Call the consolidated dbops resource (single tool call — server triggers execution and records
the billing event atomically):

```
harness_execute(
  resource_type="database_execute_llm_authoring_pipeline",
  action="run",
  schema_id="<schema_id>",
  instance_id="<instance_id>",
  conversation_id="<conversation_id or session_id from agent context>",
  changeset="<plain-text accepted YAML>",
  pipeline_identifier="<value from Step A>",
  runtime_inputs={ <field>: <value>, ... }   # OMIT this key entirely when no fields were elicited; do NOT pass {}
)
```

**If the call returns an error or times out**, surface the exact error message verbatim and stop.
Do NOT retry automatically and do NOT fall back to the default-pipeline branch.
Do NOT fabricate navigation paths, execution status claims, or retry invitations.
The `openInHarness` link MUST only be shown when the response provides it — never construct it manually.

Skip to Step F.

---

#### Step E — Trigger the pipeline (default-pipeline branch)

```
harness_execute(
  resource_type="database_execute_llm_authoring_pipeline",
  action="run",
  schema_id="<schema_id>",
  instance_id="<instance_id>",
  conversation_id="<conversation_id or session_id from agent context>",
  changeset="<plain-text accepted YAML>",
  use_default_pipeline=true
)
```

The server performs get-or-create of `dbops_default_pipeline` on first use, then triggers the
execution. The server resolves the K8s connector for the step-group infra from the DBOPS
instance's connector — the skill sends no infra hints.

**If the call returns an error or times out**, surface the exact error message verbatim and stop.
Do NOT fabricate navigation paths, execution status claims, or retry invitations.
The `openInHarness` link MUST only be shown when the response provides it — never construct it manually.

Proceed to Step F.

---

#### Step F — Show the live execution link

Both branches return:

```
{ executionId, pipelineIdentifier, openInHarness }
```

Post immediately — **only if `openInHarness` is a non-empty string in the response**:

```
Pipeline started — <a href="{openInHarness}" target="_blank">view execution</a>
```

If `openInHarness` is absent or empty, post instead:

```
Pipeline started — execution ID: `<executionId>`.
```

**Do NOT construct the URL manually.** The link must come from the response.

**Do NOT proactively poll.** When the user asks for status, call
`harness_get(resource_type="execution", execution_id="<executionId>")` once — this hits the
same pipeline-service execution endpoint that powers the `openInHarness` link.

**Status triage:**

- **Running / Queued / Paused / Waiting** — report: "Running — step `<stepName>` is `<stepStatus>`".
- **Success** — "Changeset applied successfully" — if `openInHarness` is present, append `— <a href="{openInHarness}" target="_blank">view execution</a>`. Do NOT construct the URL manually.
- **Failed / Aborted / Expired** — read the failed step name and `failureInfo.responseMessages[0].message`.
  - If the failed step name contains `changeset`/`liquibase`/`migration` OR the message
  contains those keywords or `checksum` / `precondition` / `validation error` — this is a
  **changeset error**. Offer error recovery: enter error-recovery mode (see **Error
  Recovery Mode** section below) and regenerate a corrected changeset.
  - For any other step failure (infra, connector, K8s, networking, permissions) — report the
  error verbatim and stop. Do NOT auto-debug. Reply: "Pipeline failed at step `<stepName>`:
  `<message>` — <a href="{openInHarness}" target="_blank">view execution</a>. This is an
  infrastructure or configuration issue — please check your Harness pipeline setup."

---

## Important Rules

- Present the changeset for review in chat and always offer all three options: **Accept**, **Accept & Commit**, **Deny**.
- Always include the full YAML in the review message.
- Use the YAML the user accepted/edited — not your original generation if they changed it.
- Before any `harness_execute` for `database_execute_llm_authoring_pipeline`, resolve `conversation_id` from agent context (`conversation_id`, else `session_id`). Do not execute without it.
- For `accept_commit`, post the `openInHarness` link (if present) and stop. Do NOT proactively poll — the server reconciles status asynchronously. If the user later asks for status, call `harness_get` once as described in Step F.
- For `deny`, skip re-discovery — schema and instance are already known.
- For error recovery, explain the fix BEFORE presenting the corrected YAML.
- If the DBOPS service returns an error during schema/instance discovery, report the error clearly and suggest the user check their Harness DBOPS project setup.

## Error Recovery Mode

**Trigger:** Enter this mode ONLY for changeset/Liquibase failures:
- A `FAILED` pipeline status event resumes the conversation (automated polling path), OR
- The user asks to fix a failed migration or reports a Liquibase / checksum / precondition / OPA error

**Do NOT enter this mode for infrastructure or configuration failures** (broken connector, K8s scheduling failure, missing secret, pipeline misconfiguration, etc.). For those, report the error verbatim and reply: "Pipeline failed at step `<stepName>`: `<message>` — this is an infrastructure or configuration issue — please check your Harness pipeline setup." Do NOT attempt to regenerate the changeset.

**Do NOT re-run Steps 1–2 (schema/instance discovery).** `schema_id`, `instance_id`, and
`connector` are already resolved from the original session. Jump directly to the steps below.

### Steps

**1. Extract the failure details from context:**
- From the system event (automated path): `failed_step`, `failure_message`, `execution_id`, `open_in_harness` link.
- From the user message (manual path): the error text the user pasted or described.
If the system event provides an `execution_id` but no `failure_message`, call:
```
harness_diagnose(resource_type="execution", execution_id="<execution_id>")
```
Read the full step log from the response to get the Liquibase error text before proceeding to root-cause analysis.

**1a. Classify the failure before proceeding:**
| Failure contains | Classification | Action |
|-----------------|----------------|--------|
| `liquibase`, `changeset`, `checksum`, `precondition`, `validation`, `OPA policy`, `migration` | Changeset error | Continue to step 2 below |
| Connector error, K8s / pod failure, secret not found, network timeout, pipeline config | Infrastructure error | Report verbatim + stop. Do NOT regenerate. |
| Ambiguous | Treat as infrastructure error — do not guess at changeset root cause |

**2. Identify the root cause.**
Read `reference.md` → "Author, Update Mode, and Error Recovery" section. Common causes:
- Missing `rollback` block
- Illegal or reserved table/column name for the target engine
- Wrong data type for the target engine (e.g., `DATETIME2` vs `TIMESTAMP`)
- Duplicate `changeSet` id within the changelog
- Invalid precondition syntax or missing `onFail`
- OPA policy violation — extract the policy's error text verbatim, correct the changeset to satisfy the policy

**3. Patch the offending changeSet:**
- Fix only what the error requires. Preserve `id`, `author`, and all unaffected changeSets.
- Produce the full accumulated `databaseChangeLog` (never emit just the delta).

**4. Explain the fix in a text message BEFORE presenting the corrected YAML:**
State: what the error was, which changeSet was affected, and what was changed to fix it.

**5. Present the corrected YAML for review (Step 5)** with all three options: Accept, Accept & Commit, Deny.
