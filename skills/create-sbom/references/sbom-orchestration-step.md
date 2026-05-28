# SBOM Orchestration Step — UI ↔ YAML

Maps the Harness **SBOM Orchestration** step drawer (**Step Parameters** tab) to `SscaOrchestration`
pipeline YAML. The product UI is **selection-driven**: Mode, Tool dropdown, Format dropdown, four
Source tiles, Provider dropdown (for Third-Party), Container Registry + Image, then Attest SBOM.

Use with `/create-sbom` **Step 4** — always offer the same choices the UI shows before generating YAML.

Validate fields with `harness_schema(resource_type="pipeline", path="steps")`.

## Step identity (always)

| UI field | YAML |
|----------|------|
| Name | `name: Generate SBOM` (or user label) |
| Id | `identifier: generate_sbom` |

## SBOM method

| UI field | YAML | Default |
|----------|------|---------|
| Mode → **Generation** | `spec.mode: generation` | **generation** |
| Mode → Ingestion | `spec.mode: ingestion` + `spec.ingestion` | Only when user has an existing SBOM file |
| SBOM Tool → **Syft** | `spec.tool.type: Syft` | **Syft** |
| SBOM Tool → cdxgen | `spec.tool.type: cdxgen` | |
| SBOM Format → **SPDX** | `spec.tool.spec.format: spdx-json` | **spdx-json** |
| SBOM Format → CycloneDX | `spec.tool.spec.format: cyclonedx-json` | |

## Source (registry type + provider)

Harness schema supports these `source.type` values: `docker`, `image`, `ecr`, `gcr`, `gar`, `acr`, `har`, `repository`, `local`.

| UI — Registry / source tile | UI — Provider | `source.type` | Required `source.spec` fields |
|-----------------------------|---------------|---------------|-------------------------------|
| **Third-Party** | Docker Registry | `docker` | `connector`, `image` |
| Third-Party | (generic image ref) | `image` | Same as `docker` — `connector`, `image` |
| Third-Party | Amazon ECR | `ecr` | `image`; optional `connector`, `region`, `account` |
| Third-Party | Google GCR | `gcr` | `connector`, `host`, `project_id`, `image` |
| Third-Party | Google GAR | `gar` | `connector`, `host`, `project_id`, `image` |
| Third-Party | Azure ACR | `acr` | `connector`, `image`; optional `subscription_id` |
| **Artifact Registry** | Harness AR | `har` | `registry`, `image` |
| **Repository** | Git | `repository` | `url`, `variant_type`, `variant`; plus `spec.overrideConnectorRef` on step |
| **Harness Local Stage** | Workspace | `local` | `artifact_name`; optional `workspace`, `version` |

`variant_type` for repository: `branch` | `git_tag` | `commit`.

**Third-Party + Docker Registry (most common):**

```yaml
source:
  type: docker
  spec:
    connector: <docker_registry_connector_identifier>
    image: <repo>/<name>:<tag>    # or repo/name@sha256:<digest>
```

- **Container Registry** in UI → `spec.connector` (Docker Registry connector identifier).
- **Image** in UI → single `image` string (`myorg/myapp:v7`), not split `url` + `variant`.
- Do **not** use leading `/`, `https://`, or `docker.io/` prefix in `image` for Docker Hub style refs unless the registry requires FQDN.

## SBOM attestation

| UI | YAML |
|----|------|
| **Attest SBOM** checked (default for this skill) | Include `spec.attestation` |
| Attest with → **Keyless** (default) | `attestation.type: keyless` + `spec.oidcProvider` |
| OIDC Provider → Harness | `oidcProvider: harness` |
| OIDC Provider → Non-Harness | `oidcProvider: non-harness` — account **Connector for Keyless Signing** must exist (SCS → Manage → Configuration) |
| Attest with → Cosign (key pair) | `attestation.type: cosign` or `keybased` + private key / password secret refs |
| Attest with → Secret Manager (Vault) | `attestation.type: secret-manager` + Vault connector + key path |

**Default attestation block (match UI: Attest SBOM + Keyless + Harness OIDC):**

```yaml
attestation:
  type: keyless
  spec:
    oidcProvider: harness
```

Omit `attestation` only if the user unchecks **Attest SBOM** in Step 4.

Keyless limitations: not supported on SMP; Rekor may be off when SCS Airgap is enabled. See `skills/sign-artifact/references/keyless-signing.md` for non-harness OIDC setup.

## Full example — matches reference UI

Third-Party · Docker Registry · Syft · SPDX · Generation · Attest SBOM (keyless):

```yaml
- step:
    identifier: generate_sbom
    name: Generate SBOM
    type: SscaOrchestration
    spec:
      mode: generation
      source:
        type: docker
        spec:
          connector: <docker_registry_connector>
          image: <org>/<repo>:<tag>
      tool:
        type: Syft
        spec:
          format: spdx-json
      attestation:
        type: keyless
        spec:
          oidcProvider: harness
    timeout: 15m
```

## Repository source (UI tile: Repository)

```yaml
spec:
  mode: generation
  overrideConnectorRef: <git_connector>
  source:
    type: repository
    spec:
      url: https://github.com/org/repo
      variant_type: branch
      variant: main
  tool:
    type: Syft
    spec:
      format: spdx-json
  attestation:
    type: keyless
    spec:
      oidcProvider: harness
```

Stage must have `cloneCodebase: true` and `properties.ci.codebase` so Syft scans cloned source under `/harness`.

## ECR (Third-Party → Amazon ECR)

```yaml
source:
  type: ecr
  spec:
    connector: <docker_or_aws_registry_connector>
    image: <repo/name:tag_or_digest>
    region: <aws_region>          # e.g. us-east-1
    account: <aws_account_id>     # 12-digit account
```

## GCR (Third-Party → Google Container Registry)

```yaml
source:
  type: gcr
  spec:
    connector: <docker_registry_connector>
    host: gcr.io                  # or regional host if applicable
    project_id: <gcp_project_id>
    image: <repo/name:tag_or_digest>
```

## GAR (Third-Party → Google Artifact Registry)

```yaml
source:
  type: gar
  spec:
    connector: <docker_registry_connector>
    host: <region>-docker.pkg.dev  # e.g. us-east1-docker.pkg.dev
    project_id: <gcp_project_id>
    image: <repo/name:tag_or_digest>
```

## ACR (Third-Party → Azure Container Registry)

```yaml
source:
  type: acr
  spec:
    connector: <docker_registry_connector>
    image: <registry>.azurecr.io/<repo>:<tag>
    subscription_id: <azure_subscription_id>   # optional per connector setup
```

## Harness Artifact Registry (Artifact Registry tile)

```yaml
source:
  type: har
  spec:
    registry: <harness_artifact_registry_identifier>
    image: <image_name:tag_or_digest>
```

## Harness Local Stage (workspace artifact)

Use when the artifact is already produced in the pipeline workspace (not a remote registry pull).

```yaml
source:
  type: local
  spec:
    artifact_name: <name>           # required
    workspace: <path>               # optional; default workspace under /harness
    version: <version_label>        # optional
```

For non-container artifacts (JAR, Helm, etc.), SBOM is often **ingestion** mode with a pre-generated file — see Harness docs on ingest SBOM.

## Placement

SBOM Orchestration (`SscaOrchestration`) is supported in **CI**, **CD** (`Deployment`), and
**Security** (`Security`) stages.

| Stage type | When to place | Notes |
|------------|---------------|--------|
| **CI** (`type: CI`) | After image push or at end of stage | Repository source needs `cloneCodebase: true` + `properties.ci.codebase` |
| **CD** (`type: Deployment`) | Inside `stepGroup.steps` with `stepGroupInfra` — **before** deploy | Not at top-level `execution.steps`; see `cd-containerized-step-group.md` |
| **Security** (`type: Security`) | End of `spec.execution.steps` (or after a named step) | Often used with registry image or post-build artifact |

**CD containerized step group (required):**

```yaml
- stepGroup:
    identifier: scs_sbom
    name: Supply Chain Security
    stepGroupInfra:
      type: KubernetesDirect
      spec:
        connectorRef: <k8s_cluster_connector>
        namespace: <namespace>
    steps:
      - step:
          identifier: generate_sbom
          name: Generate SBOM
          type: SscaOrchestration
          spec:
            mode: generation
            source:
              type: docker
              spec:
                connector: <docker_registry_connector>
                image: <+artifact.image>    # or literal; prefer CD expressions
            tool:
              type: Syft
              spec:
                format: spdx-json
          timeout: 15m
```

- `stepGroupInfra.type`: `KubernetesDirect` (typical) or `VM` (feature-flagged).
- Place the step group **before** `K8sRollingDeploy`, `HelmDeploy`, etc.
- Run SBOM and SLSA attestation **sequentially**, not in parallel (Cosign registry race).
- After pipeline update, the skill **auto-runs** the pipeline with wizard-derived runtime inputs (no manual run prompt).

Full CD edge cases: `references/cd-containerized-step-group.md`.

## Harness docs

- [Generate SBOM for Artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/open-source-management/generate-sbom-for-artifacts)
- [Cosign attestation options](https://developer.harness.io/docs/software-supply-chain-assurance/shared/cosign-attestation-options)
