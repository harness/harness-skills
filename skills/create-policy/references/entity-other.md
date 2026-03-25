# Variable, Override, Connector, and Other Entity Policies

---

## Variable

### Package: `variable`
### Root path: `input.variable` + `input.metadata`
### Valid actions: `onsave`

### Schema

```
input.variable.identifier
input.variable.name
input.variable.type                          # "string"
input.variable.value

input.metadata.action
input.metadata.timestamp
input.metadata.user.name
input.metadata.user.email
input.metadata.roleAssignmentMetadata[i].roleIdentifier   # "_account_viewer", "_account_admin", "_project_viewer"
input.metadata.roleAssignmentMetadata[i].roleName
input.metadata.roleAssignmentMetadata[i].resourceGroupIdentifier
input.metadata.userGroups[i].identifier
input.metadata.userGroups[i].name
```

### Example: Role-based variable edit restriction

**Scenario:** Deny creating/editing variables starting with "demo" if user has `_project_viewer` role.

```rego
package variable

deny[msg] {
  startswith(input.variable.name, "demo")
  some i
  input.metadata.roleAssignmentMetadata[i].roleIdentifier == "_project_viewer"
  msg := "Variable with name starting with 'demo' is not allowed when role '_project_viewer' is present"
}
```

### Sample JSON

```json
{
  "variable": {
    "identifier": "demo",
    "name": "demo",
    "type": "string",
    "value": "demo-value"
  },
  "metadata": {
    "action": "onsave",
    "user": { "name": "Cassie Cook", "email": "cassiecook@harness.io" },
    "roleAssignmentMetadata": [
      { "roleIdentifier": "_account_viewer", "roleName": "Account Viewer" },
      { "roleIdentifier": "_account_admin", "roleName": "Account Admin" }
    ]
  }
}
```

---

## Override

### Package: `override`
### Root path: `input.overrideEntity`
### Valid actions: `onsave`

### Schema

```
input.overrideEntity.identifier
input.overrideEntity.name
input.overrideEntity.orgIdentifier
input.overrideEntity.projectIdentifier
input.overrideEntity.environmentRef
input.overrideEntity.serviceRef
input.overrideEntity.infraIdentifier
input.overrideEntity.type                                    # "ENV_GLOBAL_OVERRIDE", "ENV_SERVICE_OVERRIDE"

input.overrideEntity.configFiles[i].configFile.identifier
input.overrideEntity.configFiles[i].configFile.spec.store.type           # "Git", "Github", "Harness"
input.overrideEntity.configFiles[i].configFile.spec.store.spec.branch

input.overrideEntity.variables[i].name
input.overrideEntity.variables[i].type                       # "String"
input.overrideEntity.variables[i].value

input.overrideEntity.manifests[i].manifest.identifier
input.overrideEntity.manifests[i].manifest.type              # "Values"
input.overrideEntity.manifests[i].manifest.spec.store.type
```

### Example 1: Deny GitHub config file overrides

```rego
package override

deny[msg] {
  input.overrideEntity.configFiles[_].configFile.spec.store.type == "Github"
  msg := "Cannot override config files to fetch from Github"
}
```

### Example 2: Deny non-main branch config files

```rego
package override

deny[msg] {
  input.overrideEntity.configFiles[_].configFile.spec.store.spec.branch != "main"
  msg := "Cannot override config files to fetch from non main branch"
}
```

### Example 3: Deny overriding specific variables

```rego
package override

protected_variables = ["DB_PASSWORD", "API_KEY", "SECRET_TOKEN"]

deny[msg] {
  var := input.overrideEntity.variables[_]
  contains(protected_variables, var.name)
  msg := sprintf("Cannot override protected variable '%s'", [var.name])
}

contains(arr, elem) {
  arr[_] = elem
}
```

---

## Connector

### Package: `connector`
### Root path: `input.connectorEntity`
### Valid actions: `onsave`

### Schema (common fields)

```
input.connectorEntity.identifier
input.connectorEntity.name
input.connectorEntity.orgIdentifier
input.connectorEntity.projectIdentifier
input.connectorEntity.type                   # "K8sCluster", "Git", "Github", "DockerRegistry", "Aws", "Gcp", etc.
input.connectorEntity.description
input.connectorEntity.tags
input.connectorEntity.spec                   # type-specific fields
```

### Example: Restrict connector types

```rego
package connector

allowed_types = ["K8sCluster", "Git", "DockerRegistry"]

deny[msg] {
  not contains(allowed_types, input.connectorEntity.type)
  msg := sprintf("Connector type '%s' is not allowed", [input.connectorEntity.type])
}

contains(arr, elem) {
  arr[_] = elem
}
```

---

## Secret

### Package: `secret`
### Root path: `input.secretEntity`
### Valid actions: `onsave`

### Schema (common fields)

```
input.secretEntity.identifier
input.secretEntity.name
input.secretEntity.orgIdentifier
input.secretEntity.projectIdentifier
input.secretEntity.type                      # "SecretText", "SecretFile", "SSHKey"
input.secretEntity.description
input.secretEntity.tags                      # object {}
input.secretEntity.spec.secretManagerIdentifier
```

**NOTE:** Some deployments use `input.secret` instead of `input.secretEntity` as the root path. Check your actual input payload. The community examples use `input.secret`.

### Example 1: Require secret descriptions

```rego
package secret

deny[msg] {
  input.secretEntity.description == ""
  msg := sprintf("Secret '%s' must have a description", [input.secretEntity.name])
}

deny[msg] {
  not input.secretEntity.description
  msg := sprintf("Secret '%s' must have a description", [input.secretEntity.name])
}
```

### Example 2: Enforce secret naming conventions

```rego
package secret

forbidden_prefix = "secret"

deny[msg] {
  startswith(lower(input.secretEntity.name), lower(forbidden_prefix))
  msg := sprintf("Secret '%s' name must not begin with '%s'", [input.secretEntity.name, forbidden_prefix])
}
```

### Example 3: Enforce approved secret managers

```rego
package secret

approved_secret_managers := ["harnessSecretManager", "vault_prod"]

deny[msg] {
  sm := input.secretEntity.spec.secretManagerIdentifier
  not array_contains(approved_secret_managers, sm)
  msg := sprintf("Secret '%s' uses unapproved Secret Manager '%s'. Approved: [%s]",
    [input.secretEntity.name, sm, concat(", ", approved_secret_managers)])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

---

## Template

### Package: `template`
### Root path: `input.template`
### Valid actions: `onsave`

### Schema

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
```

### Example 1: Require approval steps in deployment templates

```rego
package template

deny[msg] {
  stage = input.template.spec.stages[_].stage
  stage.type == "Deployment"
  not has_approval(stage)
  msg := sprintf("template deployment stage '%s' must have an approval step", [stage.name])
}

has_approval(stage) {
  stage.spec.execution.steps[_].step.type == "HarnessApproval"
}
```

### Example 2: Enforce semantic versioning on template versions

```rego
package template

version_format = "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)$"

deny[msg] {
  template_version = input.template.versionLabel
  not regex.match(version_format, template_version)
  msg := sprintf("Template version '%s' must follow semantic versioning (e.g., 1.0.0)", [template_version])
}
```

### Example 3: Restrict template types

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
