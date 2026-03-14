# Schema Validation Loop

Use this playbook for any skill that generates or updates Harness YAML or MCP payloads.

## Goal

Avoid guessed payloads by combining schema discovery with API validation feedback.

## Workflow

1. **Start with the resource type**
   - Identify the target `resource_type` and operation (`create`, `update`, `execute`).

2. **Read the schema before drafting**
   - Use `harness_describe(resource_type="...")` to inspect the expected shape.
   - Check skill-local references when a resource has specialized conventions.

3. **Draft the smallest valid payload first**
   - Prefer a minimal working payload over a large speculative one.
   - Add optional fields only when the user requested them or the schema requires them.

4. **Use API errors as structured feedback**
   - If the Harness API rejects the payload, extract the exact missing or invalid field from the error.
   - Revise the payload to address that specific error before retrying.

5. **Do not invent undocumented fields**
   - If the schema and error message still leave ambiguity, stop and clarify instead of guessing.

6. **Summarize the validated output**
   - Tell the user what was generated, which schema source guided the shape, and any remaining assumptions.

## Recommended Prompt Pattern

> I checked the schema for this resource first and drafted the minimal valid payload. The API rejected `spec.identifier`, so I added the required field and retried.

## Output Contract

After a successful create/update, include:

- schema source used
- fields that required correction during validation
- final resource identifier or artifact generated
