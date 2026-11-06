# Configuration & constants (single source of truth)

Change a value here, not in `SKILL.md` or the other references.

## Standards

| Item | Value |
|---|---|
| Patch coverage gate | **80%** (`patch_coverage_percent: "80"`, fixed org standard) |
| Total coverage | Reported for visibility, **not** gated |
| Coverage step template | `account.codeCoverage`, `versionLabel: v1` |
| Environment variables | **None required** — do not add any |
| PR status checks | `coverage-patch`, `coverage-project` |
| PR comment | Upserted "Harness Code Coverage report" (covered vs uncovered lines) |
| Default-branch names | `main` / `master` — detect from the repo, don't assume |

## Account-level centralised pipeline templates

Published at account scope; any pipeline in any org/project can inherit them
(`templateRef: account.<id>`, `versionLabel: v1`).

| Language | `templateRef` |
|---|---|
| Java / Maven | `account.centralisedJavaCoverageTemplate` |
| Go | `account.centralisedGoCheckTemplate` |
| TypeScript / React UI | `account.centralisedTsCoverageTemplate` |
| Python | `account.centralisedPythonCoverageTemplate` |

## Terminology

| Term | Sonar term | HCC term | Meaning |
|---|---|---|---|
| New code coverage | New code coverage | Patch coverage | Lines added/changed in the PR (gated at 80%) |
| Overall coverage | Overall coverage | Total coverage | Whole repository |
| Baseline coverage | — | Baseline coverage | Default-branch snapshot recorded by the baseline trigger; powers trends and PR deltas |
| Quality gate | Quality gate | Coverage check / `hcli cov wait-until` | Pass/fail decision made by the pipeline step |

"Code coverage" here means line coverage from the repo's **unit test suite**, not integration/E2E.

## Account enablement

Code Coverage must be enabled on your account before onboarding pipelines. If not yet enabled,
contact Harness Support (`support@harness.io`) or your Customer Success Engineer (CXE).

## Exclusions

- Exclusions are configured in the Code Coverage module (server-side repository coverage settings: `exclude_text` / UI settings).
- Glob patterns (e.g. `**/node_modules/**`, `**/target/**`, `**/*_test.go`, `**/gen/**`); prefix
  `regex:` for regex.
- No exclusions ready → don't block; point to
  [Rules for adding Code-Coverage exclusions](https://harness.atlassian.net/wiki/spaces/CODE/pages/24067637442/Rules+for+adding+Code-Coverage+exclusions).

## `hcli cov upload` report auto-discovery

Scans `.`, then `coverage/`, `test/`, `tests/`, `jacoco/`, `build/reports/jacoco/test`,
`target/site/jacoco`, then **each top-level module directory**, then a recursive walk. Reports in
standard module paths need no `--file` flag. Test locally: `hcli cov analyze --file=<report>`.
