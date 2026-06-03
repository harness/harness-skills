# SLSA Verification Step — UI ↔ YAML

Maps the Harness **SLSA Verification** step drawer (**Step Parameters** + **Advanced** tabs) to
`SlsaVerification` pipeline YAML.

Use with `/enforce-slsa` before generating YAML. Validate with
`harness_schema(resource_type="pipeline", path="steps")`.

## Prerequisites

- **Existing pipeline** with SLSA provenance for the artifact — typically from a `provenance` step
  (`/generate-slsa`, UI label SLSA Generation) with attestation enabled.
- Optional **SLSA OPA policy sets** for provenance policy enforcement (Advanced → Policy Enforcement).
  List via `harness_list(resource_type="policy_set")`; create via `/create-policy`.
- **Key-based verify:** Harness **file secret** with the Cosign **public** key matching the private
  key used at generation (`/create-secret`).

## Step identity

| UI field | YAML |
|----------|------|
| Name | `name: SLSA Verification` (or user label) |
| Id | `identifier: slsaverification` |

Step `type`: **`SlsaVerification`** (same type in CI and CD — no separate CD step type).

## Source (registry / artifact)

**Important:** Verification `source.type` values are **PascalCase** (`Docker`, `Ecr`, …) — unlike
the generation `provenance` step which uses lowercase (`docker`, `ecr`, …).

| UI registry | `source.type` | Required `source.spec` fields |
|-------------|---------------|--------------------------------|
| Docker Registry | `Docker` | `image_path`; optional `connector`, `tag` |
| Amazon ECR | `Ecr` | `image`; optional `connector`, `region`, `account` |
| Google GCR | `Gcr` | `connector`, `host`, `project_id`, `image_name`; optional `tag` |
| Google GAR | `Gar` | `connector`, `host`, `project_id`, `image_name`; optional `tag` |
| Azure ACR | `Acr` | `connector`, `repository`; optional `subscription_id` |
| Harness AR | `Har` | `registry`, `image` |
| Harness Local Stage | `Local` | `workspace` (same path as generation step) |

### Docker Registry

UI **Container Registry** → `source.spec.connector`.

UI **Image** → `source.spec.image_path` (single string with tag or digest).

```yaml
source:
  type: Docker
  spec:
    connector: lavakush07
    image_path: lavakush07/easy-buggy-app:blog
```

Reuse the **same** connector and image as the upstream `provenance` (SLSA Generation) step. Map
generation `source.spec.repo` → verification `source.spec.image_path`.

## Verify SLSA attestation (`spec.verify_attestation`)

Field name is **`verify_attestation`** (snake_case). Prefer the **flat** shape (matches generation
`attestation` and `SscaEnforcement` verify blocks). If API validation rejects flat shape, retry with
nested `cosign` wrapper (fallback below).

| UI | YAML (preferred) |
|----|------------------|
| **Verify SLSA** checked (recommended) | Include `spec.verify_attestation` |
| Verify with → **Keyless** | `type: keyless` + `spec.oidcProvider` |
| OIDC Provider → Harness | `oidcProvider: harness` |
| OIDC Provider → Non-Harness | `oidcProvider: non-harness` |
| Verify with → **Key-based** | `type: keybased` + **public** key file secret |
| Verify with → **Secret Manager** (Vault) | Vault connector + public key path |
| Uncheck Verify SLSA | Omit `verify_attestation` (policy-only mode) |

### Keyless — default when generation used keyless Harness OIDC

```yaml
verify_attestation:
  type: keyless
  spec:
    oidcProvider: harness
```

Verification method must **match** the upstream generation `attestation` block.

### Key-based — when generation used keybased attestation

Generation signs with **private** key; verification uses **public** key file secret:

```yaml
verify_attestation:
  type: keybased
  spec:
    publicKey: account.cosign_public_key
```

### Fallback — nested `cosign` wrapper

If flat `keyless` / `keybased` fails API validation, retry:

```yaml
verify_attestation:
  type: cosign
  spec:
    type: keyless
    spec:
      oidcProvider: harness
```

## Policy enforcement (Advanced tab)

Policy sets attach at the **step node** level via `enforce` — not inside `spec` like
`SscaEnforcement`.

| UI | YAML |
|----|------|
| Policy Enforcement → Policy Set(s) | `enforce.policySets` — array of policy set **identifiers** |

```yaml
- step:
    identifier: slsaverification
    name: SLSA Verification
    type: SlsaVerification
    spec:
      source:
        type: Docker
        spec:
          connector: lavakush07
          image_path: lavakush07/easy-buggy-app:blog
      verify_attestation:
        type: keyless
        spec:
          oidcProvider: harness
    enforce:
      policySets:
        - slsa_provenance_rules
    timeout: 15m
```

List policy sets: `harness_list(resource_type="policy_set", org_id, project_id)`.

Omit `enforce` when the user skips policy enforcement (verify attestation only).

## Full example — CI after SLSA Generation (keyless verify + policy)

Place **after** `slsageneration` in the same CI stage:

```yaml
- step:
    identifier: slsaverification
    name: SLSA Verification
    type: SlsaVerification
    spec:
      source:
        type: Docker
        spec:
          connector: lavakush07
          image_path: lavakush07/easy-buggy-app:blog
      verify_attestation:
        type: keyless
        spec:
          oidcProvider: harness
    enforce:
      policySets:
        - slsa_prod_rules
    timeout: 15m
```

## CD Deploy stage

Place inside a **containerized step group** (`stepGroupInfra`) **before** deploy. See
`skills/generate-slsa/references/cd-containerized-step-group.md` (substitute `SlsaVerification`).

**CD image:** prefer `<+artifact.image>` for `image_path` when verifying service artifacts.

## Harness docs

- [Verify SLSA](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/slsa/verify-slsa)
- [Generate SLSA](https://developer.harness.io/docs/software-supply-chain-assurance/artifact-security/slsa/generate-slsa)
