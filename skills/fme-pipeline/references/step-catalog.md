# FME Pipeline Step Catalog

Harness FME pipelines use native FME steps (`FmeFlag*`, `FmeFlagset*`, `FmeSegment*`, `FmeMetricCheck`). Step YAML `type:` strings must match the exact identifiers documented below — naming traps to watch for: `FmeFlagSetIndividualTargets` (not `FmeFlagSetTargets`), `FmeFlagAddRemoveIndividualTargets` (not `FmeFlagAddRemoveTargets`), `FmeSegmentAddRemoveTargets` (not `FmeSegmentAddRemoveKeys`).

**Schema source:** Field shapes are derived from [harness-schema/v0/pipeline.json](https://github.com/harness/harness-schema/blob/main/v0/pipeline.json). When the schema changes, re-check and update the tables below by hand.

## Stage guidance

Default to **`type: Custom`** stages for FME rollouts. The official [Harness FME pipeline docs](https://developer.harness.io/feature-management-experimentation/management-and-administration/pipelines) add FME steps in Custom stages. The schema also allows FME steps in `FeatureFlag` stages, but Custom stages are more flexible.

**Stage types:**

| Stage `type` | Use for |
|--------------|---------|
| `Custom` | FME flag/segment steps, optionally mixed with Wait, HarnessApproval, Jira/ServiceNow, or ShellScript in the same stage |
| `Approval` | Standalone human gate (optional; approvals can go inline in Custom stages) |

**Failure strategies:** Custom stages have no `rollback` section. Use `MarkAsFailure` on errors, plus an explicit kill stage with `when: pipelineStatus: Failure` for production rollback paths. Do not use `StageRollback` with FME steps.

## FME step purposes

The 25 FME steps cover flag lifecycle, targeting, traffic shaping, metrics, flagsets, and segments:

| Step | Purpose | Typical use |
|------|---------|-------------|
| `FmeFlagCreate` | Create flag metadata + treatments | Bootstrap a new flag (usually killed in all envs first) |
| `FmeFlagUpdate` | Update flag metadata (description, tags, owners, rollout status) | Bookkeeping between rollout phases |
| `FmeFlagDelete` | Delete flag | Avoid in rollout pipelines — prefer kill + archive |
| `FmeFlagArchive` | Archive launched flag | Post-launch cleanup |
| `FmeFlagKill` | Emergency **off** / rollback | Failure strategy or explicit rollback stage |
| `FmeFlagRestore` | Turn flag **on** in an environment (undo kill) | First step when enabling traffic |
| `FmeFlagDefaultAllocation` | Set default-rule percentage split across treatments | Progressive rollout (5 → 25 → 50 → 100) and full launch |
| `FmeFlagLimitExposure` | Cap exposure to a treatment (0–100) | Alternative to allocation for simple % caps |
| `FmeFlagSetTreatments` | Define treatment list + defaults | When treatments are not yet defined in the env |
| `FmeFlagSetTargetingRules` | Replace targeting rules | Beta cohorts, segment rules, prerequisites |
| `FmeFlagAddRemoveIndividualTargets` | Add/remove individual targets | Target specific users before percentage rollout |
| `FmeFlagSetIndividualTargets` | Replace individual target list | Same as above when replacing the full list |
| `FmeFlagPatchDefinition` | JSON Patch operations on a definition (`operations` is a **string**, not a YAML list) | Surgical edits; prefer `FmeFlagDefinitionInstructions` for structured, schema-checked changes |
| `FmeFlagReallocateTraffic` | Re-bucket traffic after definition change | After large targeting edits |
| `FmeFlagSetDynamicConfigurations` | Attach dynamic config per treatment | Config-driven rollouts |
| `FmeFlagDefinitionInstructions` | Apply multiple definition mutations atomically | Batch restore + allocation + rules; env promotion when several fields change together |
| `FmeMetricCheck` | Evaluate FME metrics over a lookback window; fail the **step** if JEXL `failureCriteria` is true | Soak/gate between % increases — **not** auto-rollback |
| `FmeFlagsetCreate` | Create a flagset | Bootstrap a flagset before associating rollout flags |
| `FmeFlagsetDelete` | Delete a flagset | Cleanup after launch — not typical mid-rollout |
| `FmeFlagAddRemoveFlagsets` | Add/remove flagset associations on a flag definition | Attach a flag to a release flagset in an environment |
| `FmeSegmentCreate` | Create segment | Define a user cohort |
| `FmeSegmentUpdate` | Update segment metadata | Bookkeeping |
| `FmeSegmentDelete` | Delete segment | Cleanup |
| `FmeSegmentAddRemoveTargets` | Mutate segment membership | Add/remove users from a segment |
| `FmeSegmentSetTargetingRules` | Replace segment targeting rules | Define segment inclusion criteria |

## Evaluation order (FME/Split model)

When sequencing steps, remember how targeting is evaluated:

1. **Killed** → serves `defaultTreatment` only (flag is off)
2. **Individual targets** → highest priority
3. **Rules** → top-to-bottom, first match wins
4. **Default rule / allocation** → fallthrough percentage or single treatment

**Implications:**

- `FmeFlagRestore` alone does not change percentages — pair with `FmeFlagDefaultAllocation` or `FmeFlagLimitExposure`.
- Individual targets bypass percentage rollout — remove or narrow them before a full launch.
- Downstream env gating: keep prod **killed** (`FmeFlagKill`) until upstream env is verified at 100%.

## Out of scope

**`FmeFlagSetImpressionTracking`** and **`FmeChangeProposalSubmit`** are excluded from this skill by product decision. Legacy **`FlagConfiguration`** steps are also not covered (use native FME steps instead).

---

## Flag lifecycle

### `FmeFlagCreate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `baselineTreatment` |  | string | ✓ | Baseline treatment for the feature flag |
| `defaultTreatment` |  | string | ✓ | Default treatment for the feature flag |
| `name` | ✓ | string | ✓ |  |
| `owners` |  | [string] | ✓ | Feature flag owners |
| `tags` |  | [string] | ✓ | Feature flag tags |
| `trafficType` | ✓ | string | ✓ | FME Traffic Type name (case-sensitive) |
| `treatments` |  | [{description*, treatment*}] | ✓ | List of treatments with their descriptions |

### `FmeFlagUpdate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ |  |
| `owners` |  | [string] | ✓ | Feature flag owners |
| `rolloutStatus` |  | string | ✓ | Feature flag rollout status |
| `tags` |  | [string] | ✓ | Feature flag tags |

### `FmeFlagDelete`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `deleteAllDefinitions` |  | bool | ✓ | When enabled, deletes all feature flag definitions before deleting the flag |
| `name` | ✓ | string | ✓ |  |

### `FmeFlagArchive`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ |  |

### `FmeFlagKill`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |

### `FmeFlagRestore`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |

## Targeting & traffic

### `FmeFlagDefaultAllocation`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `allocation` | ✓ | [{amount*: int 0–100, treatment*}] | ✓ | Feature flag allocation |
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |

### `FmeFlagLimitExposure`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `limit` | ✓ | int 0–100 | ✓ | Exposure limit |

### `FmeFlagSetTreatments`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `baselineTreatment` | ✓ | string | ✓ | Baseline treatment for the configuration |
| `defaultTreatment` | ✓ | string | ✓ | Default treatment for the configuration |
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `treatments` | ✓ | [{description*, treatment*}] | ✓ | List of treatments with their descriptions |

### `FmeFlagSetTargetingRules`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `targetingRules` | ✓ | see below | ✓ | Array of targeting rules, each containing conditions and allocations |

`targetingRules`: [{allocation*: [{size*: int 0–100, treatment*}], condition*: {rules*: [{attribute, feature_flag, negate: bool, type*: `"IN_SEGMENT"` or `"IN_SPLIT"` or `"BOOLEAN"` or `"ON_DATE"` or `"ON_OR_AFTER_DATE"` or `"ON_OR_BEFORE_DATE"` or `"BETWEEN_DATE"` or `"EQUAL_SET"` or `"ANY_OF_SET"` or `"ALL_OF_SET"` or `"PART_OF_SET"` or `"EQUAL_NUMBER"` or `"LESS_THAN_OR_EQUAL_NUMBER"` or `"GREATER_THAN_OR_EQUAL_NUMBER"` or `"BETWEEN_NUMBER"` or `"IN_LIST_STRING"` or `"STARTS_WITH_STRING"` or `"ENDS_WITH_STRING"` or `"CONTAINS_STRING"` or `"MATCHES_STRING"` or `"EQUAL_TO_SEMVER"` or `"GREATER_THAN_OR_EQUAL_TO_SEMVER"` or `"LESS_THAN_OR_EQUAL_TO_SEMVER"` or `"BETWEEN_SEMVER"` or `"IN_LIST_SEMVER"`, value: bool or number or string or [number or string] or {from*: …, to*: …}}]}}]

### `FmeFlagAddRemoveIndividualTargets`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `treatments` | ✓ | see below | ✓ | List of treatments with keys and segments to add or remove |

`treatments`: [{addKeys: [string], addSegments: [string], removeKeys: [string], removeSegments: [string], treatment*}]

### `FmeFlagSetIndividualTargets`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `treatments` | ✓ | [{keys: [string], segments: [string], treatment*}] | ✓ | List of treatments with keys and segments to set |

### `FmeFlagPatchDefinition`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `inputVariables` |  | see below |  |  |
| `operations` | ✓ | string | ✓ | Patch operations to apply |

`inputVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]

### `FmeFlagReallocateTraffic`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |

### `FmeFlagSetDynamicConfigurations`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `inputVariables` |  | see below |  |  |
| `treatments` | ✓ | [{configuration*, treatment*}] | ✓ | List of treatments with their configurations |

`inputVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]

### `FmeFlagDefinitionInstructions`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `defaultDefinition` |  | see below | ✓ | Optional. If the flag definition does not exist in the target environment, create one with these values. Ignored if definition already exists. |
| `environment` | ✓ | string | ✓ |  |
| `flagName` | ✓ | string | ✓ |  |
| `instructions` | ✓ | see below | ✓ | Ordered list of flag definition instructions to apply atomically. Each instruction type may appear at most once (validated when using a literal array; expressions are not checked). |

`defaultDefinition`: {baselineTreatment*, defaultTreatment*, treatments*: [{description*, treatment*}]}

`instructions` (discriminated union on `type`):
  - type `"SetDefaultTreatment"`: {value*}
  - type `"SetBaselineTreatment"`: {value*}
  - type `"SetTrackImpression"`: {value*: bool}
  - type `"SetLimitExposure"`: {value*: int 0–100}
  - type `"UpdateIndividualTargets"`: {value*: [{actions*: [{action*: `"AddKeys"` or `"RemoveKeys"` or `"AddSegments"` or `"RemoveSegments"` or `"SetKeys"` or `"SetSegments"`, value*: [string]}], treatment*}]}
  - type `"UpdateDynamicConfiguration"`: {value*: [{configuration*: string or string, treatment*}]}
  - type `"SetTargetingRules"`: {value*: [{allocation*: [{size*: int 0–100, treatment*}], condition*: {rules*: [{attribute: …, feature_flag: …, negate: …, type*: …, value: …}]}}]}
  - type `"SetDefaultAllocations"`: {value*: [{amount*: int 0–100, treatment*}]}
  - type `"SetTreatments"`: {value*: [{description*, treatment*}]}
  - type `"SetRolloutStatus"`: {value*}
  - type `"SetFlagKilled"`: {value*: bool}

## Metrics

### `FmeMetricCheck`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `environment` | ✓ | string | ✓ | FME Environment ID |
| `failureCriteria` | ✓ | {spec*: {condition*}, type*: `"Jexl"`} |  | Criteria to determine step failure. When condition evaluates to true, the step fails. |
| `flagName` | ✓ | string | ✓ | Feature flag name. Maps to testId in Tinybird queries. |
| `lookbackWindow` | ✓ | string | ✓ | Time window from now (e.g. 7d, 24h) |
| `metrics` |  | [{ref*}] | ✓ | One or more metrics to evaluate |

## Flagsets

### `FmeFlagsetCreate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ | Flag set name |

### `FmeFlagsetDelete`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ | Flag set name to delete |

### `FmeFlagAddRemoveFlagsets`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `addFlagsets` |  | [string] | ✓ | List of flagset names to add to the feature flag |
| `environment` | ✓ | string | ✓ | FME Environment Name or ID |
| `flagName` | ✓ | string | ✓ | Feature flag name |
| `removeFlagsets` |  | [string] | ✓ | List of flagset names to remove from the feature flag |

## Segments

### `FmeSegmentCreate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ |  |
| `owners` |  | [string] | ✓ | Segment owners (optional - defaults to admin team if not provided) |
| `segmentType` | ✓ | `"Standard"` or `"Large"` or `"RuleBased"` | ✓ | Segment type: Standard (less than 100,000 IDs), Large (more than 100,000 IDs, client-side SDKs only), or RuleBased (dynamic based on targeting rules) |
| `tags` |  | [string] | ✓ | Segment tags |
| `trafficType` | ✓ | string | ✓ | FME Traffic Type name (case-sensitive) |

### `FmeSegmentUpdate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ | Segment name |
| `owners` |  | [string] | ✓ | Segment owners |
| `tags` |  | [string] | ✓ | Segment tags |

### `FmeSegmentDelete`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `name` | ✓ | string | ✓ | Segment name to delete |

### `FmeSegmentAddRemoveTargets`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `addKeys` |  | [string] | ✓ | Keys to add to the segment |
| `environment` | ✓ | string | ✓ | ID of the FME environment |
| `removeKeys` |  | [string] | ✓ | Keys to remove from the segment |
| `segmentName` | ✓ | string | ✓ | Name of the segment to update |

### `FmeSegmentSetTargetingRules`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `comment` |  | string | ✓ | Optional comment for the operation |
| `environment` | ✓ | string | ✓ | ID of the FME environment |
| `excludeKeys` |  | [string] | ✓ | List of keys to exclude from the segment |
| `excludeSegments` |  | [string] | ✓ | List of segments to exclude |
| `rules` |  | see below | ✓ | List of targeting rules, each containing conditions |
| `segmentName` | ✓ | string | ✓ | Name of the rule-based segment to configure |
| `title` |  | string | ✓ | Optional title for the operation |

`rules`: [{condition*: {rules*: [{attribute, feature_flag, negate: bool, type*: `"IN_SEGMENT"` or `"IN_SPLIT"` or `"BOOLEAN"` or `"ON_DATE"` or `"ON_OR_AFTER_DATE"` or `"ON_OR_BEFORE_DATE"` or `"BETWEEN_DATE"` or `"EQUAL_SET"` or `"ANY_OF_SET"` or `"ALL_OF_SET"` or `"PART_OF_SET"` or `"EQUAL_NUMBER"` or `"LESS_THAN_OR_EQUAL_NUMBER"` or `"GREATER_THAN_OR_EQUAL_NUMBER"` or `"BETWEEN_NUMBER"` or `"IN_LIST_STRING"` or `"STARTS_WITH_STRING"` or `"ENDS_WITH_STRING"` or `"CONTAINS_STRING"` or `"MATCHES_STRING"` or `"EQUAL_TO_SEMVER"` or `"GREATER_THAN_OR_EQUAL_TO_SEMVER"` or `"LESS_THAN_OR_EQUAL_TO_SEMVER"` or `"BETWEEN_SEMVER"` or `"IN_LIST_SEMVER"`, value: bool or number or string or [number or string] or {from*: …, to*: …}}]}}]

## Building blocks

### `Wait`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `duration` | ✓ | string |  |  |
| `metadata` |  | string |  |  |

### `HarnessApproval`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `approvalMessage` |  | string |  |  |
| `approverInputs` |  | see below |  |  |
| `approvers` | ✓ | see below |  |  |
| `autoApproval` |  | see below |  |  |
| `callbackId` |  | string |  |  |
| `includePipelineExecutionHistory` | ✓ | bool or string |  |  |

`approverInputs`: [{allowedValues, defaultValue, name, regex*, required: bool, selectManyFrom, selectOneFrom} or {allowedValues*, defaultValue, name, regex, required: bool, selectManyFrom, selectOneFrom} or {allowedValues, defaultValue, name, regex, required: bool, selectManyFrom, selectOneFrom*} or {allowedValues, defaultValue, name, regex, required: bool, selectManyFrom*, selectOneFrom} or {allowedValues, defaultValue, name, regex, required: bool, selectManyFrom, selectOneFrom}]

`approvers`: {disallowPipelineExecutor*: bool or string, disallowedUserEmails: [string] or string, minimumCount*: int or string, serviceAccounts: [string] or string, userGroups: [string] or string}

`autoApproval`: {action*: `"APPROVE"`, comments, scheduledDeadline*: {time*, timeZone*}}

### `JiraCreate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `connectorRef` | ✓ | string |  |  |
| `delegateSelectors` |  | [string] or string |  |  |
| `fields` |  | [{name, value*}] |  |  |
| `issueType` | ✓ | string |  |  |
| `projectKey` | ✓ | string |  |  |

### `JiraUpdate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `connectorRef` | ✓ | string |  |  |
| `delegateSelectors` |  | [string] or string |  |  |
| `fields` |  | [{name, value*}] |  |  |
| `issueKey` | ✓ | string |  |  |
| `issueType` |  | string |  |  |
| `projectKey` |  | string |  |  |
| `transitionTo` |  | {status*, transitionName} |  |  |

### `JiraApproval`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `approvalCriteria` | ✓ | see below |  |  |
| `connectorRef` | ✓ | string |  |  |
| `delegateSelectors` |  | [string] or string |  |  |
| `issueKey` | ✓ | string |  |  |
| `issueType` |  | string |  |  |
| `projectKey` |  | string |  |  |
| `rejectionCriteria` |  | see below |  |  |
| `retryInterval` |  | string |  |  |

`approvalCriteria` (one of, by `type`):
  - type `"Jexl"`: {spec*: {expression*}}
  - type `"KeyValues"`: {spec*: {conditions*: [{key*, operator*: `"equals"` or `"not equals"` or `"in"` or `"not in"`, value*}], matchAnyCondition: bool or string}}

`rejectionCriteria` (one of, by `type`):
  - type `"Jexl"`: {spec*: {expression*}}
  - type `"KeyValues"`: {spec*: {conditions*: [{key*, operator*: `"equals"` or `"not equals"` or `"in"` or `"not in"`, value*}], matchAnyCondition: bool or string}}

### `ServiceNowCreate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `connectorRef` | ✓ | string |  |  |
| `createType` |  | `"Normal"` or `"Form"` or `"Standard"` |  |  |
| `delegateSelectors` |  | [string] or string |  |  |
| `fields` |  | [{name*, value*}] |  |  |
| `templateName` |  | string |  |  |
| `ticketType` | ✓ | string |  |  |
| `useServiceNowTemplate` |  | bool |  |  |

### `ServiceNowUpdate`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `connectorRef` | ✓ | string |  |  |
| `delegateSelectors` |  | [string] or string |  |  |
| `fields` |  | [{name*, value*}] |  |  |
| `templateName` |  | string |  |  |
| `ticketNumber` | ✓ | string |  |  |
| `ticketType` | ✓ | string |  |  |
| `updateMultiple` | ✓ | see below |  |  |
| `useServiceNowTemplate` | ✓ | bool |  |  |

`updateMultiple` (one of, by `type`):
  - type `"CHANGE_TASK"`: {spec*: {changeRequestNumber*, changeTaskType}}

### `ServiceNowApproval`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `approvalCriteria` | ✓ | see below |  |  |
| `changeWindow` |  | {endField*, startField*} |  |  |
| `connectorRef` | ✓ | string |  |  |
| `delegateSelectors` |  | [string] or string |  |  |
| `rejectionCriteria` |  | see below |  |  |
| `retryInterval` |  | string |  |  |
| `ticketNumber` | ✓ | string |  |  |
| `ticketType` | ✓ | string |  |  |

`approvalCriteria` (one of, by `type`):
  - type `"Jexl"`: {spec*: {expression*}}
  - type `"KeyValues"`: {spec*: {conditions*: [{key*, operator*: `"equals"` or `"not equals"` or `"in"` or `"not in"`, value*}], matchAnyCondition: bool or string}}

`rejectionCriteria` (one of, by `type`):
  - type `"Jexl"`: {spec*: {expression*}}
  - type `"KeyValues"`: {spec*: {conditions*: [{key*, operator*: `"equals"` or `"not equals"` or `"in"` or `"not in"`, value*}], matchAnyCondition: bool or string}}

### `ShellScript`

| Field | Required | Shape | Expr | Notes |
|-------|----------|-------|------|-------|
| `delegateSelectors` |  | [string] or string |  |  |
| `environmentVariables` |  | see below |  |  |
| `executionTarget` |  | {connectorRef, host, workingDirectory} or string |  |  |
| `includeInfraSelectors` |  | bool or string |  |  |
| `metadata` |  | string |  |  |
| `onDelegate` |  | bool or string |  |  |
| `outputAlias` |  | {key*, scope*: `"Pipeline"` or `"Stage"` or `"StepGroup"`} |  |  |
| `outputVariables` |  | see below |  |  |
| `shell` | ✓ | `"Bash"` or `"PowerShell"` |  |  |
| `source` | ✓ | see below |  |  |

`environmentVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]

`outputVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]

`source` (one of, by `type`):
  - type `"Harness"`: {spec*: {file*, type}}
  - type `"Inline"`: {spec*: {script*, type}}
