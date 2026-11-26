# Evidence contract

This document describes the payloads the skill sends and the checks applied
to them on each side.

## 1. Create the scan

MCP: `harness_create` with `resource_type: chaos_risk_scan`.

```json
{
  "identity": "code-scan-<repo>-<short-sha>-<yyyymmddhhmm>",
  "name": "Code scan <repo>@<short-sha>",
  "tags": ["code-scan"],
  "scanType": "CodeRepository",
  "detectionMethod": "External",
  "source": {
    "codeRepository": {
      "repoURL": "github.com/acme/payments",
      "branch": "main",
      "commitSHA": "<40-char sha>",
      "provider": "github",
      "linkedServices": [
        { "module": "services/api", "chaosServiceIdentity": "payments-api" }
      ]
    }
  }
}
```

- `scanType` is `CodeRepository` (ad-hoc MCP / skill path) or `CIRiskScan`
  (Build Scans / Worker Agent path). Both use `detectionMethod: External` and
  the same `source.codeRepository` shape. `CIRiskScan` may omit `commitSHA`
  until `submit_findings`. For `CIRiskScan`, set `scope` (`branch` /
  `commit` / `pullRequest`); `pullRequest` also needs `pullRequestNumber`
  (and usually `targetBranch` + `baseSHA` before submit).
- `repoURL` is normalised to `host/org/repo`, with no scheme, no credentials
  and no `.git` suffix.
- `linkedServices` is optional. Each entry links a module path to an existing
  Harness chaos service. A module with no link is matched to the
  CodeRepository chaos service whose `repoURL` and `module` match. A module
  with neither is rejected per finding and not stored.

## 2. Submit the findings

MCP: `harness_execute` with `resource_type: chaos_risk_scan`,
`action: submit_findings` and the scan identity.

```json
{
  "findings": [
    {
      "riskRuleId": "code-outbound-call-without-timeout",
      "riskName": "Payment provider client has no timeout",
      "description": "The charge handler calls the provider through http.DefaultClient.",
      "impact": "A slow provider blocks every charge request goroutine.",
      "module": "services/api",
      "evidence": ["http.DefaultClient.Do(req) in the charge handler, with no context deadline"],
      "remediation": ["Use a client with Timeout: 5s, or set a context deadline per call"],
      "resilienceTestingRec": ["Inject pod-network-latency of 3s on the provider egress and check that charge p99 stays under 5s"],
      "codeLocations": [
        { "file": "services/api/charge.go", "startLine": 41, "endLine": 43, "snippet": "resp, err := http.DefaultClient.Do(req)" }
      ],
      "callSiteCount": 7,
      "tags": ["ciRange:commit"]
    }
  ],
  "commitSHA": "<40-char sha>"
}
```

On a `CIRiskScan` with `scope: pullRequest`, inventory may tag each fact
`ciRange=commit` (overlaps the tip-commit hunks) or `ciRange=pullRequest`
(overlaps only the PR-wide hunks). `validate_evidence.py` copies that onto
finding `tags` as `ciRange:commit` or `ciRange:pullRequest`. A fact in both
ranges is stored once as `ciRange:commit`. Other tags are dropped. Branch and
commit scopes omit `ciRange`. `commitSHA` is required when the scan was
created without one.

## Field rules

| Field | Local check (`validate_evidence.py`) | Server check |
|---|---|---|
| `riskRuleId` | Exists in the fetched rule list. A custom rule must have `spec.includeInPassiveScan` true; system rules are eligible without the flag | Rule exists in scope (or is a system rule), `spec.dataSource == SourceCode`, and a custom rule has `spec.includeInPassiveScan` true |
| `riskName`, `evidence`, `remediation` | Non-empty | Non-empty |
| `resilienceTestingRec` | Names at least one fault from the rule | Names at least one fault from the rule's `spec.faults` |
| `codeLocations` | 1 to 5 entries; file inside the repo and not excluded by scope; snippet appears verbatim within the line range at `commitSHA` | 1 to 5 entries; relative path with no `..`; `1 <= startLine <= endLine`; snippet at most 2000 characters |
| `module` | Path inside the repo, or `.` for the root | Relative path with no `..` |
| `severity`, `category`, `riskRuleName` | Not sent | Taken from the rule; any sent value is overwritten |
| `tags` | From inventory `ciRange` only (`ciRange:commit` / `ciRange:pullRequest`); commit wins | Stored on the scanned risk; list filter `tags=ciRange:…` |
| Count | One finding per (rule, module) | At most 100 findings per request |

`validationType` is always `Passive` for code findings. A finding becomes
`Confirmed` only when a chaos experiment's probe with
`ruleDetails.ruleIdentity` set to the rule fails.

## Deduplication

The server fingerprints each finding by its chaos service and `riskRuleId`, so
the same (rule, module) reported by a later scan updates the existing risk.
Re-detection keeps the `Ignored` status and reopens `Resolved` risks.

## Suppression

An inline comment on the line, or the line above it, suppresses a code
location locally:

```
// harness-chaos-ignore: code-outbound-call-without-timeout provider SDK sets its own deadline
```

The comment needs both a rule identity and a reason. A finding whose code
locations are all suppressed is dropped.
