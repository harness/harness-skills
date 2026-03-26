# Template Policies

## Package: `template`
## Root path: `input.template`
## Valid actions: `onsave`

## Schema

```
input.template.identifier
input.template.name
input.template.type                          # "Stage", "Step", "Pipeline", "StepGroup", "SecretManager", "ArtifactSource", "MonitoredService", "CustomDeployment"
input.template.versionLabel                  # e.g. "1.0.0", "v2.1.3"
input.template.description
input.template.tags                          # object {}
input.template.orgIdentifier
input.template.projectIdentifier
input.template.childType                     # for Step templates: the step type, e.g. "ShellScript", "Http"
input.template.spec.stages[i].stage         # same structure as pipeline stages (for Stage/Pipeline templates)
input.template.spec.stages[i].stage.type
input.template.spec.stages[i].stage.spec.execution.steps[j].step.type
input.template.spec.stages[i].stage.spec.infrastructure.environment.identifier
input.template.spec.stages[i].stage.spec.environment.environmentRef
input.template.spec.stages[i].stage.spec.environment.infrastructureDefinitions[i].identifier
```

## Example 1: Require approval steps in deployment templates

```rego
package template

deny[msg] {
  input.template.spec.stages[i].stage.type == "Deployment"
  not stages_with_approval[i]
  msg := sprintf("deployment stage '%s' does not have a HarnessApproval step", [input.template.spec.stages[i].stage.name])
}

stages_with_approval[i] {
  input.template.spec.stages[i].stage.spec.execution.steps[_].step.type == "HarnessApproval"
}
```

## Example 2: Enforce semantic versioning on template versions

```rego
package template

version_format = "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$"

deny[msg] {
  template_version = input.template.versionLabel
  not regex.match(version_format, template_version)
  msg := sprintf("Template version '%s' must follow semantic versioning (e.g., 1.0.0)", [template_version])
}
```

## Example 3: Restrict template types

```rego
package template

allowed_types = ["Stage", "Step", "Pipeline"]

deny[msg] {
  not array_contains(allowed_types, input.template.type)
  msg := sprintf("Template type '%s' is not allowed", [input.template.type])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

## Example 4: Restrict template stages to allowed environments

**Scenario:** Deployment stages in stage/pipeline templates can only target specific environments.

```rego
package template

deny[msg] {
  stage = input.template.spec.stages[_].stage
  stage.type == "Deployment"
  not contains(allowed_environments, stage.spec.environment.infrastructureDefinitions[i].identifier)
  msg := sprintf("deployment stage cannot be deployed to infrastructure '%s'", [stage.spec.environment.infrastructureDefinitions[i].identifier])
}

deny[msg] {
  stage = input.template.spec.stages[_].stage
  stage.type == "Deployment"
  not stage.spec.environment.environmentRef
  msg := sprintf("deployment stage '%s' has no environment identifier", [stage.name])
}

allowed_environments = ["prod", "stage"]

contains(arr, elem) {
  arr[_] = elem
}
```
