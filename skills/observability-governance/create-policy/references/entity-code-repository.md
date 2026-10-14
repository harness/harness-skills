# Code Repository Policies

---

## Code Repository

### Package: `repository`
### Root path: `input` (flat structure, no wrapper key)
### Valid actions: `onsave`

### Schema

```
input.identifier                             # repository name/identifier e.g. "my-repo"
input.default_branch                         # e.g. "main"
input.description                            # repository description
input.git_ignore                             # gitignore template name
input.is_public                              # boolean - whether repo is public
input.license                                # license type
input.readme                                 # boolean - whether to create README
input.parent_ref                             # scoped parent reference e.g. "accountId/orgId/projectId"

input.metadata.action                        # "onsave"
input.metadata.principalIdentifier           # user ID
input.metadata.principalType                 # "user"
input.metadata.type                          # "repository"
input.metadata.timestamp                     # unix timestamp

input.metadata.projectMetadata.identifier    # project identifier
input.metadata.projectMetadata.name          # project name
input.metadata.projectMetadata.description   # project description
input.metadata.projectMetadata.orgIdentifier # org identifier
input.metadata.projectMetadata.modules[]     # list of enabled modules e.g. ["CD", "CI", "CODE"]
input.metadata.projectMetadata.tags          # project tags object
```

### Example 1: Deny repository names containing forbidden words

**Scenario:** Prevent creating repositories with names containing "test" or "production".

```rego
package repository

forbidden_words = ["test", "production"]

deny[msg] {
  name := lower(input.identifier)
  word := forbidden_words[_]
  contains(name, word)
  msg := sprintf("Repository '%s' is not allowed because it contains the forbidden word '%s'", [input.identifier, word])
}
```

### Example 2: Require repository descriptions

**Scenario:** All repositories must have a non-empty description.

```rego
package repository

deny[msg] {
  input.description == ""
  msg := sprintf("Repository '%s' must have a description", [input.identifier])
}

deny[msg] {
  not input.description
  msg := sprintf("Repository '%s' must have a description", [input.identifier])
}
```

### Example 3: Enforce default branch naming

**Scenario:** All repositories must use "main" as the default branch.

```rego
package repository

deny[msg] {
  input.default_branch != "main"
  msg := sprintf("Repository '%s' must use 'main' as the default branch, got '%s'", [input.identifier, input.default_branch])
}
```

### Example 4: Deny public repositories

**Scenario:** No repositories should be created as public.

```rego
package repository

deny[msg] {
  input.is_public == true
  msg := sprintf("Repository '%s' cannot be public. All repositories must be private.", [input.identifier])
}
```

### Example 5: Enforce naming conventions

**Scenario:** Repository names must follow a prefix convention (e.g., team prefix).

```rego
package repository

allowed_prefixes = ["svc-", "lib-", "infra-", "app-"]

deny[msg] {
  name := lower(input.identifier)
  not starts_with_allowed(name)
  msg := sprintf("Repository '%s' must start with one of: %v", [input.identifier, allowed_prefixes])
}

starts_with_allowed(name) {
  prefix := allowed_prefixes[_]
  startswith(name, prefix)
}
```

### Sample JSON

```json
{
  "default_branch": "main",
  "description": "",
  "git_ignore": "",
  "identifier": "test-production-repo",
  "is_public": false,
  "license": "",
  "metadata": {
    "action": "onsave",
    "principalIdentifier": "1PSO8LO2Svud3biXkMGOlA",
    "principalType": "user",
    "projectMetadata": {
      "description": "",
      "identifier": "testreporules",
      "modules": [
        "CD", "CI", "CV", "CF", "CE", "STO", "CHAOS", "SRM",
        "IACM", "CET", "IDP", "CODE", "SSCA", "AISRE", "CORE",
        "PMS", "TEMPLATESERVICE", "SEI", "HAR", "FME", "DBOPS",
        "AASP", "AARP", "AAST"
      ],
      "name": "test-repo-rules",
      "orgIdentifier": "default",
      "tags": {}
    },
    "timestamp": 1774377400,
    "type": "repository"
  },
  "parent_ref": "vpCkHKsDSxK9_KYfjCTMKA/default/testreporules",
  "readme": false
}
```
