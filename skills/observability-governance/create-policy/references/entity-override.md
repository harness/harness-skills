# Override Policies

## Package: `override`
## Root path: `input.overrideEntity`
## Valid actions: `onsave`

## Schema

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

## Example 1: Deny GitHub config file overrides

```rego
package override

deny[msg] {
  input.overrideEntity.configFiles[_].configFile.spec.store.type == "Github"
  msg := "Cannot override config files to fetch from Github"
}
```

## Example 2: Deny non-main branch config files

```rego
package override

deny[msg] {
  input.overrideEntity.configFiles[_].configFile.spec.store.spec.branch != "main"
  msg := "Cannot override config files to fetch from non main branch"
}
```

## Example 3: Deny overriding specific variables

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
