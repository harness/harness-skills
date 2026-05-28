---
name: sign-artifact
description: >-
  Add an Artifact Signing (SscaArtifactSigning) step to an existing Harness pipeline to Cosign-sign
  container or local-stage artifacts with keyless, key-based, or Vault signing. Supports Third-Party
  registries (Docker, ECR, GCR, GAR, ACR), Harness Artifact Registry (HAR), and Harness Local Stage
  artifacts. Place after image build/push; optionally upload .sig to the registry. Only works with
  existing pipelines. Use when asked to sign artifacts, add artifact signing, Cosign sign image,
  attach signature to registry, or configure SscaArtifactSigning.
  Trigger phrases: sign artifact, artifact signing, sign image, Cosign sign, add signing step,
  SscaArtifactSigning, attach signature, sign container image, HAR signing.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Sign Artifact

Add an **Artifact Signing** (`SscaArtifactSigning`) step to an existing Harness pipeline. The step
retrieves an artifact from a registry or local workspace, signs it with Cosign, and optionally pushes
the `.sig` signature file back to the registry.

This skill only works with **existing pipelines** — do not create standalone signing-only pipelines.

**Prerequisites:** Container images must be built and pushed (or available in registry) before signing.
Key-based signing requires Cosign key pair file secrets (`/create-secret`). Harness docs note that
**Deploy-stage signing is not yet supported** — prefer CI or Security stages.

Guide the user through a **step-by-step interactive wizard** (same UX as `/verify-sign`):

- Wizard: `references/interactive-wizard-flow.md`
- UI ↔ YAML: `references/artifact-signing-step.md`
- CD note: `references/cd-containerized-step-group.md`

---

## Interaction model (mandatory)

1. **One question per turn** — use `AskQuestion` when available; otherwise numbered options with `(Recommended)`.
2. **Opening message** — add Artifact Signing after build/push; mention keyless, key-based, Vault, and HAR.
3. **Progress breadcrumb** — after pipeline fetch:
   `Pipeline · Placement · Source · Details · Signing · Upload · Submit · Run`
4. **Record answers** — running summary; do not re-ask unless the user changes direction.
5. **Fetch before configure** — `harness_get` before placement/source questions.
6. **Show pipeline structure** — highlight build/push and existing `SscaArtifactSigning` steps.
7. **Infer connector from build/push** — skip connector question when unambiguous from YAML.
8. **Never guess image tags** — always ask for image in Phase 7.
9. **Confirm before write** — summary + `harness_update` only after user confirms.
10. **Auto-run after update** — `harness_execute` + monitor for CI-only changes when inputs inferrable.
11. **Phase 3 Placement is mandatory** — always run Phase 2 then Phase 3.
12. **Sequential with SBOM/SLSA** — if `SscaOrchestration` or `provenance` exists, place signing **after** those steps sequentially (Cosign registry race).
13. **Offer all three source tiles** — Third-Party, **Harness Artifact Registry (HAR)**, and Harness Local Stage (HAR is supported in YAML even when the UI screenshot shows only two tiles).
14. **Existing signing step** — if `SscaArtifactSigning` already exists, ask: update in place, add a second step, or abort. If existing step has `uploadSignature.upload: false` (or block missing) and user wants `.sig` in registry, set `upload: true`.
15. **Upload `.sig` defaults OFF in Harness** — UI checkbox **Attach signature to Artifact Registry** is unchecked by default. For container images, **always** set `uploadSignature.upload: true` unless the user explicitly opts out. Confirm this in Phase 9 and in the submit summary.
16. **Verify `.sig` after run** — when upload is enabled, check step logs for signature push success; see Troubleshooting if registry shows no signature tag.

Full phase prompts: `references/interactive-wizard-flow.md`.

---

## Instructions

### Wizard phases

| Phase | Breadcrumb | Action |
|-------|------------|--------|
| 0 | Pipeline | AskQuestion: pipeline URL ready? |
| 1 | Pipeline | Collect URL → `harness_get` |
| 2 | Pipeline | Display structure; note build/push + existing signing steps; flag missing `uploadSignature.upload: true` |
| 2b | Pipeline | If `SscaArtifactSigning` exists — AskQuestion: update, add second, or abort |
| 3 | Placement | **Mandatory** AskQuestion: stage + position + anchor push step (after build/push recommended) |
| 4 | Source | AskQuestion: Third-Party, HAR, or Local |
| 5 | Source | AskQuestion: registry provider (Third-Party only) |
| 6 | Details | Connector (skip if obvious) |
| 7 | Details | Image / registry fields; optional digest expression |
| 8 | Signing | AskQuestion: keyless, keybased, vault |
| 9 | Upload | AskQuestion: attach `.sig` to registry (container images only) |
| 10 | Submit | AskQuestion: confirm pipeline update |
| 11 | Run | Auto-trigger + monitor |

### Supported stage types

| Stage type | Placement notes |
|------------|-----------------|
| `CI` | **Recommended** — immediately after `BuildAndPush*` or image push step |
| `Security` | End of stage when signing pre-built registry images |
| `Deployment` | **Not supported** by Harness today — warn user; prefer CI signing |

### After the wizard — backend steps

#### Extract connectors from pipeline YAML

From `BuildAndPushDockerRegistry`, `BuildAndPushECR`, `BuildAndPushGCR`, `BuildAndPushGAR`,
`BuildAndPushACR`, Kaniko/`Run` push steps, `SscaOrchestration`, `SscaArtifactSigning`, or
`provenance` steps — reuse `connectorRef` / `connector`. Signing source uses `connector` (not
`connectorRef`).

#### Generate Artifact Signing step YAML

Use **only wizard answers**. Docker Third-Party uses `source.spec.image` (not `repo`).

**Docker Registry — key-based signing (Harness docs reference):**

```yaml
- step:
    identifier: artifactsigning
    name: Artifact Signing
    type: SscaArtifactSigning
    spec:
      source:
        type: docker
        spec:
          connector: lavakush07
          image: lavakush07/easy-buggy-app:v5
      signing:
        type: cosign
        spec:
          private_key: account.cosign_private_key
          password: account.cosign_password
      uploadSignature:
        upload: true
    timeout: 15m
```

**Keyless signing (Harness OIDC) — include upload when pushing `.sig`:**

```yaml
      signing:
        type: keyless
        spec:
          oidcProvider: harness
      uploadSignature:
        upload: true
```

**Non-Harness keyless OIDC** (requires account Connector for Keyless Signing):

```yaml
      signing:
        type: keyless
        spec:
          oidcProvider: non-harness
      uploadSignature:
        upload: true
```

**Harness Artifact Registry (HAR):**

```yaml
      source:
        type: har
        spec:
          registry: <har_registry_identifier>
          image: my-image:v5
```

**Harness Local Stage (non-container):**

```yaml
      source:
        type: local
        spec:
          workspace: <path_in_workspace>
          artifact_name: my-artifact.jar
          version: "1.0.0"
```

**No registry upload:** omit `uploadSignature` or set `upload: false`. Harness still stores signature
metadata internally — but external tools and registry-side verify need `upload: true`.

**Amazon ECR / GCR / GAR / ACR:** see `references/artifact-signing-step.md` — always include
`uploadSignature.upload: true` when user expects `.sig` in the registry.

#### Insert step into pipeline YAML

- Insert at Phase 3 placement — **after** build/push (or after SBOM/SLSA when present).
- Do not modify unrelated steps, variables, or failure strategies.
- Step identifier: `artifactsigning` (use `artifactsigning_2`, etc. if duplicate). CD Deploy placement
  is unsupported — do not use `_cd` suffix for signing steps.

#### Update pipeline via MCP

```
harness_update
  resource_type: pipeline
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  body: { yamlPipeline: "<updated pipeline YAML>" }
```

On validation errors, read the API message. Common fixes: `image` vs `repo`, `signing` vs `attestation`,
`private_key` / `password` secret refs for key-based cosign.

#### Auto-run pipeline (mandatory after successful update)

```
harness_execute
  resource_type: pipeline
  action: run
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  inputs: <branch/tag if codebase pipeline>
```

Poll `harness_get` (`execution`) every 20–30s. On failure, `harness_diagnose`.

**Skip auto-run** when: Security-only pipeline with missing branch inputs, manual-run pipeline, or
user chose not to run. Otherwise auto-run is mandatory.

**After successful signing with upload enabled:** confirm step logs mention signature upload. Cosign
stores signatures as OCI artifacts or `sha256-<digest>.sig` tags — they may not appear as a literal
`.sig` filename in the registry UI. See Troubleshooting if upload failed.

#### Provide summary

```
## Artifact Signing Configured

**Pipeline:** <pipeline_name>
**Step:** Artifact Signing (SscaArtifactSigning)
**Location:** Stage "<stage_name>", <position>
**Source:** docker — <connector> — <image>
**Signing:** Keyless (Harness OIDC) — or as configured
**Upload .sig:** Yes / No

**Execution:** <id> — <Success | Failed | Running>
**Execution URL:** <openInHarness>

**Signature:** Supply Chain tab + Chain of Custody

### Next Steps
1. If **Failed** or **no `.sig` in registry**, see Troubleshooting — confirm `uploadSignature.upload: true`
2. Add verification with `/verify-sign`
3. Add SBOM/SLSA **before** signing if not present (`/manage-supply-chain` or `SscaOrchestration` / `provenance`)
4. Automate with `/create-trigger`
```

---

## Examples

### After Docker build/push — key-based sign + upload .sig

```
/sign-artifact
Add artifact signing after docker push — lavakush07/easy-buggy-app:v5, key-based with account cosign secrets, upload signature
```

### Keyless on Harness Cloud

```
/sign-artifact
Use defaults — keyless Harness OIDC after Build_and_Push, attach signature to registry
```

### Harness Artifact Registry

```
/sign-artifact
Sign image my-service:v2 from Harness Artifact Registry registry-id prod-har — keyless
```

### Placement must be explicit

```
/sign-artifact
add signing to the pipeline
```

Agent must still run Phase 2 + Phase 3 — do not assume stage or skip placement.

### Fix missing `.sig` in registry

```
/sign-artifact
Signing step succeeded but no .sig in Docker Hub — update existing artifactsigning step to upload signature
```

Agent must inspect existing YAML for `uploadSignature`, set `upload: true`, ensure signing runs
**after** build/push sequentially, and re-run the pipeline.

---

## Performance Notes

- Only **existing pipelines** — do not create standalone signing pipelines.
- **Wizard UX is mandatory** — one question per turn; see `references/interactive-wizard-flow.md`.
- **Docker source uses `image`** — not `repo` (SLSA `provenance` uses `repo`; SBOM uses `image`).
- **Signing block is `signing`** — not `attestation` (SLSA generation) or `verifySign` (verification).
- **HAR is a first-class source** — `source.type: har` with `registry` + `image`; offer even if UI shows only Third-Party + Local tiles.
- **Deploy stage signing unsupported** — warn if user picks CD Deploy placement.
- **Upload .sig** — container images only; maps to `uploadSignature.upload: true`. Harness UI defaults
  this to **unchecked** — missing block = no registry upload.
- **One signing step = one image** — monorepos need multiple steps or sequential runs per image.
- **Key-based signing** — private key + password must be Harness **file secrets** (`/create-secret`).
- Do **not** use for dashboard-only SSCA config — use `/manage-supply-chain` instead.

---

## Troubleshooting

### Pipeline Not Found
- Verify org/project; `harness_list` (resource_type: `pipeline`).

### Connector Not Found
- Search build/push steps for `connectorRef`; `harness_search` for Docker registry connectors.

### Image Not Found / Invalid Reference
- Docker: single `image` string — e.g. `lavakush07/easy-buggy-app:v5`.
- HAR: `registry` identifier + `image` name with tag or digest.

### Signing Failed (Key-based)
- Verify file secrets exist and Cosign key is `ecdsa-p256`.
- Try `signing.type: cosign` with `private_key` + `password` if `keybased` fails validation.
- JFrog registries need extra connector permissions for signature upload.

### Signing Failed (Keyless)
- Requires Harness CI execution context; configure Connector for Keyless Signing for non-harness OIDC.

### `.sig` Not in Registry (step succeeded)
Most common cause: **`uploadSignature.upload` is missing or `false`**. Harness defaults the UI checkbox
**Attach signature to Artifact Registry** to unchecked — signature is stored in Harness only.

**Fix checklist:**
1. Set `uploadSignature.upload: true` on the `SscaArtifactSigning` step (container images only).
2. Re-run pipeline after updating YAML — existing successful runs do not retroactively upload.
3. Confirm signing step uses the **same connector and image tag** as the build/push step.
4. Place signing **sequentially after** build/push — not in parallel with push, SBOM, or SLSA.
5. Check step logs for upload/push errors (403 = connector lacks write permission to push signature tags).
6. **Docker Hub / OCI registries:** Cosign pushes signatures as separate manifest tags (e.g.
   `sha256-<digest>.sig`) or OCI referrers — not always visible as a `.sig` file in the UI. Use
   `cosign verify` CLI or Harness Supply Chain tab to confirm.
7. **JFrog Artifactory:** connector needs permission to push signature artifacts alongside the image.
8. **ECR/GCR/GAR/ACR:** connector must have push permissions; use digest pinning if tag was overwritten
   between push and sign.

### SBOM / SLSA / Signing Race
- Symptom: missing `.sig` or attestation in registry — steps ran in parallel.
- Fix: reorder — build/push → SBOM → SLSA → signing sequentially in the same stage.

### Existing Signing Step Without Upload
- Inspect YAML: if `uploadSignature` is absent, Harness treated upload as disabled.
- Ask user: update existing step with `upload: true` vs add new step.

### Deploy Stage Not Supported
- Harness docs: artifact signing in Deploy stage is on the roadmap — use CI stage instead.

### YAML Validation Errors
- Step `type` must be `SscaArtifactSigning`.
- Docker source requires `connector` + `image` (not `repo`).
- `uploadSignature.upload` is boolean — UI checkbox "Attach signature to Artifact Registry".

### Skipped Placement
- Re-run wizard from Phase 2; ask stage + position explicitly.

### Auto-run Failed
- Map branch/tag into `inputs` for codebase pipelines.

### MCP Errors
- `CONNECTOR_NOT_FOUND` — verify connector identifier.
- `ACCESS_DENIED` — PAT needs pipeline edit permission.
