# Quality Test Cases

Use these hold-out test cases to evaluate AI-generated policy quality. For each test case:
1. Give the AI only the **prompt** (not the expected output).
2. Compare the generated policy against the **expected policy**.
3. Score using the checklist at the bottom.

---

## Test 1: Pipeline — Require Chaos Step

**Prompt:** "Write a policy that ensures all deployment stages have a Chaos step with an experimentRef."

**Expected entity:** pipeline
**Expected action:** onrun or onsave

**Expected policy (reference):**
```rego
package pipeline

deny[msg] {
  stage = input.pipeline.stages[_].stage
  stage.type == "Deployment"
  not has_chaos_step(stage)
  msg := sprintf("deployment stage '%s' must have a Chaos step", [stage.name])
}

has_chaos_step(stage) {
  step = stage.spec.execution.steps[_].step
  step.type == "Chaos"
  step.spec.experimentRef
}
```

**Validation input (should PASS):**
```json
{"pipeline":{"stages":[{"stage":{"name":"deploy","type":"Deployment","spec":{"execution":{"steps":[{"step":{"type":"Chaos","spec":{"experimentRef":"exp-123"}}}]}}}}]}}
```

**Validation input (should DENY):**
```json
{"pipeline":{"stages":[{"stage":{"name":"deploy","type":"Deployment","spec":{"execution":{"steps":[{"step":{"type":"K8sRollingDeploy","spec":{}}}]}}}}]}}
```

---

## Test 2: Feature Flag — Require Description

**Prompt:** "Write a policy that denies feature flags without a description."

**Expected entity:** featureFlag
**Expected action:** onsave

**Expected policy:**
```rego
package fme_feature_flags

deny[msg] {
  input.featureFlag.description == ""
  msg := sprintf("Feature flag '%s' must have a description", [input.featureFlag.name])
}

deny[msg] {
  not input.featureFlag.description
  msg := sprintf("Feature flag '%s' must have a description", [input.featureFlag.name])
}
```

---

## Test 3: GitOps — Enforce Sync Options

**Prompt:** "Write a policy that requires GitOps applications to have Validate=true in syncOptions."

**Expected entity:** gitopsApplication
**Expected action:** onsave

**Expected policy:**
```rego
package gitopsApplication

deny[msg] {
  app := input.gitopsApplication
  not has_sync_option("Validate=true")
  msg := sprintf("Application '%s' must have 'Validate=true' in syncOptions", [app.name])
}

has_sync_option(opt) {
  input.gitopsApplication.app.spec.syncPolicy.syncOptions[_] == opt
}
```

---

## Test 4: Terraform — Block Resource Deletion

**Prompt:** "Write a policy that prevents deleting any aws_s3_bucket resources in a Terraform plan."

**Expected entity:** terraformPlan
**Expected action:** afterTerraformPlan

**Expected policy:**
```rego
package terraform_plan

deny[msg] {
  rc = input.resource_changes[_]
  rc.type == "aws_s3_bucket"
  rc.change.actions[_] == "delete"
  msg := sprintf("Deleting S3 bucket '%s' is not allowed", [rc.address])
}
```

---

## Test 5: Service — Require Variables Have Descriptions

**Prompt:** "Write a policy that ensures all service variables have non-empty descriptions."

**Expected entity:** service
**Expected action:** onsave

**Expected policy:**
```rego
package service

deny[msg] {
  var := input.serviceEntity.serviceDefinition.spec.variables[_]
  var.description == ""
  msg := sprintf("Service variable '%s' must have a description", [var.name])
}

deny[msg] {
  var := input.serviceEntity.serviceDefinition.spec.variables[_]
  not var.description
  msg := sprintf("Service variable '%s' must have a description", [var.name])
}
```

---

## Test 6: SBOM — Block Log4j

**Prompt:** "Write a policy that blocks any SBOM component matching log4j regardless of version."

**Expected entity:** sbom
**Expected action:** onstep

**Expected policy:**
```rego
package sbom

deny[msg] {
  pkg := input[_]
  regex.match(".*log4j.*", pkg.packageName)
  msg := sprintf("Package '%s' (version %s) matches blocked pattern 'log4j'", [pkg.packageName, pkg.packageVersion])
}
```

---

## Test 7: Environment — Production Naming Convention

**Prompt:** "Write a policy that requires production environments to have names starting with 'prod-'."

**Expected entity:** environment
**Expected action:** onsave

**Expected policy:**
```rego
package env

deny[msg] {
  input.environmentEntity.type == "Production"
  not startswith(input.environmentEntity.name, "prod-")
  msg := sprintf("Production environment '%s' must have name starting with 'prod-'", [input.environmentEntity.name])
}
```

---

## Test 8: Pipeline — User Group Restriction

**Prompt:** "Write a policy that only allows users in the 'platform-admins' user group to run pipelines targeting production environments."

**Expected entity:** pipeline
**Expected action:** onrun

**Expected policy:**
```rego
package pipeline

deny[msg] {
  stage = input.pipeline.stages[_].stage
  stage.type == "Deployment"
  stage.spec.infrastructure.environment.type == "Production"
  not user_in_group("platform-admins")
  msg := sprintf("Only platform-admins can run deployments to production (stage '%s')", [stage.name])
}

user_in_group(group_name) {
  group = input.metadata.userGroups[_]
  group.identifier == group_name
  group.users[_] == input.metadata.user.uuid
}
```

---

## Scoring Checklist

For each generated policy, score 1 point per criterion:

| # | Criterion | Weight |
|---|-----------|--------|
| 1 | Correct `package` name for entity type | 1 |
| 2 | Compiles without errors (valid Rego syntax) | 2 |
| 3 | Uses correct `input.*` field paths matching the entity schema | 2 |
| 4 | Uses `deny[msg]` (not `deny[msg] =` or `allow`) | 1 |
| 5 | Produces human-readable error messages | 1 |
| 6 | Handles edge cases (missing fields, empty arrays) | 1 |
| 7 | No unbounded `_` inside `not` expressions | 1 |
| 8 | Deny fires on bad input (true positive) | 2 |
| 9 | Deny does NOT fire on good input (no false positive) | 2 |
| 10 | No unnecessary complexity (no unused imports, helpers) | 1 |

**Total: 14 points. Target: >= 12 for production-quality output.**
