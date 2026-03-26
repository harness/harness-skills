# Feature Flag / FME Policies

## Entity Types Covered
- `featureFlag` — FME feature flags (package: `fme_feature_flags`)
- `featureFlagDefinition` — FME feature flag definitions (package: `fme_feature_flags`)
- `fmeEnvironment` — FME environments (package: `fme_environment`)
- `fmeSegment` — FME segments (package: `fme_segment`)
- `flag` — Legacy feature flags (package: `flag`)

## Valid actions: `onsave` (all FME types)

---

## featureFlag Schema

```
input.featureFlag.id
input.featureFlag.name
input.featureFlag.trafficTypeName
input.featureFlag.status                    # "ACTIVE", "ARCHIVED", etc.
input.featureFlag.description
input.featureFlag.keyMetrics[i]
input.featureFlag.supportingMetrics[i]
input.featureFlag.rolloutStatusName
input.featureFlag.pendingChangeRequests
input.featureFlag.hasPendingStatusChange
input.featureFlag.tags[i]                   # array of strings like "owner:alice@example.com"
input.featureFlag.lastTrafficDate
input.featureFlag.governanceType            # "fmeFeatureFlag"

input.entityMetadata.actor.type             # "user"
input.entityMetadata.actor.id
input.entityMetadata.actor.name
input.entityMetadata.account.accountId
input.entityMetadata.account.harnessUrl
input.entityMetadata.account.organizationId
input.entityMetadata.trafficType.id
input.entityMetadata.trafficType.name
input.entityMetadata.trafficType.projectId
input.entityMetadata.project.id
input.entityMetadata.owners[i].id
input.entityMetadata.owners[i].ownerType    # "team", "user"
input.entityMetadata.owners[i].ownerId
input.entityMetadata.owners[i].ownerName
input.entityMetadata.changeTrigger          # "update", "create"
```

## Example 1: Naming convention enforcement

**Scenario:** Feature flag names must start with `ff_` and use only lowercase letters, numbers, underscores.

```rego
package fme_feature_flags

deny[msg] {
	not regex.match("^ff_[a-z]+[a-z0-9_]*$", input.featureFlag.name)
	msg := sprintf("FME Feature Flag name '%s' must start with 'ff_' and contain only lowercase letters, numbers, and underscores", [input.featureFlag.name])
}

deny[msg] {
	count(input.featureFlag.name) < 5
	msg := sprintf("FME Feature Flag name '%s' is too short (minimum 5 characters)", [input.featureFlag.name])
}

deny[msg] {
	count(input.featureFlag.name) > 100
	msg := sprintf("FME Feature Flag name '%s' is too long (maximum 100 characters)", [input.featureFlag.name])
}
```

## Example 2: Required tags

**Scenario:** Feature flags must have owner, team, service, and component tags.

```rego
package fme_feature_flags

deny[msg] {
	count(input.featureFlag.tags) == 0
	msg := sprintf("FME Feature Flag '%s' must have at least one tag", [input.featureFlag.name])
}

deny[msg] {
	not contains_required_tag("owner")
	msg := sprintf("FME Feature Flag '%s' must have an 'owner' tag", [input.featureFlag.name])
}

deny[msg] {
	not contains_required_tag("team")
	msg := sprintf("FME Feature Flag '%s' must have a 'team' tag", [input.featureFlag.name])
}

deny[msg] {
	not contains_required_tag("service")
	msg := sprintf("FME Feature Flag '%s' must have a 'service' tag", [input.featureFlag.name])
}

contains_required_tag(tag_name) {
	some i
	contains(input.featureFlag.tags[i], tag_name)
}

warn[msg] {
	input.featureFlag.description == ""
	msg := sprintf("FME Feature Flag '%s' should have a description", [input.featureFlag.name])
}
```

## Example 3: Team ownership enforcement

**Scenario:** Feature flags must have at least one owner and all owners must be teams (not individual users).

```rego
package fme_feature_flags

deny[msg] {
	count(input.entityMetadata.owners) == 0
	msg := sprintf("FME Feature Flag '%s' must have at least one owner", [input.featureFlag.name])
}

deny[msg] {
	some i
	owner := input.entityMetadata.owners[i]
	owner.ownerType == "user"
	owner_name := object.get(owner, "ownerName", owner.ownerId)
	msg := sprintf("FME Feature Flag '%s' has an individual user owner '%s'. Owners must be teams, not individual users", [input.featureFlag.name, owner_name])
}
```

---

## featureFlagDefinition Schema

```
input.featureFlagDefinition.name
input.featureFlagDefinition.description
input.featureFlagDefinition.treatments[i].name        # "ON", "OFF"
input.featureFlagDefinition.treatments[i].description
input.featureFlagDefinition.definition
input.featureFlagDefinition.defaultTreatment           # "OFF"
input.featureFlagDefinition.governanceType             # "fmeFeatureFlagDefinition"
```

## Example 4: Definition validation

**Scenario:** Feature flag definitions must have at least 2 treatments (ON/OFF), each with descriptions, default must be OFF.

```rego
package fme_feature_flags

deny[msg] {
	count(input.featureFlagDefinition.treatments) < 2
	msg := sprintf("Feature Flag Definition '%s' must have at least 2 treatments", [input.featureFlagDefinition.name])
}

deny[msg] {
	not has_treatment("ON")
	msg := sprintf("Feature Flag Definition '%s' must have an 'ON' treatment", [input.featureFlagDefinition.name])
}

deny[msg] {
	not has_treatment("OFF")
	msg := sprintf("Feature Flag Definition '%s' must have an 'OFF' treatment", [input.featureFlagDefinition.name])
}

deny[msg] {
	input.featureFlagDefinition.defaultTreatment != "OFF"
	msg := sprintf("Feature Flag Definition '%s' default treatment must be 'OFF', got '%s'", [input.featureFlagDefinition.name, input.featureFlagDefinition.defaultTreatment])
}

deny[msg] {
	some i
	treatment := input.featureFlagDefinition.treatments[i]
	treatment.description == ""
	msg := sprintf("Feature Flag Definition '%s' treatment '%s' must have a description", [input.featureFlagDefinition.name, treatment.name])
}

has_treatment(name) {
	input.featureFlagDefinition.treatments[_].name == name
}
```

---

## fmeEnvironment Schema

```
input.fmeEnvironment.id
input.fmeEnvironment.name
input.fmeEnvironment.status
input.fmeEnvironment.environmentType
input.fmeEnvironment.changeSettings
input.fmeEnvironment.pipelineSettings
input.fmeEnvironment.tags[i]
input.entityMetadata                        # same structure as featureFlag
```

## Example 5: FME environment naming

```rego
package fme_environment

deny[msg] {
	not regex.match("^[a-z][a-z0-9_]*$", input.fmeEnvironment.name)
	msg := sprintf("FME Environment name '%s' must start with lowercase letter and contain only lowercase letters, numbers, and underscores", [input.fmeEnvironment.name])
}
```

---

## Legacy Flag Schema

```
input.flag.name
input.flag.identifier
input.flag.kind                            # "boolean", "multivariate"
input.flag.variations[i].identifier
input.flag.variations[i].name
input.flag.variations[i].value
input.flag.defaultOnVariation
input.flag.defaultOffVariation
input.flag.envProperties.state             # "on", "off"
input.flag.envProperties.rules[i]
input.flag.envProperties.environment
input.flag.envProperties.pipelineConfigured
input.flag.envProperties.pipelineDetails.pipelineIdentifier
input.flag.services[i]
```

## Example 6: Legacy flag defaults

```rego
package flag

deny[msg] {
	input.flag.defaultOnVariation != "false"
	msg := sprintf("flag '%s' on-variation must be 'false'", [input.flag.name])
}

deny[msg] {
	input.flag.defaultOffVariation != "false"
	msg := sprintf("flag '%s' off-variation must be 'false'", [input.flag.name])
}
```

## Example 7: Require description before save (FME)

**Scenario:** Feature flags must have a non-empty description. Skip validation during deletion.

```rego
package fme_feature_flags

deny[msg] {
  input.entityMetadata.changeTrigger != "delete"
  not input.featureFlag.description
  msg := sprintf(
    "Feature flag '%s' must include a description before it can be saved",
    [input.featureFlag.name]
  )
}

deny[msg] {
  input.entityMetadata.changeTrigger != "delete"
  input.featureFlag.description == ""
  msg := sprintf(
    "Feature flag '%s' must include a non-empty description",
    [input.featureFlag.name]
  )
}
```

## Example 8: Require owner for active flags (FME)

**Scenario:** Active feature flags cannot exist without an assigned owner.

```rego
package fme_feature_flags

deny[msg] {
  input.featureFlag.status == "ACTIVE"
  count(input.entityMetadata.owners) == 0
  msg := sprintf(
    "Feature flag '%s' cannot be active without an assigned owner",
    [input.featureFlag.name]
  )
}
```

## Example 9: Enforce Jira ticket in flag name (FME)

**Scenario:** New feature flag names must start with a valid Jira ticket prefix.

```rego
package fme_feature_flags

deny[msg] {
  input.entityMetadata.changeTrigger == "create"
  not regex.match("^FME-[0-9]+-.*", input.featureFlag.name)
  msg := sprintf(
    "Feature flag name '%s' must start with a valid Jira ticket (for example, FME-1234-*)",
    [input.featureFlag.name]
  )
}
```

## Example 10: Prevent archiving flags with recent traffic (FME)

**Scenario:** Feature flags that received traffic within the last 24 hours cannot be archived.

```rego
package fme_feature_flags

deny[msg] {
  input.entityMetadata.changeTrigger == "archive"
  last_traffic_ns := time.parse_rfc3339_ns(input.featureFlag.lastTrafficDate)
  now_ns := time.now_ns()
  one_day_ns := 24 * 60 * 60 * 1000000000
  now_ns - last_traffic_ns < one_day_ns
  msg := sprintf(
    "Feature flag '%s' cannot be archived because it received traffic within the last 24 hours (last traffic: %s)",
    [input.featureFlag.name, input.featureFlag.lastTrafficDate]
  )
}
```

---

## Example 11: Require default treatment to be OFF (FME Definition)

**Scenario:** Feature flag definitions must have "off" as the default treatment.

```rego
package fme_feature_flag_definitions

deny[msg] {
  input.entityMetadata.changeTrigger != "delete"
  some i
  input.featureFlagDefinition.treatments[i].defaultTreatment == true
  input.featureFlagDefinition.treatments[i].name != "off"
  msg := sprintf(
    "Feature flag '%s' in '%s' must have 'off' as the default treatment",
    [input.featureFlagDefinition.name, input.featureFlagDefinition.environmentName]
  )
}
```

## Example 12: Require flag sets in Production (FME Definition)

**Scenario:** Feature flag definitions in Production must belong to at least one flag set.

```rego
package fme_feature_flag_definitions

deny[msg] {
  input.featureFlagDefinition.environmentName == "Production"
  count(input.featureFlagDefinition.flagSets) == 0
  msg := sprintf(
    "Feature flag '%s' in Production must belong to at least one flag set",
    [input.featureFlagDefinition.name]
  )
}
```

---

## Example 13: Production/stage sync check (Legacy)

**Scenario:** A flag cannot be enabled in production if it is disabled in stage.

```rego
package feature_flags

deny[msg] {
  prod := input.flag.envProperties[_]
  prod.environment == "production"
  prod.state == "on"
  stage := input.flag.envProperties[_]
  stage.environment == "stage"
  stage.state == "off"
  msg := sprintf("Flag '%s' cannot be enabled in 'production' because it is disabled in 'stage'", [input.flag.name])
}
```

## Example 14: Boolean type enforcement (Legacy)

**Scenario:** Flags must be of boolean type only.

```rego
package feature_flags

deny[msg] {
  input.flag.kind != "boolean"
  msg := sprintf("Flag '%s' isn't of type 'boolean'", [input.flag.name])
}
```

## Example 15: Jira ticket naming (Legacy)

**Scenario:** Flag names must contain a Jira ticket number.

```rego
package feature_flags

deny[msg] {
  not regex.match("[FFM|OPA|CI|CD]+[-][1-9][0-9]?", input.flag.name)
  msg := sprintf("Flag name '%s' doesn't contain a Jira ticket number", [input.flag.name])
}
```

## Sample featureFlag JSON

```json
{
  "featureFlag": {
    "id": "5f8d9a1b2c3d4e5f6a7b8c9d",
    "name": "ff_user_authentication_v2",
    "trafficTypeName": "user",
    "status": "ACTIVE",
    "description": "Enable new authentication flow",
    "tags": ["authentication", "security"],
    "governanceType": "fmeFeatureFlag"
  },
  "entityMetadata": {
    "actor": { "type": "user", "id": "user_001", "name": "Developer" },
    "account": { "accountId": "harness_acc_xyz789" },
    "owners": [
      { "ownerType": "team", "ownerId": "team_platform", "ownerName": "Platform Engineering" }
    ],
    "changeTrigger": "update"
  }
}
```
