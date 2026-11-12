# Troubleshooting

| Symptom | Root cause | Fix |
|---|---|---|
| Partial module coverage / modules missing | HCC only analyses files in uploaded reports, not git source | Run tests + coverage plugins on all modules (Maven parent POM plugin, Gradle `subprojects`, `go test ./...`); confirm every module emits a report ([language-recipes.md](language-recipes.md)) |
| No baseline on default branch / empty trend graph | Missing baseline trigger | Create the baseline push trigger ([triggers.md](triggers.md)); data appears after the first merge runs |
| "Coverage report not found" | Report path/filename not in auto-discovery | Write the report to a standard dir (`coverage/`, `test/`, `build/reports/jacoco/test`, `target/site/jacoco`) or pass `--file`; test with `hcli cov analyze --file=<report>` |
| Patch gate passes but no patch data | Build ran on a branch, not a PR | `wait-until` skips patch gates on non-PR runs by design; ensure the PR trigger exists |
| `--target-scope is not supported for Harness Code` | Flag passed on an internal Harness Code repo | Remove the flag; coverage is stored on the repo's scope automatically |
| `hcli: command not found` | Account enablement missing (no env vars are required) | Confirm Code Coverage is enabled for the account with Harness Support (`support@harness.io`) / CXE, and the step uses `account.codeCoverage` or the account-level template |
| `ACCESS_DENIED` | Missing API permissions | Flag the exact missing permission and resource scope directly to the user; contact account/project admin |
| Pipeline template resolution error | Account template identifier mismatch | Verify the template exists at account scope (`templateRef: account.<id>`, see [config.md](config.md)) and `versionLabel` is correct |
| Pipeline update rejected | Wrong body format | Pass `{ "yamlPipeline": "<string>" }`, not nested JSON; verify with `harness_schema(resource_type="pipeline")` |
| "Nothing to change" | `hcli cov upload` already present | Already onboarded — idempotent early exit |
