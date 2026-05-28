# Artifact Signing Step — UI ↔ YAML

Maps the Harness **Artifact Signing** step drawer (**Step Parameters** tab) to `SscaArtifactSigning`
pipeline YAML. The UI is **selection-driven**: Source tile, registry fields, **Sign with**, and
**Attach signature to Artifact Registry**.

Use with `/sign-artifact` before generating YAML. Validate with
`harness_schema(resource_type="pipeline", path="steps")`.

## Step identity

| UI field | YAML |
|----------|------|
| Name | `name: Artifact Signing` (or user label) |
| Id | `identifier: artifactsigning` |

Step `type`: **`SscaArtifactSigning`**

## Source (artifact / registry)

Harness `spec.source` uses **`ArtifactSigningSource`**. UI tiles map to lowercase `source.type`:

| UI tile | UI provider | `source.type` | Required `source.spec` fields |
|---------|-------------|---------------|----------------------------------|
| **Third-Party** | Docker Registry | `docker` | `connector`, `image` |
| Third-Party | Amazon ECR | `ecr` | `image`; optional `connector`, `region`, `account`, `digest` |
| Third-Party | Google GCR | `gcr` | `connector`, `host`, `projectID`, `imageName`; optional `digest` |
| Third-Party | Google GAR | `gar` | `connector`, `host`, `projectID`, `imageName`; optional `digest` |
| Third-Party | Azure ACR | `acr` | `connector`, `repository`; optional `subscriptionId`, `digest` |
| **Artifact Registry** | Harness AR (HAR) | `har` | `registry`, `image` |
| **Harness Local Stage** | Workspace | `local` | `workspace`; `artifact_name`, `version` when manual |

**UI note:** Some Pipeline Studio builds show only **Third-Party** and **Harness Local Stage** tiles.
**HAR is supported in YAML** — always offer it in the wizard when the user stores images in Harness
Artifact Registry.

### Docker Registry (matches reference UI)

UI **Container Registry** → `source.spec.connector`.

UI **Image** → `source.spec.image` (single string with tag or digest).

```yaml
source:
  type: docker
  spec:
    connector: lavakush07
    image: lavakush07/easy-buggy-app:v5
```

- Do **not** use `repo` for Artifact Signing docker source (that field is for SLSA `provenance`).
- **Optional digest:** set `digest` on ECR/GCR/GAR/ACR or pin via expression from build/push output.

### Harness Artifact Registry (HAR)

UI **Registry** → `source.spec.registry` (HAR registry identifier).

UI **Image** → `source.spec.image` (e.g. `my-service:v2` or digest).

```yaml
source:
  type: har
  spec:
    registry: prod_har_registry
    image: my-service:v2
```

### Harness Local Stage (non-container)

For `.jar`, `.war`, `.tgz` (Helm), `.yaml`, and other workspace artifacts.

```yaml
source:
  type: local
  spec:
    workspace: /harness/my-artifact.jar
    artifact_name: my-artifact.jar
    version: "1.0.0"
```

Omit `version` when using auto target detection from path.

## Sign with (`spec.signing`)

Maps to **`AttestationV1`**. Field name is **`signing`** — not `attestation`.

| UI | YAML |
|----|------|
| **Keyless** | `signing.type: keyless` + `spec.oidcProvider` |
| OIDC Provider → Harness | `oidcProvider: harness` |
| OIDC Provider → Non-Harness | `oidcProvider: non-harness` |
| **Key-based** | `signing.type: keybased` or `cosign` + private key + password secrets |
| **Secret Manager** (Vault) | `signing.type: secret-manager` + Vault connector + key path |

### Keyless (Harness OIDC)

```yaml
signing:
  type: keyless
  spec:
    oidcProvider: harness
```

### Key-based — matches Harness docs sample

UI **Private Key** / **Password** → Harness **file secret** identifiers.

```yaml
signing:
  type: cosign
  spec:
    private_key: account.cosign_private_key
    password: account.cosign_password
```

If API validation rejects `private_key`, try `privateKey` / `key` with the same secret refs — mirror
an existing `SscaOrchestration` or `provenance` attestation block in the pipeline.

Generate keys with Cosign (`ecdsa-p256`) and store as Harness file secrets via `/create-secret`.

### Secret Manager (HashiCorp Vault)

```yaml
signing:
  type: secret-manager
  spec:
    connector: <vault_connector>
    key: <transit_engine_path>/<key_name>
```

### Keyless — Non-Harness OIDC

Requires SSCA account **Connector for Keyless Signing** (AWS/Azure/GCP OIDC connector).

```yaml
signing:
  type: keyless
  spec:
    oidcProvider: non-harness
```

## Attach signature to Artifact Registry (`spec.uploadSignature`)

UI checkbox **Attach signature to Artifact Registry** → `uploadSignature.upload`.

| UI | YAML |
|----|------|
| Checked | `uploadSignature: { upload: true }` |
| Unchecked (Harness default) | omit block or `upload: false` — **no `.sig` in registry** |

Container images only — not applicable to Harness Local Stage artifacts.

**Critical:** Per Harness docs, the checkbox defaults to **unchecked**. If the user does not see a
`.sig` in the registry after a successful signing step, the most likely cause is missing
`uploadSignature.upload: true`. Update the step YAML and re-run the pipeline.

```yaml
uploadSignature:
  upload: true
```

### Where to find signatures after upload

Cosign does not always push a file literally named `image.sig`. Depending on registry:

| Registry | Typical signature storage |
|----------|---------------------------|
| Docker Hub / OCI | Separate tag `sha256-<digest>.sig` or OCI artifact attachment |
| ECR / GCR / GAR / ACR | OCI signature manifest linked to image digest |
| HAR | Signature stored alongside image in Harness Artifact Registry |

Verify via Harness **Supply Chain** tab, **Artifacts Overview**, or `cosign verify <image>`.

## Full example — Docker Registry, key-based, upload .sig

Third-Party · Docker Registry · Key-based · Attach signature:

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

## Full example — HAR, keyless, upload .sig

```yaml
- step:
    identifier: artifactsigning_har
    name: Artifact Signing HAR
    type: SscaArtifactSigning
    spec:
      source:
        type: har
        spec:
          registry: prod_har
          image: payment-service:v3
      signing:
        type: keyless
        spec:
          oidcProvider: harness
      uploadSignature:
        upload: true
    timeout: 15m
```

## Cloud registry examples (with `.sig` upload)

### Amazon ECR

```yaml
- step:
    identifier: artifactsigning_ecr
    name: Artifact Signing ECR
    type: SscaArtifactSigning
    spec:
      source:
        type: ecr
        spec:
          connector: my_aws_connector
          region: us-east-1
          account: "123456789012"
          image: my-repo/my-service:v5
      signing:
        type: keyless
        spec:
          oidcProvider: harness
      uploadSignature:
        upload: true
    timeout: 15m
```

### Google GCR / GAR

```yaml
      source:
        type: gar
        spec:
          connector: my_gcp_connector
          host: us-docker.pkg.dev
          projectID: my-gcp-project
          imageName: my-repo/my-service:v5
      uploadSignature:
        upload: true
```

### Azure ACR

```yaml
      source:
        type: acr
        spec:
          connector: my_azure_connector
          repository: myregistry.azurecr.io/my-service:v5
      uploadSignature:
        upload: true
```

## Placement and ordering

| Rule | Detail |
|------|--------|
| **When** | Immediately **after** image build/push (`BuildAndPushDockerRegistry`, Kaniko `Run`, etc.) |
| **SBOM / SLSA coexistence** | Run **after** `SscaOrchestration` and/or `provenance` when both exist — **sequentially** |
| **CD Deploy** | Not supported today — use CI or Security stage |
| **Upload** | Always include `uploadSignature.upload: true` when user expects registry-side `.sig` |

## Harness docs

- [Sign Artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/sign-verify/sign-artifacts)
- [Verify Signed Artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/sign-verify/verify-signed-artifacts)
- [Cosign key pair generation](https://developer.harness.io/docs/software-supply-chain-assurance/shared/generate-cosign-key-pair)
