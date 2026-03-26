# Connector Policies

## Package: `connector`
## Root path: `input.entity` + `input.metadata`
## Valid actions: `onsave`

## Schema (common fields)

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
input.entity.spec.credential.spec.auth.type  # e.g. "UsernamePassword" for K8sCluster
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
input.metadata.userGroups[i].identifier
input.metadata.userGroups[i].name
input.metadata.projectMetadata.identifier
input.metadata.projectMetadata.name
input.metadata.projectMetadata.orgIdentifier
```

## Example 1: Restrict connector types

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

## Example 2: Deny connectors with forbidden words in the name

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

## Example 3: Restrict connector creation by role

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

## Example 4: Require connectors to use delegate execution

```rego
package connector

deny[msg] {
  input.entity.spec.executeOnDelegate == false
  msg := sprintf("Connector '%s' must use delegate execution", [input.entity.name])
}
```

## Example 5: Enforce Kubernetes auth types

**Scenario:** Restrict K8s cluster connectors to specific authentication types only.

```rego
package connector
import future.keywords.in

connectorType := "K8sCluster"
allowedAuthTypes := ["UsernamePassword"]

deny[msg] {
  cType := input.entity.type
  aType := input.entity.spec.credential.spec.auth.type
  cType == connectorType
  not aType in allowedAuthTypes
  msg := sprintf("Auth types %s are allowed for connector type %s, used '%s'", [allowedAuthTypes, cType, aType])
}
```

## Example 6: Restrict connector access by user group

**Scenario:** Only specific user groups can create K8s cluster connectors.

```rego
package connector

connectorType := "K8sCluster"
AllowedUserGroups := ["_project_all_users"]

deny[msg] {
  cType := input.entity.type
  cType == connectorType
  not has_allowed_group(input.metadata.userGroups)
  msg := sprintf("Only user groups %s are allowed for connector type %s", [AllowedUserGroups, cType])
}

has_allowed_group(userGroups) {
  identifier := userGroups[_].identifier
  AllowedUserGroups[_] = identifier
}
```

## Example 7: Enforce connector naming convention

**Scenario:** Connector names must follow a "Team - Account" naming convention.

```rego
package connector

deny[msg] {
  not regex.match("[Cheetah|Tiger|Lion]\\s[-]\\s[a-zA-Z0-9\\s]+", input.entity.name)
  msg := sprintf("Connector name '%s' must follow the correct naming convention 'Team - Account'", [input.entity.name])
}
```

## Sample JSON

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
