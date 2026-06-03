# SBOM Policy Enforcement Step — UI ↔ YAML

Maps the Harness **SBOM Policy Enforcement** step drawer (**Step Parameters** tab) to
`SscaEnforcement` (CI / Security) or `CdSscaEnforcement` (CD `Deployment`) pipeline YAML.

Use with `/enforce-sbom` — offer the same choices the UI shows before generating YAML.

Validate fields with `harness_schema(resource_type="pipeline", path="steps")`.

## Prerequisites

- An **existing pipeline** with (or about to have) an SBOM for the artifact — typically from
  `SscaOrchestration` (`/create-sbom`) or SBOM ingestion.
- At least one **SBOM OPA policy** and a **policy set** that evaluates **On Step** against the
  `sbom` entity. Create via `/create-policy` (see `skills/create-policy/references/entity-sbom.md`).
- For **key-based** verification: a Harness **file secret** with the Cosign **public** key used to
  sign/attest the SBOM.

## Step identity

| UI field | YAML |
|----------|------|
| Name | `name: SBOM Policy Enforcement` (or user label) |
| Id | `identifier: enforce_sbom` |

| Stage context | `type` value |
|---------------|--------------|
| CI, Security | `SscaEnforcement` |
| CD `Deployment` (containerized step group) | `CdSscaEnforcement` |

## Source (registry / repository)

Same `source` model as SBOM Orchestration (`SbomSource`). UI tiles map to `source.type`:

| UI tile | `source.type` | Required `source.spec` |
|---------|---------------|-------------------------|
| **Artifact Registry** | `har` | `registry`, `image` |
| **Third-Party** → Docker Registry | `docker` | `connector`, `image` |
| Third-Party → Amazon ECR | `ecr` | `image`; optional `connector`, `region`, `account` |
| Third-Party → Google GCR | `gcr` | `connector`, `host`, `project_id`, `image` |
| Third-Party → Google GAR | `gar` | `connector`, `host`, `project_id`, `image` |
| Third-Party → Azure ACR | `acr` | `connector`, `image`; optional `subscription_id` |
| **Repository** | `repository` | `url`, `variant_type`, `variant`; step `overrideConnectorRef` for Git |

**Registry** (UI) → `spec.connector` (Docker connector) or `spec.registry` (HAR).

**Image** (UI) → single `image` string (`org/repo:tag` or digest). Use the **same** image/repo as
the upstream `SscaOrchestration` step when enforcing policies on that artifact.

## Verify SBOM attestation

| UI | YAML |
|----|------|
| **Verify SBOM** checked (recommended) | Include `spec.verifyAttestation` |
| Verify with → **Keyless** | `verifyAttestation.type: cosign` + keyless spec (see below) |
| OIDC Provider → Harness | `oidcProvider: harness` |
| OIDC Provider → Non-Harness | `oidcProvider: non-harness` — account connector for keyless signing required |
| Verify with → **Key-based** | Cosign public key via Harness file secret ref in spec |
| Verify with → **Secret Manager** | HashiCorp Vault connector + key path (same as attestation) |
| Uncheck Verify SBOM | Omit `verifyAttestation` (only if SBOM is unsigned and policy allows) |

**Default — Verify SBOM + Keyless + Harness OIDC** (matches reference UI):

```yaml
verifyAttestation:
  type: cosign
  spec:
    type: keyless
    spec:
      oidcProvider: harness
```

If API validation rejects nested `type: keyless`, mirror the **exact** `attestation` block from the
upstream `SscaOrchestration` step under `verifyAttestation` (same signing method used at generation).

Key-based example:

```yaml
verifyAttestation:
  type: cosign
  spec:
    type: keybased
    spec:
      publicKey: <file_secret_identifier_for_public_key>
```

## Policy configuration

| UI | YAML |
|----|------|
| **Policy Sets** (one or more) | `spec.policy.policySets` — array of policy set **identifiers** |
| Add/Modify Policy Set | Use Harness Policy UI or `/create-policy` + `harness_list` (`policy_set`) |

```yaml
policy:
  policySets:
    - sbom_license_allowlist
    - sbom_deny_log4j
```

Policy sets must include SBOM policies (`package sbom`, entity **sbom**, event **onstep**). List
available sets:

```
harness_list(resource_type="policy_set", org_id="...", project_id="...")
```

## Full example — CI (Third-Party Docker, keyless verify, policy sets)

Place **after** `SscaOrchestration` in the same CI stage:

```yaml
- step:
    identifier: enforce_sbom
    name: SBOM Policy Enforcement
    type: SscaEnforcement
    spec:
      source:
        type: docker
        spec:
          connector: <docker_registry_connector>
          image: <org>/<repo>:<tag>
      verifyAttestation:
        type: cosign
        spec:
          type: keyless
          spec:
            oidcProvider: harness
      policy:
        policySets:
          - <sbom_policy_set_identifier>
    timeout: 15m
```

## CD Deployment (containerized step group)

Use `CdSscaEnforcement` inside a step group with **container-based execution** enabled. Place
**before** the deployment step; source/verify/policy match CI.

```yaml
- step:
    identifier: enforce_sbom
    name: SBOM Policy Enforcement
    type: CdSscaEnforcement
    spec:
      infrastructure:
        type: KubernetesDirect
        spec:
          connectorRef: <k8s_connector>
          namespace: <namespace>
      source:
        type: docker
        spec:
          connector: <docker_registry_connector>
          image: <org>/<repo>:<tag>
      verifyAttestation:
        type: cosign
        spec:
          type: keyless
          spec:
            oidcProvider: harness
      policy:
        policySets:
          - <sbom_policy_set_identifier>
    timeout: 15m
```

Adjust `infrastructure` to match the hosting containerized step group.

## Repository source

```yaml
spec:
  overrideConnectorRef: <git_connector>
  source:
    type: repository
    spec:
      url: https://github.com/org/repo
      variant_type: branch
      variant: main
  verifyAttestation:
    type: cosign
    spec:
      type: keyless
      spec:
        oidcProvider: harness
  policy:
    policySets:
      - <sbom_policy_set_identifier>
```

## Placement

| Stage type | When to place |
|------------|----------------|
| **CI** | Immediately **after** `SscaOrchestration` (same image/repo) |
| **CD** (`Deployment`) | **Before** deploy; inside **containerized** `stepGroup` (`stepGroupInfra`) |
| **Security** | After SBOM generation or artifact scan when SBOM exists |

- **Do not** run enforcement before an SBOM exists for the artifact.
- Use the **same** `source` image/repo as the orchestration step unless the user specifies otherwise.
- **CI-only pipeline + CD enforcement:** allowed — append a new `Deployment` stage with containerized group + `CdSscaEnforcement` before deploy. Follow `skills/create-sbom/references/cd-containerized-step-group.md` (substitute `CdSscaEnforcement` for `SscaOrchestration`).
- **Do not** place `CdSscaEnforcement` at top-level `execution.steps` on a Deployment stage.

### New Deploy stage — enforcement in containerized group (abbreviated)

```yaml
- stage:
    identifier: Deploy_Dev
    name: Deploy Dev
    type: Deployment
    spec:
      deploymentType: Kubernetes
      service:
        serviceRef: <service_id>
      environment:
        environmentRef: <environment_id>
        deployToAll: false
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
                  connectorRef: <k8s_cluster_connector>
                  namespace: <namespace>
              steps:
                - step:
                    identifier: enforce_sbom_cd
                    name: SBOM Policy Enforcement
                    type: CdSscaEnforcement
                    spec:
                      infrastructure:
                        type: KubernetesDirect
                        spec:
                          connectorRef: <k8s_cluster_connector>
                          namespace: <namespace>
                      source:
                        type: docker
                        spec:
                          connector: <connector>
                          image: <+artifact.image>
                      verifyAttestation:
                        # match CI SscaOrchestration attestation
                      policy:
                        policySets:
                          - <policy_set_id>
                    timeout: 15m
          - step:
              identifier: rolling_deployment
              type: K8sRollingDeploy
              spec:
                skipDryRun: false
              timeout: 10m
```

## Harness docs

- [Enforce SBOM policies](https://developer.harness.io/docs/software-supply-chain-assurance/open-source-management/enforce-sbom-policies)
- [Define SBOM policies](https://developer.harness.io/docs/software-supply-chain-assurance/open-source-management/define-sbom-policies)
- [Generate SBOM for artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/open-source-management/generate-sbom-for-artifacts)
