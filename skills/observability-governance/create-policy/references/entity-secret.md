# Secret Policies

## Package: `secret`
## Root path: `input.secret` + `input.metadata`
## Valid actions: `onsave`

## Schema (common fields)

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
input.secret.spec.secretManagerIdentifier    # e.g. "harnessSecretManager"

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

## Example 1: Require secret descriptions

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

## Example 2: Enforce secret naming conventions

```rego
package secret

forbidden_prefix = "secret"

deny[msg] {
  startswith(lower(input.secret.name), lower(forbidden_prefix))
  msg := sprintf("Secret '%s' name must not begin with '%s'", [input.secret.name, forbidden_prefix])
}
```

## Example 3: Enforce approved secret types

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

## Example 4: Restrict secret creation by role

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

## Example 5: Restrict secret creation by principal

**Scenario:** Only specific principals (users) are allowed to create or update secrets.

```rego
package secret
import future.keywords.in

allowedPrincipals = ["1234abcd"]

deny["Principal is not allowed to save secrets"] {
  not input.metadata.principalIdentifier in allowedPrincipals
}
```

## Example 6: Enforce secret naming convention with regex

**Scenario:** Secret names must follow a "Team - Purpose" pattern.

```rego
package secret

deny[msg] {
  not regex.match("[Cheetah|Tiger|Lion]\\s[-]\\s[a-zA-Z0-9\\s]+", input.secret.name)
  msg := sprintf("Secret name '%s' must follow the correct naming convention 'Team - Purpose'", [input.secret.name])
}
```

## Example 7: Restrict secrets manager providers

**Scenario:** Only approved secret manager providers can be used for storing secrets.

```rego
package secret
import future.keywords.in

allowedProviders := ["harnessSecretManager"]

deny[msg] {
  not input.secret.spec.secretManagerIdentifier in allowedProviders
  msg := sprintf("Only %s are allowed as providers", [allowedProviders])
}
```

## Sample JSON

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
