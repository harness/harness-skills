---
name: enable-code-coverage
description: >-
  Onboard a repository to Harness Code Coverage (HCC): inspect test setups, wire the codeCoverage step
  immediately after unit tests, verify multi-module coverage reports, set up PR and baseline triggers,
  and configure exclusions. Use when asked to enable code coverage, onboard a repository to code coverage,
  add coverage gating, or set up PR patch coverage checks. Trigger phrases: enable code coverage,
  onboard code coverage, add code coverage, patch coverage gate, baseline coverage.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  summary: Onboard repositories to Harness Code Coverage with PR gating and baseline triggers
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Enable Code Coverage

Onboard any repository or pipeline to Harness Code Coverage (HCC) end-to-end. The skill inspects the build and test setup, verifies report generation across all modules, adds the `codeCoverage` step immediately after tests, and configures PR and default-branch baseline triggers.

Detail lives in `references/` — read a reference only when needed:

| Reference | Read when |
|---|---|
| [config.md](references/config.md) | Standard thresholds, status checks, auto-discovery order |
| [language-recipes.md](references/language-recipes.md) | Multi-module detection, report formats, build file recipes |
| [pipelines.md](references/pipelines.md) | Step classification, step placement rules, wiring YAML |
| [triggers.md](references/triggers.md) | Checking or creating PR and baseline push triggers |
| [troubleshooting.md](references/troubleshooting.md) | Diagnosing errors or symptom-to-fix mapping |

## Instructions

Follow this structured checklist:

```
Enable code coverage — <repo>
- [ ] 1. Discover (read-only, cached) & early-exit checks
- [ ] 2. Classify onboarding path & step placement
- [ ] 3. Validate coverage report generation (every module)
- [ ] 4. Plan & decisions (one batched approval)
- [ ] 5. Apply (pipeline, repo fix, triggers)
- [ ] 6. Verify & prerequisites
- [ ] 7. Quality-check summary
```

### Step 1: Discover & Early-Exit Checks
1. Accept a repository identifier, pipeline identifier, or Harness URL.
2. Auto-extract `org_id` and `project_id`. Retrieve default branch (`main` or `master`), git connector, and existing PR checks via `harness_list(resource_type="pr_check")`.
3. Fetch candidate pipeline YAML via `harness_list` and `harness_get`.
4. Early exits:
   - If test command already contains `hcli cov upload` or uses `codeCoverage`, skip wiring.
   - If PR trigger and baseline trigger exist, skip trigger creation.

### Step 2: Classify Onboarding Path & Step Placement
- **Step Placement Rule:** The `codeCoverage` step must be placed **immediately after the test step** within the same stage (reports must exist before upload). Never place it in parallel before tests run.
- **Track A (Extend Existing):** Insert the `codeCoverage` step (from `templates/codeCoverage.yaml`) immediately after the unit-test step in the existing pipeline.
- **Track B (No CI Pipeline Exists):** Offer to scaffold a standard build/test/coverage pipeline for the detected language.

### Step 3: Validate Coverage Report Generation (Critical)
HCC analyzes **only** lines present in uploaded coverage reports; it does not analyze raw git source. Verify that every module in multi-module setups (Maven `<modules>`, Gradle `subprojects`, npm `workspaces`, `go test ./...`, pytest) produces a supported report format:
- Java/Kotlin: JaCoCo XML (`jacoco.xml`)
- Python, JS/TS: LCOV (`lcov.info`) or Cobertura (`coverage.xml`)
- Go: Go coverage profile (`coverage.out`)

If any module lacks reports, prepare the build-file fix using recipes in `references/language-recipes.md`.

### Step 4: Plan & Batched Approval
Show all proposed diffs together (pipeline YAML, trigger YAMLs, repo PR diff). Ask for explicit chat approval before making any changes. In dry-run mode, stop here and produce the plan summary.

### Step 5: Apply Approved Changes
- **Pipeline:** Update via `harness_update(resource_type="pipeline", body={ "yamlPipeline": "<YAML string>" })`.
- **Repo-side fix:** If approved, open a PR with the required build-file configuration.
- **Triggers:** Create the missing PR trigger (`PullRequest` webhook, 80% patch gate) and Baseline trigger (`Push` webhook on default branch) via `harness_create(resource_type="trigger")`.

### Step 6: Verify & Prerequisites
- Ensure Code Coverage is enabled on the account.
- If `ACCESS_DENIED` is returned, flag the missing permission and resource scope directly to the user.
- Success criteria: `coverage-patch` check appears on PRs; baseline trigger runs on merges to the default branch.

### Step 7: Quality-Check Summary
Always conclude with this fixed summary:

```
Quality check — <repo>   [mode: normal | dry-run]

1. PR coverage
   - Patch coverage (coverage-patch): working | failing | not yet verified | planned — <evidence>
   - Project coverage (coverage-project): working | failing | not yet verified | planned — <evidence>
   - PR trigger: existing | created (<id>) | planned
   - Modules with reports: <n>/<total> — <missing modules, if any>

2. Branch scans / repo coverage (baseline)
   - Baseline trigger on <default branch>: existing | created (<id>) | planned
   - Baseline execution: <link + status> | pending until a PR is merged
   - Monitoring: <user will monitor the first post-merge run | offered to check it after merge>

3. Fixes made
   - Repo-side fix: PR <link> | manual instructions given | none needed
   - Pipeline: PR/commit <link> (REMOTE) | inline update — <diff summary> | none
   - Triggers: created <ids> (inline, no PR) | already existed
   - Outstanding prerequisites: <e.g. account coverage enablement, deferred exclusions>
```

## Examples

### Example 1: Onboard by Pipeline URL
```text
/enable-code-coverage https://app.harness.io/ng/account/l7B_kbSEQD2wjrM7PShm5w/all/orgs/default/projects/demo/pipelines/build_pipeline
```
The agent inspects the pipeline, detects the `mvn test` step, confirms JaCoCo report generation, drafts the `codeCoverage` step immediately after test execution, prepares PR and baseline triggers, and presents diffs for approval.

### Example 2: Dry Run on a Repository
```text
/enable-code-coverage Dry run on repository analytics-service in org default, project core.
```
The agent inspects the repository and pipelines, validates multi-module coverage outputs, and prints the plan and quality summary without performing any write calls.

## Performance Notes

- Always inspect existing checks via `harness_list(resource_type="pr_check")` to avoid redundant runs.
- Keep the coverage step within the test stage to reuse the checkout and workspace without re-downloading source.
- Configure exclusions in the Code Coverage module settings rather than cluttering pipeline YAML.

## Troubleshooting

| Symptom | Root Cause | Fix |
|---|---|---|
| Coverage shows 0% | Reports not generated or not placed in standard auto-discovery paths | Verify test tool output matches paths in `references/config.md`; check module test commands |
| `ACCESS_DENIED` | Missing API permissions | Flag the missing permission (e.g. Pipeline Edit or Trigger Create) directly to the user |
| Baseline coverage missing | Default branch has no baseline trigger | Create the baseline push trigger; baseline populates after the first post-merge run |
| Pipeline update rejected | Invalid YAML payload | Verify pipeline YAML using `harness_schema(resource_type="pipeline")` |
