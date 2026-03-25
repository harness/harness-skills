# Harness OPA Rego Policy Writing Guide

## Workflow

1. **Identify the entity type** the policy targets. Ask the user if unclear.
2. **Identify the action** (onSave, onRun, onStep, etc.). Ask the user if unclear.
3. **Read the matching entity schema** from the reference files to understand the payload structure.
4. **Read relevant example policies** from the reference files to match the pattern.
5. **Write the policy** following the Rego rules below.

## Entity Types and Valid Actions

| Entity Type | Package Name | Root Input Path | Valid Actions |
|---|---|---|---|
| pipeline | `pipeline` | `input.pipeline` | onrun, onsave, onstepstart |
| template | `template` | `input.template` | onsave |
| service | `service` | `input.serviceEntity` | onsave, onrun |
| environment | `environment` or `env` | `input.environmentEntity` | onsave, onrun |
| infrastructure | `infra` | `input.infrastructureEntity` | onsave, onrun |
| featureFlag | `fme_feature_flags` | `input.featureFlag` + `input.entityMetadata` | onsave |
| featureFlagDefinition | `fme_feature_flags` | `input.featureFlagDefinition` + `input.entityMetadata` | onsave |
| fmeEnvironment | `fme_environment` | `input.fmeEnvironment` + `input.entityMetadata` | onsave |
| fmeSegment | `fme_segment` | `input.fmeSegment` + `input.entityMetadata` | onsave |
| flag (legacy FF) | `flag` | `input.flag` | onsave |
| connector | `connector` | `input.connectorEntity` | onsave |
| secret | `secret` | `input.secretEntity` | onsave |
| variable | `variable` | `input.variable` + `input.metadata` | onsave |
| override | `override` | `input.overrideEntity` | onsave |
| securityTests | `securityTests` | `input[i]` (array of outputs) | onstep |
| sbom | `sbom` | `input` (array of packages) | onstep |
| terraformPlan | `terraform_plan` | `input.planned_values`, `input.resource_changes` | afterTerraformPlan |
| terraformPlanCost | `terraform_plan_cost` | `input.TotalMonthlyCost`, etc. | afterTerraformPlan |
| terraformState | `terraform_state` | `input.resources` | afterTerraformPlan, afterTerraformApply |
| workspace | `workspace` | `input.workspace` | onsave |
| gitopsApplication | `gitopsApplication` | `input.gitopsApplication` | onsave, onsync |
| upstreamProxy | `firewall` | `input` (array of packages) | onEvaluation |

## Metadata Object

Every evaluation includes `input.metadata` (or `metadata` at root level) with:

```json
{
  "metadata": {
    "type": "pipeline",
    "action": "onrun",
    "timestamp": 1651585226,
    "principalIdentifier": "user-id",
    "principalType": "USER",
    "user": { "name": "...", "email": "...", "uuid": "..." },
    "userGroups": [{ "identifier": "...", "name": "...", "users": [...] }],
    "roleAssignmentMetadata": [{
      "roleIdentifier": "_account_admin",
      "roleName": "Account Admin",
      "resourceGroupIdentifier": "...",
      "resourceGroupName": "..."
    }],
    "projectMetadata": { "identifier": "...", "name": "...", "orgIdentifier": "..." }
  }
}
```

Use metadata for: user/role-based restrictions, time-based policies, action-aware behavior.

## Rego Writing Rules

### Structure
- Always declare `package <name>` as the first line.
- Use `deny[msg]` for enforced rules (block the action). Use `warn[msg]` for advisory rules.
- Each `deny` rule should produce a human-readable `msg` via `sprintf` or direct string assignment.
- Prefer `msg := "direct string"` over `sprintf` when no interpolation is needed.

### Field Access
- Always use `input.` prefix to access the payload. Fields are accessed with dot notation: `input.pipeline.stages[i].stage.type`.
- Use `[_]` for wildcard iteration: `input.pipeline.stages[_].stage`.
- Use `[i]` when you need to reference the index elsewhere.
- Assign intermediate variables for readability: `stage = input.pipeline.stages[_].stage`.

### Pipeline Step Nesting (CRITICAL)

Pipeline steps can be nested arbitrarily deep. Each execution slot is exactly **one of**: `step`, `stepGroup`, `parallel`, or `insert`. Step groups contain their own `steps[]` array, so nesting is **recursive**.

**Always use `walk()` to find steps at any depth** — otherwise policies miss steps inside step groups, parallel blocks, or inserts:

```rego
deny[msg] {
  [_, step] = walk(input.pipeline)
  step.type == "HarnessApproval"
  step.spec.approvers.disallowPipelineExecutor != true
  msg := sprintf("approval step '%s' must set disallowPipelineExecutor", [step.name])
}
```

Similarly, stages can be sequential or parallel:

```rego
all_stages[stage] { stage := input.pipeline.stages[_].stage }
all_stages[stage] { stage := input.pipeline.stages[_].parallel[_].stage }
```

### Common Patterns

**Require a step type exists (walk-based):**
```rego
deny[msg] {
  stage := all_stages[_]
  stage.type == "Deployment"
  not stage_has_step_type(stage, "HarnessApproval")
  msg := sprintf("stage '%s' missing required step", [stage.name])
}
all_stages[stage] { stage := input.pipeline.stages[_].stage }
all_stages[stage] { stage := input.pipeline.stages[_].parallel[_].stage }
stage_has_step_type(stage, t) { [_, v] = walk(stage.spec.execution); v.type == t }
```

**Forbid a step type (walk-based):**
```rego
deny[msg] {
  stage := all_stages[_]
  stage.type == "Deployment"
  [_, step] = walk(stage.spec.execution)
  step.type == "ShellScript"
  msg := sprintf("stage '%s' has forbidden step '%s'", [stage.name, step.name])
}
all_stages[stage] { stage := input.pipeline.stages[_].stage }
all_stages[stage] { stage := input.pipeline.stages[_].parallel[_].stage }
```

**Check membership in a list:**
```rego
allowed_environments = ["prod", "staging"]
deny[msg] {
  stage := all_stages[_]
  stage.type == "Deployment"
  env := stage.spec.infrastructure.environment.identifier
  not array_contains(allowed_environments, env)
  msg := sprintf("environment '%s' not allowed", [env])
}
array_contains(arr, elem) { arr[_] = elem }
```

**Role-based restriction:**
```rego
deny[msg] {
  some i
  input.metadata.roleAssignmentMetadata[i].roleIdentifier == "_project_viewer"
  msg := "viewers cannot perform this action"
}
```

**Pipeline exemption by org/project/pipeline:**
```rego
exempted_pipelines = [
  {"org": "default", "project": "prod", "pipeline": "emergency_deploy"},
]
is_pipeline_exempt {
  pipeline = input.pipeline
  orgs = [elem | some elem in exempted_pipelines; elem.org == pipeline.orgIdentifier]
  prjs = [elem | some elem in orgs; elem.project == pipeline.projectIdentifier]
  pipes = [elem.pipeline | some elem in prjs]
  array_contains(pipes, pipeline.identifier)
}
```

### Things to Avoid
- Do NOT use `not` to negate an expression with an unbounded variable (`_`). Instead, create a helper rule and negate that.
- Do NOT use `sprintf` when a plain string suffices.
- Do NOT use `allow` rules unless explicitly required (SBOM allow-lists are the exception). Harness OPA uses `deny` semantics.
- Do NOT import `future.keywords` unless using `if`, `in`, `every`, or `contains` keywords. Simple policies don't need them.
- Do NOT define `contains()` as a helper if you can use the `in` keyword with `import future.keywords.in`.
- Do NOT use deprecated OPA builtins: `any()`, `all()`, `re_match()`, `set_diff()`, `cast_*()`.

## Quality Checklist

Before returning a policy, verify:

- [ ] `package` declaration matches entity type convention
- [ ] All field paths exist in the entity's JSON schema
- [ ] `deny[msg]` (not `deny[msg] =`) syntax is correct
- [ ] `msg` is human-readable and includes relevant identifiers
- [ ] No unbounded `_` inside `not` expressions
- [ ] Helper functions like `contains()` are defined if used
- [ ] Policy handles edge cases (missing fields, empty arrays)
- [ ] **For pipeline step policies:** Uses `walk()` or covers all nesting levels (step groups, parallel blocks, insert nodes) — NOT just `steps[_].step`
- [ ] **For pipeline stage policies:** Handles both sequential (`stages[_].stage`) and parallel (`stages[_].parallel[_].stage`) stages
- [ ] **For pipeline step policies:** Consider whether rollback steps (`rollbackSteps[]`) should also be checked
