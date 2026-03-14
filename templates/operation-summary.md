# Operation Summary Template

Use this template for skills that create, update, debug, or analyze Harness resources and need a consistent final response.

```md
## Summary
- Operation: <create | update | debug | analyze>
- Resource type: <pipeline | connector | secret | ...>
- Scope: <account/org/project>

## What I confirmed
- Scope: <org/project or account-level context>
- Dependencies: <verified resources or "none">
- Schema/source of truth: <harness_describe, reference doc, existing resource, etc.>

## What changed
- Created/updated/analyzed: <resource identifiers or generated artifacts>
- Key fields or behaviors: <important configuration choices>

## Risks or follow-ups
- <missing dependency, rollout caveat, access concern, or "none">

## Recommended next step
- <run pipeline, attach trigger, validate connector, review RBAC blast radius, etc.>
```

## Notes

- Keep the summary short and operational.
- Do not repeat the entire YAML or payload unless the user asked for it.
- If the operation failed, replace `What changed` with `What blocked completion`.
