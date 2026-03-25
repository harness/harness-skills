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
### Root path: `input.entity` + `input.metadata`
### Valid actions: `onsave`

### Schema (common fields)

```
input.entity.identifier
input.entity.name
input.entity.orgIdentifier
input.entity.projectIdentifier
input.entity.type                            # "K8sCluster", "Git", "Github", "DockerRegistry", "Aws", "Gcp", etc.
input.entity.description
input.entity.tags                            # object {}
input.entity.spec                            # type-specific fields
input.entity.spec.credential.type            # e.g. "ManualConfig" for Aws
input.entity.spec.credential.region          # e.g. "ap-south-2" for Aws
input.entity.spec.executeOnDelegate          # boolean
input.entity.spec.proxy                      # boolean

input.metadata.action                        # "onsave"
input.metadata.type                          # "connector"
input.metadata.timestamp                     # unix timestamp
input.metadata.principalIdentifier           # user ID
input.metadata.principalType                 # "USER"
input.metadata.user.name
input.metadata.user.email
input.metadata.roleAssignmentMetadata[i].roleIdentifier    # "_project_admin", "_account_admin", etc.
input.metadata.roleAssignmentMetadata[i].roleName
input.metadata.roleAssignmentMetadata[i].roleScopeLevel    # "project", "organization", "account"
input.metadata.projectMetadata.identifier
input.metadata.projectMetadata.name
input.metadata.projectMetadata.orgIdentifier
```

### Example 1: Restrict connector types

```rego
package connector

allowed_types = ["K8sCluster", "Git", "DockerRegistry"]

deny[msg] {
  not array_contains(allowed_types, input.entity.type)
  msg := sprintf("Connector type '%s' is not allowed", [input.entity.type])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

### Example 2: Deny connectors with forbidden words in the name

```rego
package connector

forbidden_words = ["test", "temp", "dummy"]

deny[msg] {
  name := lower(input.entity.name)
  word := forbidden_words[_]
  contains(name, word)
  msg := sprintf("Connector '%s' is not allowed because it contains the forbidden word '%s'", [input.entity.name, word])
}
```

### Example 3: Restrict connector creation by role

```rego
package connector

deny[msg] {
  input.entity.type == "Aws"
  not has_admin_role
  msg := sprintf("Only admins can create AWS connectors. Connector: '%s'", [input.entity.name])
}

has_admin_role {
  some i
  input.metadata.roleAssignmentMetadata[i].roleIdentifier == "_account_admin"
}
```

### Example 4: Require connectors to use delegate execution

```rego
package connector

deny[msg] {
  input.entity.spec.executeOnDelegate == false
  msg := sprintf("Connector '%s' must use delegate execution", [input.entity.name])
}
```

### Sample JSON

```json
{
  "entity": {
    "description": "",
    "identifier": "awsprod",
    "name": "aws-prod",
    "orgIdentifier": "abhijittestorg",
    "projectIdentifier": "abhijitCRDProject",
    "spec": {
      "awsSdkClientBackOffStrategyOverride": {
        "spec": { "fixedBackoff": 0, "retryCount": 0 },
        "type": "FixedDelayBackoffStrategy"
      },
      "credential": {
        "region": "ap-south-2",
        "spec": {
          "accessKey": "blah",
          "secretKeyRef": "account.CI_AWS_KKKKKK",
          "sessionTokenRef": "account.CI_AWS_KKKKKK"
        },
        "type": "ManualConfig"
      },
      "executeOnDelegate": false,
      "ignoreTestConnection": false,
      "proxy": false
    },
    "tags": {},
    "type": "Aws"
  },
  "metadata": {
    "action": "onsave",
    "principalIdentifier": "1PSO8LO2Svud3biXkMGOlA",
    "principalType": "USER",
    "projectMetadata": {
      "description": "",
      "identifier": "abhijitCRDProject",
      "modules": ["CD", "CI", "CV", "CF", "CE", "STO", "CHAOS", "SRM", "IACM", "CET", "IDP", "CODE", "SSCA"],
      "name": "abhijitCRDProject",
      "orgIdentifier": "abhijittestorg",
      "tags": {}
    },
    "roleAssignmentMetadata": [
      {
        "identifier": "role_assignment_ornacoGX5gRQzdmpGvQn",
        "managedRole": true,
        "resourceGroupIdentifier": "_all_project_level_resources",
        "resourceGroupName": "All Project Level Resources",
        "roleIdentifier": "_project_admin",
        "roleName": "Project Admin",
        "roleScopeLevel": "project"
      },
      {
        "identifier": "role_assignment_9DGgbMEYB8XEJmHzhwXL",
        "managedRole": true,
        "resourceGroupIdentifier": "_all_resources_including_child_scopes",
        "resourceGroupName": "All Resources Including Child Scopes",
        "roleIdentifier": "_account_admin",
        "roleName": "Account Admin",
        "roleScopeLevel": "account"
      }
    ],
    "timestamp": 1774285364,
    "type": "connector",
    "user": {
      "email": "abhijit.pujare@harness.io",
      "name": "Abhijit Pujare"
    }
  }
}
```

---

## Secret

### Package: `secret`
### Root path: `input.secret` + `input.metadata`
### Valid actions: `onsave`

### Schema (common fields)

```
input.secret.identifier
input.secret.name
input.secret.orgIdentifier
input.secret.projectIdentifier
input.secret.type                            # "SecretText", "SecretFile", "SSHKey", "WinRmCredentials"
input.secret.description
input.secret.tags                            # object {}
input.secret.spec                            # type-specific fields
input.secret.spec.auth.type                  # e.g. "NTLM" for WinRmCredentials
input.secret.spec.port                       # e.g. 5986 for WinRm

input.metadata.action                        # "onsave"
input.metadata.type                          # "secret"
input.metadata.timestamp                     # unix timestamp
input.metadata.principalIdentifier           # user ID
input.metadata.principalType                 # "USER"
input.metadata.user.name
input.metadata.user.email
input.metadata.roleAssignmentMetadata[i].roleIdentifier    # "_project_admin", "_account_admin", etc.
input.metadata.roleAssignmentMetadata[i].roleName
input.metadata.roleAssignmentMetadata[i].roleScopeLevel    # "project", "organization", "account"
input.metadata.projectMetadata.identifier
input.metadata.projectMetadata.name
input.metadata.projectMetadata.orgIdentifier
```

### Example 1: Require secret descriptions

```rego
package secret

deny[msg] {
  input.secret.description == ""
  msg := sprintf("Secret '%s' must have a description", [input.secret.name])
}

deny[msg] {
  not input.secret.description
  msg := sprintf("Secret '%s' must have a description", [input.secret.name])
}
```

### Example 2: Enforce secret naming conventions

```rego
package secret

forbidden_prefix = "secret"

deny[msg] {
  startswith(lower(input.secret.name), lower(forbidden_prefix))
  msg := sprintf("Secret '%s' name must not begin with '%s'", [input.secret.name, forbidden_prefix])
}
```

### Example 3: Enforce approved secret types

```rego
package secret

allowed_types = ["SecretText", "SecretFile"]

deny[msg] {
  not array_contains(allowed_types, input.secret.type)
  msg := sprintf("Secret '%s' uses disallowed type '%s'. Allowed: %v", [input.secret.name, input.secret.type, allowed_types])
}

array_contains(arr, elem) {
  arr[_] = elem
}
```

### Example 4: Restrict secret creation by role

```rego
package secret

deny[msg] {
  input.secret.type == "WinRmCredentials"
  not has_admin_role
  msg := sprintf("Only admins can create WinRm secrets. Secret: '%s'", [input.secret.name])
}

has_admin_role {
  some i
  input.metadata.roleAssignmentMetadata[i].roleIdentifier == "_account_admin"
}
```

### Sample JSON

```json
{
  "metadata": {
    "action": "onsave",
    "principalIdentifier": "1PSO8LO2Svud3biXkMGOlA",
    "principalType": "USER",
    "projectMetadata": {
      "description": "",
      "identifier": "abhijitCRDProject",
      "modules": ["CD", "CI", "CV", "CF", "CE", "STO", "CHAOS", "SRM", "IACM", "CET", "IDP", "CODE", "SSCA"],
      "name": "abhijitCRDProject",
      "orgIdentifier": "abhijittestorg",
      "tags": {}
    },
    "roleAssignmentMetadata": [
      {
        "roleIdentifier": "_project_admin",
        "roleName": "Project Admin",
        "roleScopeLevel": "project"
      },
      {
        "roleIdentifier": "_account_admin",
        "roleName": "Account Admin",
        "roleScopeLevel": "account"
      }
    ],
    "timestamp": 1774292341,
    "type": "secret",
    "user": {
      "email": "abhijit.pujare@harness.io",
      "name": "Abhijit Pujare"
    }
  },
  "secret": {
    "description": "",
    "identifier": "applerm",
    "name": "apple-rm-2",
    "orgIdentifier": "abhijittestorg",
    "projectIdentifier": "abhijitCRDProject",
    "spec": {
      "auth": {
        "spec": {
          "domain": "blah",
          "password": "account.CI_AWS_KKKKKK",
          "skipCertChecks": false,
          "useNoProfile": false,
          "useSSL": true,
          "username": "blah"
        },
        "type": "NTLM"
      },
      "parameters": [],
      "port": 5986
    },
    "tags": {},
    "type": "WinRmCredentials"
  }
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
