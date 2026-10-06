# FME Pipeline Step Catalog

Harness FME pipelines use native FME steps (`FmeFlag*`, `FmeFlagset*`, `FmeSegment*`, `FmeMetricCheck`). Step YAML `type:` strings must match the exact identifiers documented below — naming traps to watch for: `FmeFlagSetIndividualTargets` (not `FmeFlagSetTargets`), `FmeFlagAddRemoveIndividualTargets` (not `FmeFlagAddRemoveTargets`), `FmeSegmentAddRemoveTargets` (not `FmeSegmentAddRemoveKeys`).

**Schema source:** Field shapes are derived from [harness-schema/v0/pipeline.json](https://github.com/harness/harness-schema/blob/main/v0/pipeline.json).

## Stage guidance

Default to **`type: Custom`** stages for FME rollouts. The schema allows FME steps in both `Custom` and `FeatureFlag` stages. Custom stages are more flexible for mixing FME steps with Wait, HarnessApproval, Jira/ServiceNow, or ShellScript steps in the same stage.

**Failure strategies:** Custom stages have no `rollback` section. Use `MarkAsFailure` on errors, plus an explicit kill stage with `when: pipelineStatus: Failure` for production rollback paths. Do not use `StageRollback` with FME steps.

## FME step purposes

| Step | Purpose | Typical use |
|------|---------|-------------|
| `FmeFlagCreate` | Create flag metadata + treatments | Bootstrap a new flag (creates definitions with trafficAllocation 100% and defaultRule 100% on `defaultTreatment`) |
| `FmeFlagUpdate` | Update flag metadata (description, tags, owners, rollout status) | Bookkeeping between rollout phases |
| `FmeFlagDelete` | Delete flag | Avoid in rollout pipelines — prefer kill + archive |
| `FmeFlagArchive` | Archive launched flag | Post-launch cleanup |
| `FmeFlagKill` | Serve `defaultTreatment` to everyone in an environment | Failure strategy or explicit rollback stage |
| `FmeFlagRestore` | Un-kill: targeting resumes as configured | After approved initial targeting is written and manually read back/approved; before soak/later increases |
| `FmeFlagDefaultAllocation` | Set default-rule percentage split across treatments | Progressive rollout (5 → 25 → 50 → 100) and full launch |
| `FmeFlagLimitExposure` | Set flag-wide `trafficAllocation` exposure cap (0–100) | Limit exposure; traffic outside the cap gets `defaultTreatment` |
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

1. **Killed** → serves `defaultTreatment` to everyone
2. **Individual targets** → highest priority
3. **Traffic allocation** → keys outside the allocation % get `defaultTreatment`
4. **Rules** → top-to-bottom, first match wins
5. **Default rule / allocation** → fallthrough percentage or single treatment

**Implications:**

- `FmeFlagRestore` alone does not change percentages — pair with `FmeFlagDefaultAllocation` or `FmeFlagLimitExposure`.
- **Order matters when un-killing:** write approved initial allocation/targeting while killed → manual full-definition readback and `HarnessApproval` → `FmeFlagRestore` → soak/later ramp increases. Never restore stale targeting first, or wait until the final percentage to restore. A change to the served `defaultTreatment`/configuration affects killed traffic immediately and needs explicit approval.
- Individual targets bypass percentage rollout — remove or narrow them before a full launch.
- Downstream env gating: keep prod **killed** (`FmeFlagKill`) until upstream env is verified at 100%.
- **No native readback step exists for these mutations.** Use an agreed `HarnessApproval` checkpoint after the writes: the approver reads the complete target definition in Harness UI or `/explain-flag` and rejects mismatches before restore. If this cannot be done, stop and hand off; API acceptance is not verification. This manual configuration check is distinct from SDK propagation or a later `FmeMetricCheck`.

## Out of scope

**`FmeFlagSetImpressionTracking`** and **`FmeChangeProposalSubmit`** are excluded from this skill by product decision. Legacy **`FlagConfiguration`** steps are also not covered (use native FME steps instead).

---

## Flag lifecycle

### `FmeFlagCreate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string |  |
| `trafficType` | ✓ | string | FME Traffic Type name (case-sensitive) |
| `description` |  | string | Feature flag description |
| `baselineTreatment` |  | string | Baseline treatment for the feature flag |
| `defaultTreatment` |  | string | Default treatment for the feature flag |
| `owners` |  | [string] | Feature flag owners |
| `tags` |  | [string] | Feature flag tags |
| `treatments` |  | [{description*, treatment*}] | List of treatments with their descriptions |

**Note:** `treatments`, `defaultTreatment`, and `baselineTreatment` must be given together, with at least 2 treatments.

### `FmeFlagUpdate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string |  |
| `description` |  | string | Feature flag description |
| `owners` |  | [string] | Feature flag owners |
| `rolloutStatus` |  | string | Feature flag rollout status |
| `tags` |  | [string] | Feature flag tags |

### `FmeFlagDelete`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string |  |
| `deleteAllDefinitions` |  | bool | When enabled, deletes all feature flag definitions before deleting the flag |

### `FmeFlagArchive`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string |  |

### `FmeFlagKill`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |

### `FmeFlagRestore`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |

## Targeting & traffic

### `FmeFlagDefaultAllocation`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `allocation` | ✓ | [{amount*: int 0–100, treatment*}] | Feature flag allocation |

### `FmeFlagLimitExposure`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `limit` | ✓ | int 0–100 | Exposure limit |

### `FmeFlagSetTreatments`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `defaultTreatment` | ✓ | string | Default treatment for the configuration |
| `baselineTreatment` | ✓ | string | Baseline treatment for the configuration |
| `treatments` | ✓ | [{description*, treatment*}] | List of treatments with their descriptions |

### `FmeFlagSetTargetingRules`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `targetingRules` | ✓ | see below | Array of targeting rules, each containing conditions and allocations |

`targetingRules`: [{allocation*: [{size*: int 0–100, treatment*}], condition*: {rules*: [{attribute, feature_flag, negate: bool, type*: `"IN_SEGMENT"` or `"IN_SPLIT"` or `"BOOLEAN"` or `"ON_DATE"` or `"ON_OR_AFTER_DATE"` or `"ON_OR_BEFORE_DATE"` or `"BETWEEN_DATE"` or `"EQUAL_SET"` or `"ANY_OF_SET"` or `"ALL_OF_SET"` or `"PART_OF_SET"` or `"EQUAL_NUMBER"` or `"LESS_THAN_OR_EQUAL_NUMBER"` or `"GREATER_THAN_OR_EQUAL_NUMBER"` or `"BETWEEN_NUMBER"` or `"IN_LIST_STRING"` or `"STARTS_WITH_STRING"` or `"ENDS_WITH_STRING"` or `"CONTAINS_STRING"` or `"MATCHES_STRING"` or `"EQUAL_TO_SEMVER"` or `"GREATER_THAN_OR_EQUAL_TO_SEMVER"` or `"LESS_THAN_OR_EQUAL_TO_SEMVER"` or `"BETWEEN_SEMVER"` or `"IN_LIST_SEMVER"`, value: bool or number or string or [number or string] or {from*: …, to*: …}}]}}]

### `FmeFlagAddRemoveIndividualTargets`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `treatments` | ✓ | see below | List of treatments with keys and segments to add or remove |

`treatments`: [{addKeys: [string], addSegments: [string], removeKeys: [string], removeSegments: [string], treatment*}]

### `FmeFlagSetIndividualTargets`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `treatments` | ✓ | [{keys: [string], segments: [string], treatment*}] | List of treatments with keys and segments to set |

### `FmeFlagPatchDefinition`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `operations` | ✓ | string | Patch operations to apply (JSON Patch as **string**, not YAML list) |
| `inputVariables` |  | see below |  |

`inputVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]

### `FmeFlagReallocateTraffic`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |

### `FmeFlagSetDynamicConfigurations`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `treatments` | ✓ | [{configuration*, treatment*}] | List of treatments with their configurations |
| `inputVariables` |  | see below |  |

`inputVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]

### `FmeFlagDefinitionInstructions`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string |  |
| `environment` | ✓ | string |  |
| `defaultDefinition` |  | see below | Optional. If the flag definition does not exist in the target environment, create one with these values. Ignored if definition already exists. |
| `instructions` | ✓ | see below | Ordered list of flag definition instructions to apply atomically. Each instruction type may appear at most once. |

`defaultDefinition`: {baselineTreatment*, defaultTreatment*, treatments*: [{description*, treatment*}]}

`instructions` (discriminated union on `type`):
  - type `"SetDefaultTreatment"`: {value*}
  - type `"SetBaselineTreatment"`: {value*}
  - type `"SetTrackImpression"`: {value*: bool}
  - type `"SetLimitExposure"`: {value*: int 0–100}
  - type `"UpdateIndividualTargets"`: {value*: [{actions*: [{action*: `"AddKeys"` or `"RemoveKeys"` or `"AddSegments"` or `"RemoveSegments"` or `"SetKeys"` or `"SetSegments"`, value*: [string]}], treatment*}]}
  - type `"UpdateDynamicConfiguration"`: {value*: [{configuration*: string, treatment*}]}
  - type `"SetTargetingRules"`: {value*: [{allocation*: [{size*: int 0–100, treatment*}], condition*: {rules*: [{attribute: …, feature_flag: …, negate: …, type*: …, value: …}]}}]}
  - type `"SetDefaultAllocations"`: {value*: [{amount*: int 0–100, treatment*}]}
  - type `"SetTreatments"`: {value*: [{description*, treatment*}]}
  - type `"SetRolloutStatus"`: {value*}
  - type `"SetFlagKilled"`: {value*: bool}

## Metrics

### `FmeMetricCheck`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string | Feature flag name. Maps to testId in Tinybird queries. |
| `environment` | ✓ | string | FME Environment ID |
| `lookbackWindow` | ✓ | string | Time window from now (e.g. 7d, 24h) |
| `failureCriteria` | ✓ | {spec*: {condition*}, type*: `"Jexl"`} | Criteria to determine step failure. When condition evaluates to true, the step fails. |
| `metrics` |  | [{ref*}] | One or more metrics to evaluate |

## Flagsets

### `FmeFlagsetCreate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string | Flag set name |

### `FmeFlagsetDelete`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string | Flag set name to delete |

### `FmeFlagAddRemoveFlagsets`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `flagName` | ✓ | string | Feature flag name |
| `environment` | ✓ | string | FME Environment Name or ID |
| `addFlagsets` |  | [string] | List of flagset names to add to the feature flag |
| `removeFlagsets` |  | [string] | List of flagset names to remove from the feature flag |

## Segments

### `FmeSegmentCreate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string |  |
| `trafficType` | ✓ | string | FME Traffic Type name (case-sensitive) |
| `segmentType` | ✓ | `"Standard"` or `"Large"` or `"RuleBased"` | Segment type: Standard (less than 100,000 IDs), Large (more than 100,000 IDs, client-side SDKs only), or RuleBased (dynamic based on targeting rules) |
| `owners` |  | [string] | Segment owners |
| `tags` |  | [string] | Segment tags |

### `FmeSegmentUpdate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string | Segment name |
| `owners` |  | [string] | Segment owners |
| `tags` |  | [string] | Segment tags |

### `FmeSegmentDelete`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `name` | ✓ | string | Segment name to delete |

### `FmeSegmentAddRemoveTargets`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `segmentName` | ✓ | string | Name of the segment to update |
| `environment` | ✓ | string | ID of the FME environment |
| `addKeys` |  | [string] | Keys to add to the segment |
| `removeKeys` |  | [string] | Keys to remove from the segment |

### `FmeSegmentSetTargetingRules`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `segmentName` | ✓ | string | Name of the rule-based segment to configure |
| `environment` | ✓ | string | ID of the FME environment |
| `rules` |  | see below | List of targeting rules, each containing conditions |
| `excludeKeys` |  | [string] | List of keys to exclude from the segment |
| `excludeSegments` |  | [string] | List of segments to exclude |
| `comment` |  | string | Optional comment for the operation |
| `title` |  | string | Optional title for the operation |

`rules`: [{condition*: {rules*: [{attribute, feature_flag, negate: bool, type*: `"IN_SEGMENT"` or `"IN_SPLIT"` or `"BOOLEAN"` or `"ON_DATE"` or `"ON_OR_AFTER_DATE"` or `"ON_OR_BEFORE_DATE"` or `"BETWEEN_DATE"` or `"EQUAL_SET"` or `"ANY_OF_SET"` or `"ALL_OF_SET"` or `"PART_OF_SET"` or `"EQUAL_NUMBER"` or `"LESS_THAN_OR_EQUAL_NUMBER"` or `"GREATER_THAN_OR_EQUAL_NUMBER"` or `"BETWEEN_NUMBER"` or `"IN_LIST_STRING"` or `"STARTS_WITH_STRING"` or `"ENDS_WITH_STRING"` or `"CONTAINS_STRING"` or `"MATCHES_STRING"` or `"EQUAL_TO_SEMVER"` or `"GREATER_THAN_OR_EQUAL_TO_SEMVER"` or `"LESS_THAN_OR_EQUAL_TO_SEMVER"` or `"BETWEEN_SEMVER"` or `"IN_LIST_SEMVER"`, value: bool or number or string or [number or string] or {from*: …, to*: …}}]}}]

## Building blocks

### `Wait`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `duration` | ✓ | string |  |

### `HarnessApproval`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `approvers` | ✓ | {disallowPipelineExecutor*: bool or string, disallowedUserEmails: [string] or string, minimumCount*: int or string, serviceAccounts: [string] or string, userGroups: [string] or string} |  |
| `includePipelineExecutionHistory` | ✓ | bool or string |  |
| `approvalMessage` |  | string |  |

### `JiraCreate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `connectorRef` | ✓ | string |  |
| `projectKey` | ✓ | string |  |
| `issueType` | ✓ | string |  |
| `fields` |  | [{name, value*}] |  |

### `JiraUpdate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `connectorRef` | ✓ | string |  |
| `issueKey` | ✓ | string |  |
| `fields` |  | [{name, value*}] |  |
| `transitionTo` |  | {status*, transitionName} |  |

### `JiraApproval`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `connectorRef` | ✓ | string |  |
| `issueKey` | ✓ | string |  |
| `approvalCriteria` | ✓ | see below |  |
| `rejectionCriteria` |  | see below |  |

`approvalCriteria` (one of, by `type`):
  - type `"Jexl"`: {spec*: {expression*}}
  - type `"KeyValues"`: {spec*: {conditions*: [{key*, operator*: `"equals"` or `"not equals"` or `"in"` or `"not in"`, value*}], matchAnyCondition: bool or string}}

### `ServiceNowCreate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `connectorRef` | ✓ | string |  |
| `ticketType` | ✓ | string |  |
| `fields` |  | [{name*, value*}] |  |

### `ServiceNowUpdate`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `connectorRef` | ✓ | string |  |
| `ticketType` | ✓ | string |  |
| `ticketNumber` |  | string |  |
| `useServiceNowTemplate` | ✓ | bool |  |
| `fields` |  | [{name*, value*}] |  |

### `ServiceNowApproval`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `connectorRef` | ✓ | string |  |
| `ticketType` | ✓ | string |  |
| `ticketNumber` | ✓ | string |  |
| `approvalCriteria` | ✓ | see below |  |
| `rejectionCriteria` |  | see below |  |

`approvalCriteria` (one of, by `type`):
  - type `"Jexl"`: {spec*: {expression*}}
  - type `"KeyValues"`: {spec*: {conditions*: [{key*, operator*: `"equals"` or `"not equals"` or `"in"` or `"not in"`, value*}], matchAnyCondition: bool or string}}

### `ShellScript`

| Field | Required | Shape | Notes |
|-------|----------|-------|-------|
| `shell` | ✓ | `"Bash"` or `"PowerShell"` |  |
| `source` | ✓ | see below |  |
| `onDelegate` |  | bool or string |  |
| `outputVariables` |  | see below |  |

`source` (one of, by `type`):
  - type `"Harness"`: {spec*: {file*, type}}
  - type `"Inline"`: {spec*: {script*, type}}

`outputVariables`: [{default: number, name, required: bool, type: `"Number"`, value*: number or string} or {default, name, required: bool, type: `"Secret"`, value*} or {default, name, required: bool, type: `"String"`, value*}]
