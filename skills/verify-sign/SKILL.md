---
name: verify-sign
description: >-
  Add an Artifact Verification (SscaArtifactVerification) step to an existing Harness pipeline to
  verify Cosign signatures on container or local-stage artifacts. Supports CI, Security, and CD
  Deploy (containerized step group). Supports Third-Party registries (Docker, ECR, GCR, GAR, ACR),
  Harness Artifact Registry (HAR), and Harness Local Stage artifacts. Only works with existing
  pipelines. Use when asked to verify signed artifacts, verify artifact signature, verify-sign,
  validate Cosign signature, or configure SscaArtifactVerification.
  Trigger phrases: verify sign, verify artifact, artifact verification, verify signature, verify-sign,
  SscaArtifactVerification, verify signed image, verify Cosign, HAR verification.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Verify Sign

Add an **Artifact Verification** (`SscaArtifactVerification`) step to an existing Harness pipeline.
The step verifies Cosign signatures on artifacts — typically immediately after `SscaArtifactSigning`.

This skill only works with **existing pipelines** — do not create standalone verification-only pipelines.

**Prerequisites:** Artifact must already be signed (typically via `/sign-artifact` /
`SscaArtifactSigning`). Key-based verify requires the Cosign **public** key file secret matching the
signing private key (`/create-secret`). If signing did not upload `.sig` to the registry, Harness
pulls the signature from its database during verification.

**Supported stages:** CI, Security, and CD (`Deployment` in containerized step group before deploy).

Guide the user through a **step-by-step interactive wizard** (same UX as `/sign-artifact`):

- Wizard: `references/interactive-wizard-flow.md`
- UI ↔ YAML: `references/artifact-verification-step.md`
- CD containerized step groups: `references/cd-containerized-step-group.md`

---

## Interaction model (mandatory)

1. **One question per turn** — use `AskQuestion` when available; otherwise numbered options with `(Recommended)`.
2. **Opening message** — add Artifact Verification; mention signing prerequisite + HAR support.
3. **Progress breadcrumb** — after pipeline fetch:
   `Pipeline · Placement · Source · Details · Verify · Submit`
4. **Record answers** — running summary; do not re-ask unless the user changes direction.
5. **Fetch before configure** — `harness_get` before placement/source questions.
6. **Show pipeline structure** — highlight `SscaArtifactSigning` and connectors.
7. **Infer source from signing** — when one `SscaArtifactSigning` step exists, reuse its source. If
   multiple exist, ask which step to mirror.
8. **Never guess image tags** — default from signing step; ask if ambiguous.
9. **Confirm before write** — summary + `harness_update` only after user confirms.
10. **Stop after update** — after successful `harness_update`, provide a configuration summary and
    point the user to `/run-pipeline` to execute. Do **not** call `harness_execute`, poll
    executions, or run `harness_diagnose` in this skill (same pattern as `/configure-repo-scan`).
11. **CD on CI-only pipeline** — do not reject CD verify; run Phase 3b to add Deploy stage + containerized group.
12. **Verify method must match signing** — keyless ↔ keyless, keybased/cosign ↔ public key from same key pair.
13. **Offer all three source tiles** — Third-Party, **HAR**, and Harness Local Stage.
14. **List all connectors in Phase 6** — same rules as `/sign-artifact`: `harness_list` with
    `filters.type`, all scopes, `size: 100`, paginate; never hand-pick a subset. See wizard Phase 6.
15. **List all infrastructure in Phase 3b** — `harness_list` per environment with
    `filters.environment_id`; never show only the infra for one pre-selected environment.
16. **CD image defaults to `<+artifact.image>`** — for Deploy-stage verify, recommend the service
    artifact expression over a static tag from signing. Warn when static image ≠ service default tag.
17. **Preflight delegates before CD update** — `harness_list(resource_type="delegate")` or
    `harness_execute(test_connection)` on the K8s connector used in `stepGroupInfra`. Abort or warn if
    `DELEGATE_NOT_AVAILABLE` is likely (connector has `delegateSelectors` with no active delegate).
18. **CD Deploy stage YAML requirements** — new Deploy stages need `failureStrategies: StageRollback`,
    `rollbackSteps` with `K8sRollingRollback` + `spec: {}`, and CI stages need `MarkAsFailure` when
    missing. See `references/cd-containerized-step-group.md`.

Full phase prompts: `references/interactive-wizard-flow.md`.

---

## Instructions

### Wizard phases

| Phase | Breadcrumb | Action |
|-------|------------|--------|
| 0 | Pipeline | AskQuestion: pipeline URL ready? |
| 1 | Pipeline | Collect URL → `harness_get` |
| 2 | Pipeline | Display structure; note missing `SscaArtifactSigning` |
| 3 | Placement | AskQuestion: after signing, CD before deploy, etc. |
| 3b | Placement (CD) | Service, env, infra, step group if new Deploy stage |
| 4 | Source | Infer from signing or pick registry tile |
| 5 | Source | Registry provider (Third-Party only) |
| 6 | Details | Connector — list **all** via `harness_list` + `filters.type` (skip if obvious) |
| 7 | Details | Image / artifact fields (default from signing) |
| 8 | Verify | AskQuestion: verify signature method |
| 9 | Submit | AskQuestion: confirm pipeline update |

After Phase 9 `confirm` → insert step, `harness_update`, then provide summary (do not run the pipeline).

### Supported stage types

| Stage type | Step `type` | Placement notes |
|------------|-------------|-----------------|
| `CI` | `SscaArtifactVerification` | **After** `SscaArtifactSigning` in the same stage |
| `Deployment` | `SscaArtifactVerification` | Containerized step group; **before** deploy |
| `Security` | `SscaArtifactVerification` | After signing when artifact is in registry |

### CD edge case

If no `Deployment` stage and user chose CD verify:

> No CD Deploy stage yet. We can add a **Deployment** stage with a **containerized step group** and
> place **Artifact Verification** before deploy.

Run Phase 3b (service, environment, infrastructure, `stepGroupInfra`) — see
`references/cd-containerized-step-group.md`.

#### Preflight before CD stage write

1. **`harness_get`** the K8s connector used in `stepGroupInfra` — note `delegateSelectors`.
2. **`harness_list(resource_type="delegate")`** — confirm an **active** delegate matches required
   selectors (e.g. `ssca-prod2-at`). Warn before `harness_update` if none match.
3. **`harness_get(resource_type="service")`** — note primary artifact tag; if user chose a static
   verify image, warn when it differs from the service default.

#### CD Deploy stage YAML (append to pipeline)

When adding a new Deploy stage, include **all** required blocks (API rejects incomplete YAML):

```yaml
    - stage:
        name: Deploy
        identifier: Deploy
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            serviceRef: <service_id>
          environment:
            environmentRef: <env_id>
            infrastructureDefinitions:
              - identifier: <infra_id>
          execution:
            steps:
              - stepGroup:
                  identifier: scs_before_deploy
                  name: Supply Chain Security
                  stepGroupInfra:
                    type: KubernetesDirect
                    spec:
                      connectorRef: <k8s_connector>
                      namespace: <namespace>
                  steps:
                    - step:
                        identifier: artifactverification_cd
                        name: Artifact Verification
                        type: SscaArtifactVerification
                        spec:
                          source:
                            type: docker
                            spec:
                              connector: <registry_connector>
                              image: <+artifact.image>
                          verifySign:
                            type: keyless
                            spec:
                              oidcProvider: harness
                        timeout: 15m
              - step:
                  identifier: rolling_deployment
                  name: Rolling Deployment
                  type: K8sRollingDeploy
                  spec:
                    skipDryRun: false
                  timeout: 10m
            rollbackSteps:
              - step:
                  identifier: rollback
                  name: Rollback
                  type: K8sRollingRollback
                  spec: {}
                  timeout: 10m
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: StageRollback
```

Also ensure existing CI stages have `failureStrategies: MarkAsFailure` when missing.

#### Check prerequisites

1. **Artifact signing** — pipeline contains `SscaArtifactSigning` (or user confirms signature exists).
2. **Public key secret** (key-based) — file secret with Cosign public key matching signing private key.

#### Extract context from pipeline YAML

From `SscaArtifactSigning` (if present), copy source and map signing → verification:

| Signing | Verification |
|---------|--------------|
| `source.type: docker` | same `source.type: docker` |
| `source.spec.image` | same `source.spec.image` |
| `source.spec.connector` | same `source.spec.connector` |
| `source.type: har` | same `source.type: har` + `registry` + `image` |
| `signing.type: keyless` | `verifySign` keyless (match OIDC provider) |
| `signing.type: cosign` / `keybased` | `verifySign` with **public** key secret |

#### Generate Artifact Verification step YAML

**CI — Docker Registry, key-based verify (Harness docs):**

```yaml
- step:
    identifier: artifactverification
    name: Artifact Verification
    type: SscaArtifactVerification
    spec:
      source:
        type: docker
        spec:
          connector: lavakush07
          image: lavakush07/easy-buggy-app:v5
      verifySign:
        type: cosign
        spec:
          public_key: account.cosign_public_key
    timeout: 15m
```

**Keyless verify** (when signing used keyless Harness OIDC):

```yaml
      verifySign:
        type: keyless
        spec:
          oidcProvider: harness
```

If API validation rejects flat `keyless`, retry nested `cosign` wrapper — see
`references/artifact-verification-step.md`.

**HAR verify:**

```yaml
      source:
        type: har
        spec:
          registry: prod_har
          image: my-service:v3
```

**CD Deploy** — same step type inside containerized `stepGroup`; use `<+artifact.image>` for `image`
when verifying service artifacts.

Full provider mapping: `references/artifact-verification-step.md`.

#### Insert step into pipeline YAML

- Insert at Phase 3 placement — **after** `artifactsigning` when possible.
- Do not modify unrelated steps.
- Step identifier: `artifactverification` (use `artifactverification_cd` in CD when CI already has one).
- **CD:** inside containerized step group only.

#### Update pipeline via MCP

```
harness_update
  resource_type: pipeline
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  body: { yamlPipeline: "<updated pipeline YAML>" }
```

On validation errors, check `verifySign` shape, `image` field, and public key secret refs.

#### Provide summary

Report the results to the user (same pattern as `/configure-repo-scan` — do **not** execute the pipeline):

```
## Artifact Verification Configured

**Pipeline:** <pipeline_name>
**Step:** Artifact Verification (SscaArtifactVerification)
**Location:** Stage "<stage_name>", <position>
**Source:** docker — <connector> — <image>
**Verify signature:** Keyless (Harness OIDC) — or as configured

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/ci/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

**Note:** Review the Artifact Verification step in Pipeline Studio to adjust Advanced settings.

### Next Steps
1. Run the pipeline via `/run-pipeline` to verify artifact verification executes successfully
2. If the run fails, diagnose with `/debug-pipeline`
3. View verification outcome on the execution **Supply Chain** tab
4. If **Failed**, confirm verify method matches signing; check public key for keybased
5. Add signing with `/sign-artifact` if signature was missing — ensure `uploadSignature.upload: true`
6. Add SBOM/SLSA if not present (`/manage-supply-chain` or pipeline `SscaOrchestration` / `provenance`)
7. Automate with `/create-trigger`
```

**CD pipelines:** note in the summary if runtime inputs (service artifact, environment, infrastructure,
artifact tag/digest) will be required at run time — the user provides those via `/run-pipeline` or
Harness UI Run. When running CI+CD, check `runtime_input_template` — service `primaryArtifactRef: <+input>`
may need artifact tag/digest in `inputs` even when the template only shows `build`.

---

## Examples

### Verify after Artifact Signing

```
/verify-sign
Add artifact verification after artifactsigning — public key account.cosign_public_key
```

### CD before deploy

```
/verify-sign
Verify signed artifact in deploy stage before K8s rolling deploy — keyless verify
```

### HAR verification

```
/verify-sign
Verify signature for HAR image payment-service:v2 — same registry as signing step
```

### Keyless verify (matches keyless signing)

```
/verify-sign
Verify with keyless Harness OIDC — same image as signing step
```

---

## Performance Notes

- Only **existing pipelines** (may append Deploy stage).
- **Wizard UX mandatory** — one question per turn.
- **Reuse signing source** — same lowercase `source.type` and `image` as `SscaArtifactSigning`.
- **Field is `verifySign`** (camelCase) — not `verify_attestation` (SLSA) or `signing`.
- **HAR is a first-class source** — `source.type: har`; offer even if UI shows only two tiles.
- **CD verification supported** — containerized step group only; signing in Deploy is not supported.
- **Do not execute pipelines** in this skill — use `/run-pipeline` after configuration (same as `/configure-repo-scan`).
- Pair with `/sign-artifact` (sign) — verify method must match signing.

---

## Troubleshooting

### No Artifact Signing Step
- Add `/sign-artifact` first with signature upload or Harness DB signature storage.
- Scan for `SscaArtifactSigning` or `identifier: artifactsigning`.

### Signature Verification Failed
- Verify method must match signing (`keyless` vs `keybased`/`cosign`).
- Keybased: use **public** key secret (signing uses **private** key).
- If `.sig` not in registry, signing step may not have set `uploadSignature.upload: true` (Harness
  default is unchecked). Update signing step and re-run, or rely on Harness DB signature storage.

### Multiple Signing Steps
- Ask user which `SscaArtifactSigning` step to mirror for source, image, and verify method.

### Vault Verify Failed
- Confirm Vault connector and public key path match the signing `secret-manager` block.

### Wrong Image
- CI: use same `image` as signing step `source.spec.image`.
- CD: **default to** `<+artifact.image>` — static signing tag (e.g. `:v5`) may not match service
  artifact (e.g. `:v24`) and verification will fail or verify the wrong image.

### CD Deploy Failed — No Delegate (`DELEGATE_NOT_AVAILABLE`)
- Symptom: Deploy fails immediately; message mentions missing delegate or selector mismatch
  (e.g. `Delegate(s) don't have selectors [ssca-prod2-at]`).
- Fix: start a delegate with matching selectors (`/manage-delegates`), or pick infra/K8s connector
  backed by an active delegate. Re-run after delegate is healthy.

### CD YAML Validation Errors (new Deploy stage)
- `failureStrategies: is missing` — add `StageRollback` on the Deploy stage.
- `rollbackSteps[0].step.spec: is missing` — `K8sRollingRollback` requires `spec: {}`.
- See full template in `references/cd-containerized-step-group.md`.

### YAML Validation Errors
- Step `type` must be `SscaArtifactVerification`.
- Docker source requires `connector` + `image` (not `repo` or `image_path`).
- `verifySign`: prefer flat `type: keyless`; keybased uses `type: cosign` + `public_key`.
- `DUPLICATE_IDENTIFIER` — rename `artifactverification`.

### CD Step Errors
- Place inside `stepGroup` with `stepGroupInfra` — not top-level `execution.steps`.
- See `references/cd-containerized-step-group.md`.

### User Chose CD on CI-Only Pipeline
- Expected — run Phase 3b; do not force CI-only unless user changes direction.

### Incomplete connector / infrastructure list
- Use `harness_list` + `filters: { type: "DockerRegistry" }` (not `harness_search` or
  `params.filterType`). Query project, org, and account scopes. For infrastructure, list per
  environment with `filters: { environment_id: "<env>" }` — see wizard Phase 3b and Phase 6.

### Pipeline Run Failed
- Use `/run-pipeline` to execute and `/debug-pipeline` to diagnose failures
- Missing runtime inputs: provide branch/tag, artifact tag/digest, or deploy inputs via `/run-pipeline` or Harness UI Run

### MCP Errors
- `CONNECTOR_NOT_FOUND` — verify connector in Project Settings; re-run scoped `harness_list`.
- `ACCESS_DENIED` — PAT needs pipeline edit permission.
- **`harness_update` timeout** — retry once; provide YAML for manual paste if MCP keeps timing out.
