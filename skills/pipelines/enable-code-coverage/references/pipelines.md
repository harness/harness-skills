# Pipelines: classification, Track A, Track B, applying writes

## Classifying existing steps

Match each CI stage `Run` step `command` (case-insensitive):

| Class | Matches |
|---|---|
| unit-test | `pytest`, `go test`, `gradle test`, `gradlew test`, `mvn test`, `mvn verify`, `npm test`, `npm run test`, `yarn test`, `jest`, `vitest`, `ctest` |
| build | `gradle build`/`gradlew build` (no `test`), `mvn package`/`compile`, `go build`, `npm run build`, `make`, `docker build` |
| integration-test | `integ`, `integration`, `e2e`, `it test`, `verify -Pintegration` |

A step that builds and tests (e.g. `./gradlew build`) counts as the unit-test step. Several
unit-test steps → ask which to instrument.

**Parity with the central template:** does the pipeline do essentially the standard build, unit
test and coverage flow (`mvn test`, `go test ./...`, `npm test`, pytest)? Yes → offer to switch
(recommended: zero pipeline maintenance, standardised CI). Deployments, custom integration tests,
complex monorepo orchestration or multi-stage flows → Track A.

Switch prompt (one option in the batched question):
> "Your pipeline performs standard build and test steps matching `account.<centralisedTemplateId>`.
> 1. Switch to the centralised template (Recommended)
> 2. Extend your existing pipeline with HCC (add `account.codeCoverage` after the test step)"

## Track A — extend an existing pipeline

Add the step **immediately after the test step** in the same stage (reports must exist before upload). No env vars.

```yaml
- step:
    name: harnessCoverage
    identifier: harnessCoverage
    template:
      templateRef: account.codeCoverage
      versionLabel: v1
      templateInputs:
        type: Run
        spec:
          envVariables:
            patch_coverage_percent: "80"
```

CLI fallback for custom build systems (e.g. Bazel):

```bash
hcli cov upload --file=coverage.info
hcli cov wait-until --patch-gt=80 --timeout=5m
```

## Track B — inherit an account-level template

1. **Reuse check first** (same project): look for pipelines with `templateRef: account.centralised*`.
   Already targets this repo → reuse, verify triggers only. Targets another repo → mirror its
   connector/codebase/variables as the starting point (ask reuse vs sibling). None → continue.
2. Create the pipeline (template IDs in [config.md](config.md)):

```yaml
pipeline:
  name: <repo>-coverage-ci
  identifier: <repo>_coverage_ci
  projectIdentifier: <project>
  orgIdentifier: <org>
  template:
    templateRef: account.<centralisedTemplateId>
    versionLabel: v1
    templateInputs:
      properties:
        ci:
          codebase:
            build: <+input>
      variables:
        - name: REPO_NAME
          type: String
          value: <repo>
        - name: SOURCE_BRANCH
          type: String
          value: <+input>
        - name: TARGET_BRANCH
          type: String
          value: <+input>
        - name: SOURCE_SHA
          type: String
          value: <+input>
        - name: PR_NUMBER
          type: String
          value: <+input>
        - name: RUN_SONAR_SCAN
          type: String
          value: "false" # "true" if dual-running with Sonar
```

(These are pipeline variables of the template, not environment variables.)

## Applying pipeline writes

- Check `storeType` first. `REMOTE` (git-backed): `harness_update` commits to git — show diff,
  get chat approval. `INLINE`: applies immediately, no git history — flag it and get consent.
- Update:
  ```
  harness_update(resource_type="pipeline", resource_id=<id>, org_id=<org>, project_id=<project>,
                 body={ "yamlPipeline": "<full modified YAML incl. 'pipeline:' root>" })
  ```
  New pipelines: `harness_create` with the same body shape. If rejected, verify with
  `harness_schema(resource_type="pipeline")`.
