# Variable Policies

## Package: `variable`
## Root path: `input.variable` + `input.metadata`
## Valid actions: `onsave`

## Schema

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

## Example 1: Role-based variable edit restriction

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

## Sample JSON

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
