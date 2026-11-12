# Coverage report validation & per-language recipes

## 1. HCC analysis constraint

> **CRITICAL:** `hcli cov` can only analyse files and lines present in the uploaded coverage
> report(s). It does **not** read raw git source. Any file, package or submodule missing from the
> reports is invisible to HCC.

## 2. Multi-module detection

| Repository type | Indicators | Risk if not handled |
|---|---|---|
| Java Maven multi-module | Root `pom.xml` with `<modules><module>…` | Only root/one module reports; untested modules missing |
| Java/Kotlin Gradle multi-project | `settings.gradle[.kts]` with multiple `include(...)` | Only root project report; subprojects ignored |
| JS/TS monorepo | `package.json` `workspaces`, `pnpm-workspace.yaml`, `lerna.json`, `turbo.json` | Jest/Vitest only runs in root; packages skipped |
| Go multi-module / multi-package | `go.work`, subdirs with `go.mod`, many packages under `pkg/`/`cmd/` | `go test` without `./...` tests only the root package |
| Python monorepo | Several service dirs with `pyproject.toml`/`setup.py` | Pytest only runs one package |

When any of these apply (or when validating existing test commands), ask the user whether a report
is generated for each module.

## 3. Report format detection

| Language | Marker in test command | Format | Default filenames |
|---|---|---|---|
| Python | `--cov`, `pytest-cov`, `coverage run` | LCOV / Cobertura | `lcov.info`, `coverage.xml` |
| Java/Kotlin/Scala | `jacoco`, `jacocoTestReport`, `jacoco-maven-plugin`, `scoverage` | JaCoCo XML / Cobertura | `jacoco.xml`, `jacocoTestReport.xml`, `scoverage.xml` |
| Go | `-coverprofile`, `-covermode` | Go coverage | `coverage.out`, `cover.out`, `*.cov`, `*.out` |
| Node/JS/TS | `--coverage`, `nyc`, `c8` | LCOV | `lcov.info`, `coverage.info` |
| .NET/C# | `coverlet`, `--collect:"XPlat Coverage"` | Cobertura | `coverage.xml`, `cobertura.xml` |

Outcomes:
- Command already contains `hcli cov upload` → coverage already wired (idempotent early exit).
- Marker present, no `hcli cov upload` → **A**: reports work; go wire HCC.
- No marker, or modules missing reports → **B**: apply the recipe below.
- No unit-test step → **C**: build CI first.

## 4. Fix recipes (infer language/build system from the test command and repo files)

- **Java/Kotlin — Gradle:** command `./gradlew test jacocoTestReport`. Multi-project
  `build.gradle[.kts]`:
  ```kotlin
  subprojects {
      apply(plugin = "jacoco")
      tasks.withType<JacocoReport> {
          reports { xml.required.set(true) }
      }
      tasks.withType<Test> { finalizedBy("jacocoTestReport") }
  }
  ```
  (or a merged `jacocoRootReport` task if an aggregate is preferred). Report:
  `build/reports/jacoco/test/jacocoTestReport.xml` per subproject.
- **Java — Maven:** `mvn -B test` (or `mvn -B test jacoco:report` / `jacoco:report-aggregate`).
  Add `jacoco-maven-plugin` (`prepare-agent` + `report` goals) to the parent `<plugins>` or
  `<pluginManagement>` so all child modules emit reports. Report: `target/site/jacoco/jacoco.xml`.
- **Python (pytest):** `pytest tests/ --junitxml=test-results.xml --cov=<pkg> --cov-report=lcov:lcov.info -v`;
  ensure `pytest-cov` is in test dependencies. Report: `lcov.info`.
- **Node/JS/TS (Jest, monorepos):** single project
  `npx jest --coverage --coverageReporters=lcov --reporters=default`; monorepo
  `npm test --workspaces -- --coverage --coverageReporters=lcov` (or per workspace).
  Report: `coverage/lcov.info` per module.
- **Go:** `go test ./... -coverprofile=coverage.out -covermode=atomic` — `./...` is crucial so all
  subpackages/modules are tested. Report: `coverage.out`.
- **.NET/C#:** `dotnet test --collect:"XPlat Code Coverage" --results-directory ./coverage`; add the
  `coverlet.collector` package reference. Report: `coverage/**/coverage.cobertura.xml`.

## 5. Delivering a repo-side fix

Always show the exact diff in chat. Delivery options (asked in the batched question): open a PR
(branch `chore/enable-code-coverage`, apply recipe, commit
`chore: enable coverage reporting for hcli code coverage`, push, open the PR), manual instructions,
or skip (wire the step anyway; no data until reports exist).
