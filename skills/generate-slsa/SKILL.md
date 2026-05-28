---
name: generate-slsa
description: >-
  Add a SLSA Generation step (YAML type: provenance) to an existing Harness pipeline to generate SLSA
  provenance and optionally attest with Cosign (keyless, key-based, or Vault). Supports container
  images (Docker, ECR, GCR, GAR, ACR, HAR) and Harness Local Stage artifacts. Place after image
  build/push; run sequentially after SBOM steps, not in parallel. Only works with existing pipelines.
  Use when asked to generate SLSA, add SLSA provenance, SLSA Generation step, attest SLSA, or
  configure SLSA Level 3 provenance in a pipeline.
  Trigger phrases: generate SLSA, SLSA generation, add SLSA step, SLSA provenance, attest SLSA,
  SlsaGeneration, provenance step, SLSA attestation, add provenance step.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Generate SLSA

Add a **SLSA Generation** step to an existing Harness pipeline to generate SLSA provenance and
optionally attest/sign the `.att` file in the container registry. Pipeline YAML uses
`type: provenance` (UI label: SLSA Generation; do not use `SlsaGeneration` — API rejects it).

This skill only works with **existing pipelines** — do not create standalone SLSA-only pipelines.

**Prerequisites:** Image must be built and pushed (or available in registry) before SLSA runs.
Key-based attestation requires Cosign key pair secrets (`/create-secret`). Harness Cloud builds
enable SLSA Level 3 provenance when using hosted infrastructure.

Guide the user through a **step-by-step interactive wizard** (same UX as `/configure-repo-scan`):

- Wizard: `references/interactive-wizard-flow.md`
- UI ↔ YAML: `references/slsa-generation-step.md`
- CD containerized step groups: `references/cd-containerized-step-group.md`

---

## Interaction model (mandatory)

1. **One question per turn** — use `AskQuestion` when available; otherwise numbered options with `(Recommended)`.
2. **Opening message** — add SLSA Generation after image build/push; mention attestation options.
3. **Progress breadcrumb** — after pipeline fetch:
   `Pipeline · Placement · Source · Details · Attestation · Submit · Run`
4. **Record answers** — running summary; do not re-ask unless the user changes direction.
5. **Fetch before configure** — `harness_get` before placement/source questions.
6. **Show pipeline structure** — highlight build/push steps and existing `provenance` / `SscaOrchestration` steps (UI: SLSA Generation).
7. **Infer connector from build/push** — skip connector question when unambiguous from YAML.
8. **Never guess image tags** — always ask for image/repo in Phase 7.
9. **Confirm before write** — summary + `harness_update` only after user confirms.
10. **Auto-run after update** — `harness_execute` + monitor for CI-only changes when inputs inferrable.
11. **Phase 3 Placement is mandatory** — always run Phase 2 then Phase 3, even with one CI stage or prior session context.
12. **Sequential with SBOM** — if `SscaOrchestration` exists, place SLSA **after** it; never parallel (Cosign race).
13. **CD path** — Deploy stage steps go inside containerized `stepGroup` only — see CD reference.

Full phase prompts: `references/interactive-wizard-flow.md`.

---

## Instructions

### Wizard phases

| Phase | Breadcrumb | Action |
|-------|------------|--------|
| 0 | Pipeline | AskQuestion: pipeline URL ready? |
| 1 | Pipeline | Collect URL → `harness_get` |
| 2 | Pipeline | Display structure; note build/push + SBOM steps |
| 3 | Placement | **Mandatory** AskQuestion: stage + position (after build/push recommended) |
| 3b | Placement (CD) | Service, env, infra, step group if new Deploy stage |
| 4 | Source | AskQuestion: Third-Party, HAR, or Local |
| 5 | Source | AskQuestion: registry provider (Third-Party only) |
| 6 | Details | Connector (skip if obvious) |
| 7 | Details | Image/repo; optional digest expression |
| 8 | Attestation | AskQuestion: keyless, keybased, vault, or none |
| 9 | Submit | AskQuestion: confirm pipeline update |
| 10 | Run | Auto-trigger + monitor |

### Supported stage types

| Stage type | Placement notes |
|------------|-----------------|
| `CI` | **Recommended** — immediately after `BuildAndPush*` or image push `Run` step |
| `Deployment` | Containerized step group only; before deploy — uncommon for generation |
| `Security` | End of stage when scanning pre-built registry images |

### After the wizard — backend steps

#### Extract connectors from pipeline YAML

From `BuildAndPushDockerRegistry`, `BuildAndPushECR`, `Run`, `Plugin`, `SscaOrchestration`,
`provenance` (SLSA Generation), or `SscaArtifactSigning` steps — reuse `connectorRef` / `connector`.

#### Generate SLSA step YAML

Use **only wizard answers**. Default attestation: keyless Harness OIDC when user chose defaults.

**Docker Registry — matches reference UI (key-based attestation):**

```yaml
- step:
    identifier: slsageneration
    name: slsa-generation
    type: provenance
    spec:
      source:
        type: docker
        spec:
          connector: lavakush07
          repo: lavakush07/easy-buggy-app:blog
      attestation:
        type: keybased
        spec:
          privateKey: account.cosign_private_key
          password: account.cosign_password
    timeout: 15m
```

**Keyless attestation (default for “use defaults”):**

```yaml
      attestation:
        type: keyless
        spec:
          oidcProvider: harness
```

**With digest from Build and Push:**

```yaml
      source:
        type: docker
        spec:
          connector: <docker_registry_connector>
          repo: <org>/<repo>:<tag>
          digest: <+pipeline.stages.<stage>.spec.execution.steps.<build_step>.output.outputVariables.digest>
```

**Amazon ECR:**

```yaml
      source:
        type: ecr
        spec:
          connector: <registry_connector>
          image: <repo/name>
          region: <aws_region>
          account: <aws_account_id>
```

**Google GCR / GAR / Azure ACR / HAR / Local:** see `references/slsa-generation-step.md`.

**No attestation:** omit `attestation` block.

#### Insert step into pipeline YAML

- Insert at Phase 3 placement — **after** build/push (or after `generate_sbom` when both exist).
- Do not modify unrelated steps, variables, or failure strategies.
- Step identifier: `slsageneration` (suffix `_cd` in CD when CI already has one).
- **CD:** inside containerized `stepGroup.steps` only.

#### Update pipeline via MCP

```
harness_update
  resource_type: pipeline
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  body: { yamlPipeline: "<updated pipeline YAML>" }
```

On validation errors, read the API message, fix fields (often `repo` vs `image`, attestation spec), retry.

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

Skip auto-run for new CD Deploy stages when service/env/infra inputs are missing.

#### Provide summary

```
## SLSA Generation Configured

**Pipeline:** <pipeline_name>
**Step:** SLSA Generation (`provenance`)
**Location:** Stage "<stage_name>", <position>
**Source:** docker — <connector> — <repo/image>
**Attestation:** Key-based (account.cosign_private_key) — or as configured

**Execution:** <id> — <Success | Failed | Running>
**Execution URL:** <openInHarness>

**Provenance:** Supply Chain tab + SCS Artifacts

### Next Steps
1. If **Failed**, verify image exists in registry and Cosign secrets are valid file secrets
2. Add SLSA verification with `/enforce-slsa`
3. Pair with `SscaOrchestration` (Generate SBOM) — run SBOM then SLSA sequentially
4. Automate with `/create-trigger`
```

---

## Examples

### After Docker build/push — key-based attestation (reference UI)

```
/generate-slsa
Add SLSA Generation to my CI pipeline after docker push — lavakush07/easy-buggy-app:blog, key-based attest with account cosign secrets
```

### Keyless defaults on Harness Cloud

```
/generate-slsa
Use defaults — keyless Harness OIDC after Build_and_Push step
```

### With digest expression

```
/generate-slsa
Generate SLSA for image from Build_and_Push digest output — keyless attest
```

### Placement must be explicit

```
/generate-slsa
add slsa to the pipeline
```

Agent must still run Phase 2 + Phase 3 — do not assume stage or skip placement.

---

## Performance Notes

- Only **existing pipelines** — do not create standalone SLSA pipelines (may append Deploy stage for CD).
- **Wizard UX is mandatory** — one question per turn; see `references/interactive-wizard-flow.md`.
- **Placement after build/push** — SLSA needs a published image (tag or digest).
- **Sequential with SBOM** — never parallel SBOM + SLSA attestation (Cosign registry race).
- **YAML step `type` is `provenance`** — not `SlsaGeneration` (API enum rejects `SlsaGeneration`).
- Docker UI **Image** field → YAML `source.spec.repo` (not `image`; SBOM `SscaOrchestration` uses `image` for docker).
- **Key-based attestation** — private key + password must be Harness **file secrets** (`/create-secret`).
- **CD generation is rare** — prefer CI generation + CD `/enforce-slsa`; see CD reference.
- **Auto-run** after CI-only update when inputs inferrable.
- Do **not** use for dashboard-only SSCA config — use `/manage-supply-chain` instead.

---

## Troubleshooting

### Pipeline Not Found
- Verify org/project; `harness_list` (resource_type: `pipeline`).

### Connector Not Found
- Search build/push steps for `connectorRef`; `harness_search` for Docker registry connectors.

### Image Not Found / Invalid Reference
- Use single `repo` string — e.g. `lavakush07/easy-buggy-app:blog`.
- Symptom: provenance generation fails — confirm image exists at run time.

### Attestation Failed (Key-based)
- Verify file secrets exist and Cosign key is `ecdsa-p256`.
- Password secret must match the key pair generation password.
- JFrog registries need extra connector permissions for `.att` upload.

### Attestation Failed (Keyless)
- Requires Harness CI execution context; configure Connector for Keyless Signing for non-harness OIDC.

### SBOM + SLSA Race
- Symptom: only one `.att` in registry — steps ran in parallel.
- Fix: reorder — SBOM then SLSA sequentially in the same stage.

### CD Validation Errors
- `provenance` (SLSA Generation) in Deploy stages must be inside `stepGroup` with `stepGroupInfra`.
- See `references/cd-containerized-step-group.md`.

### YAML Rejects `SlsaGeneration` Step Type
- Symptom: `does not have a value in the enumeration` for `SlsaGeneration`.
- Fix: use `type: provenance` — validate with `harness_schema(resource_type="pipeline", path="steps")`.

### Skipped Placement
- Re-run wizard from Phase 2; ask stage + position explicitly.

### Auto-run Failed
- Map branch/tag into `inputs` for codebase pipelines.
- CD: report missing service/env/infra — do not guess runtime inputs.

### MCP Errors
- `CONNECTOR_NOT_FOUND` — verify connector identifier.
- `ACCESS_DENIED` — PAT needs pipeline edit permission.
