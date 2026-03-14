# Dependency Check Playbook

Use this playbook when a resource references other Harness resources.

## Goal

Verify upstream resources exist before generating YAML or making API calls for dependent resources.

## Common Dependency Chains

- Pipeline -> service, environment, infrastructure, connector, template, secret
- Service -> connector, secret
- Infrastructure -> connector, environment
- Trigger -> pipeline, connector
- Role assignment -> user group, role, resource group

## Workflow

1. **List the referenced resources**
   - Write down every identifier the new resource depends on.

2. **Check existence before create/update**
   - Use `harness_list` or `harness_get` to confirm referenced resources exist in the intended scope.

3. **Detect scope mismatches**
   - A referenced resource may exist at account or org scope while the new resource is project-scoped.
   - Surface that mismatch explicitly if it affects visibility or reuse.

4. **Stop on missing dependencies**
   - Do not fabricate identifiers.
   - If a dependency is missing, either:
     - route the user to the prerequisite skill, or
     - create the prerequisite first if that is already in scope for the request.

5. **Summarize the verified dependency graph**
   - Before generating the final resource, show which dependencies were confirmed and which still need action.

## Recommended Prompt Pattern

> Before I create the pipeline, I need to confirm its dependencies. I found the environment and service, but I still need the infrastructure definition identifier.

For choice-heavy workflows, recommend a path:

> Recommend reusing the existing Docker connector to keep credentials centralized.  
> A) Reuse existing connector  
> B) Create a new connector  
> C) Stop and inspect current setup first

## Output Contract

Include a short dependency summary:

- confirmed resources
- missing resources
- next required action
