# Artifact Verification Step — UI ↔ YAML

Maps the Harness **Artifact Verification** step drawer (**Step Parameters** tab) to
`SscaArtifactVerification` pipeline YAML.

Use with `/verify-sign` before generating YAML. Validate with
`harness_schema(resource_type="pipeline", path="steps")`.

## Prerequisites

- **Existing pipeline** with a signed artifact — typically from `SscaArtifactSigning`
  (`/sign-artifact`).
- **Key-based verify:** Harness **file secret** with the Cosign **public** key matching the private
  key used at signing (`/create-secret`).

## Step identity

| UI field | YAML |
|----------|------|
| Name | `name: Artifact Verification` (or user label) |
| Id | `identifier: artifactverification` |

Step `type`: **`SscaArtifactVerification`**

## Source (registry / artifact)

Verification reuses **`ArtifactSigningSource`** — same lowercase types and fields as signing.

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
**HAR is supported in YAML** — always offer it in the wizard.

### Docker Registry

```yaml
source:
  type: docker
  spec:
    connector: lavakush07
    image: lavakush07/easy-buggy-app:v5
```

Reuse the **same** connector and `image` as the upstream `SscaArtifactSigning` step.

### Harness Artifact Registry (HAR)

```yaml
source:
  type: har
  spec:
    registry: prod_har_registry
    image: my-service:v2
```

## Verify signature (`spec.verifySign`)

Field name is **`verifySign`** (camelCase). Maps to **`SlsaVerifyAttestation`**.

| UI | YAML (preferred) |
|----|------------------|
| **Keyless** | `verifySign.type: keyless` + `spec.oidcProvider` |
| OIDC Provider → Harness | `oidcProvider: harness` |
| **Key-based** | `verifySign.type: cosign` + `public_key` file secret |
| **Secret Manager** (Vault) | Vault connector + public key path |

### Keyless — when signing used keyless Harness OIDC

```yaml
verifySign:
  type: keyless
  spec:
    oidcProvider: harness
```

Verification method must **match** the upstream `signing` block.

### Key-based — Harness docs sample

Signing uses **private** key; verification uses **public** key file secret:

```yaml
verifySign:
  type: cosign
  spec:
    public_key: account.cosign_public_key
```

If API validation rejects `public_key`, try `publicKey` with the same secret ref.

### Fallback — nested `cosign` wrapper for keyless

If flat `keyless` fails API validation, retry:

```yaml
verifySign:
  type: cosign
  spec:
    type: keyless
    spec:
      oidcProvider: harness
```

### Secret Manager (HashiCorp Vault)

When signing used `signing.type: secret-manager`:

```yaml
verifySign:
  type: secret-manager
  spec:
    connector: <vault_connector>
    key: <transit_engine_path>/<public_key_name>
```

## Cloud registry examples

### Amazon ECR

```yaml
- step:
    identifier: artifactverification_ecr
    name: Artifact Verification ECR
    type: SscaArtifactVerification
    spec:
      source:
        type: ecr
        spec:
          connector: my_aws_connector
          region: us-east-1
          account: "123456789012"
          image: my-repo/my-service:v5
      verifySign:
        type: keyless
        spec:
          oidcProvider: harness
    timeout: 15m
```

### Harness Local Stage

```yaml
- step:
    identifier: artifactverification_local
    name: Artifact Verification Local
    type: SscaArtifactVerification
    spec:
      source:
        type: local
        spec:
          workspace: /harness/my-artifact.jar
          artifact_name: my-artifact.jar
          version: "1.0.0"
      verifySign:
        type: cosign
        spec:
          public_key: account.cosign_public_key
    timeout: 15m
```

## Full example — CI after Artifact Signing (key-based)

Place **after** `artifactsigning` in the same CI stage:

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

## Full example — HAR, keyless

```yaml
- step:
    identifier: artifactverification_har
    name: Artifact Verification HAR
    type: SscaArtifactVerification
    spec:
      source:
        type: har
        spec:
          registry: prod_har
          image: payment-service:v3
      verifySign:
        type: keyless
        spec:
          oidcProvider: harness
    timeout: 15m
```

## CD Deploy stage

Place inside a **containerized step group** (`stepGroupInfra`) **before** deploy. See
`references/cd-containerized-step-group.md`.

**CD image:** prefer `<+artifact.image>` for `image` when verifying service artifacts.

## Harness docs

- [Verify Signed Artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/sign-verify/verify-signed-artifacts)
- [Sign Artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/sign-verify/sign-artifacts)
