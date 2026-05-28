# SLSA Generation Step — UI ↔ YAML

Maps the Harness **SLSA Generation** step drawer (**Step Parameters** tab) to pipeline YAML.
The UI label is **SLSA Generation**; the pipeline step `type` is **`provenance`** (not
`SlsaGeneration` — the API rejects that enum value).

The UI is **selection-driven**: Source tile (Third-Party / Artifact Registry / Harness Local Stage),
Provider dropdown (Third-Party), Container Registry + Image, then **Attest SLSA**.

Use with `/generate-slsa` before generating YAML. Validate with
`harness_schema(resource_type="pipeline", path="steps")`.

## Step identity

| UI field | YAML |
|----------|------|
| Name | `name: slsa-generation` (or user label) |
| Id | `identifier: slsageneration` |

Step `type`: **`provenance`** (UI: SLSA Generation)

## Source (artifact / registry)

Harness `spec.source` uses **`ProvenanceSource`**. UI tiles map to lowercase `source.type`:

| UI tile | UI provider | `source.type` | Required `source.spec` fields |
|---------|-------------|---------------|----------------------------------|
| **Third-Party** | Docker Registry | `docker` | `connector`, `repo` |
| Third-Party | Amazon ECR | `ecr` | `connector`, `image`; optional `region`, `account`, `digest` |
| Third-Party | Google GCR | `gcr` | `connector`, `host`, `projectID`, `imageName`; optional `digest` |
| Third-Party | Google GAR | `gar` | `connector`, `host`, `projectID`, `imageName`; optional `digest` |
| Third-Party | Azure ACR | `acr` | `connector`, `repository`; optional `subscriptionId`, `digest` |
| **Artifact Registry** | Harness AR | `har` | `registry`, `image`; optional `digest` |
| **Harness Local Stage** | Workspace | `local` | `workspace`, `type` (`auto` \| `manual`); `artifact_name`, `version` when manual |

### Docker Registry (matches reference UI)

UI **Container Registry** → `source.spec.connector` (Docker Registry connector identifier).

UI **Image** (`lavakush07/easy-buggy-app:blog`) → `source.spec.repo` (single string with tag or digest).

```yaml
source:
  type: docker
  spec:
    connector: lavakush07
    repo: lavakush07/easy-buggy-app:blog
```

- Do **not** use leading `/`, `https://`, or split tag into a separate field for Docker Hub style refs.
- **Optional digest:** for ECR/GCR/GAR/ACR or when pinning to a build output, set `digest` to a Harness
  expression from the prior build/push step (see below). Newer SCS builds accept tag-only `repo` for
  Docker Registry — omit `digest` unless the user chose expression mode or API requires it.

### Digest expression (optional — after Build and Push)

When the user wants digest from a prior step:

```yaml
    digest: <+pipeline.stages.<stage_id>.spec.execution.steps.<build_step_id>.output.outputVariables.digest>
```

Or from Build and Push published artifacts:

```yaml
    digest: <+pipeline.stages.<stage_id>.spec.execution.steps.<build_step_id>.stepArtifacts.publishedImageArtifacts[0].digest>
```

## Attest SLSA (`spec.attestation`)

Maps to **`AttestationV1`**. Omit the entire `attestation` block when the user unchecks **Attest SLSA**.

| UI | YAML |
|----|------|
| **Attest SLSA** checked | Include `spec.attestation` |
| **Keyless** (default in UI when attesting) | `attestation.type: keyless` + `spec.oidcProvider` |
| OIDC Provider → Harness | `oidcProvider: harness` |
| OIDC Provider → Non-Harness | `oidcProvider: non-harness` — account **Connector for Keyless Signing** required |
| **Key-based** | `attestation.type: keybased` + Cosign private key + password secret refs |
| **Secret Manager** (Vault) | `attestation.type: secret-manager` + Vault connector + key path |

### Keyless (Harness OIDC) — default when attesting

```yaml
attestation:
  type: keyless
  spec:
    oidcProvider: harness
```

### Key-based — matches reference UI

UI **Private Key** → Harness **file secret** identifier (e.g. `account.cosign_private_key`).

UI **Password** → Harness **file secret** identifier for the key password (e.g. `account.cosign_password`).

```yaml
attestation:
  type: keybased
  spec:
    privateKey: account.cosign_private_key
    password: account.cosign_password
```

Use the secret identifiers exactly as shown in Pipeline Studio (account / org / project scoped).
If API validation rejects `privateKey`, try `key` with the same secret ref — mirror the upstream
`SscaOrchestration` attestation block shape from an existing pipeline step.

Generate keys with Cosign (`ecdsa-p256`) and store as Harness file secrets via `/create-secret`.

### Secret Manager (HashiCorp Vault)

```yaml
attestation:
  type: secret-manager
  spec:
    connector: <vault_connector>
    key: <transit_engine_path>/<key_name>
```

Requires Vault Transit engine and delegate `25.10.87000+` for subfolder paths (FF `SSCA_COSIGN_USING_VAULT_V2`).

## Full example — reference UI screenshot

Third-Party · Docker Registry · Attest SLSA · Key-based:

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

## Placement and ordering

| Rule | Detail |
|------|--------|
| **When** | Immediately **after** image build/push (`BuildAndPushDockerRegistry`, Kaniko `Run`, etc.) |
| **SBOM coexistence** | Run **after** `SscaOrchestration` when both exist — **sequentially**, never in parallel (Cosign registry race) |
| **CD Deploy** | Generation is usually CI-side; verification runs in CD. If user insists on CD generation, use containerized step group — see `cd-containerized-step-group.md` |

## Harness docs

- [Generate SLSA](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/slsa/generate-slsa)
- [Verify SLSA](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/slsa/verify-slsa)
- [Cosign key pair generation](https://developer.harness.io/docs/software-supply-chain-assurance/shared/generate-cosign-key-pair)
