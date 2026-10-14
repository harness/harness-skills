# CD Deployment Stage — Containerized Step Group for SLSA

Use with `/generate-slsa` when Placement targets a **`type: Deployment`** (CD) stage. **SLSA Generation**
is most common in **CI immediately after build/push**; CD typically uses **`SlsaVerification`**. Only
use CD generation when the user explicitly chooses deploy-time provenance.

Harness requires SCS steps in Deploy stages to run inside a **containerized step group** with
`stepGroupInfra`. See [Containerized step groups](https://developer.harness.io/docs/continuous-delivery/x-platform-cd-features/cd-steps/containerized-steps/containerized-step-groups/).

## Rules (mandatory for CD)

| Rule | Detail |
|------|--------|
| **Where** | `stage.spec.execution.steps[].stepGroup.steps[]` — **not** top-level `execution.steps` |
| **Container infra** | `stepGroupInfra` (`KubernetesDirect` or `VM`) |
| **When** | Before deploy; image must exist in registry |
| **Order** | After SBOM/SLSA peers in the **same** group — **sequentially**, not parallel |

## Example — containerized group with SLSA before deploy

```yaml
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
          identifier: slsageneration_cd
          name: SLSA Generation
          type: provenance
          spec:
            source:
              type: docker
              spec:
                connector: <registry_connector>
                repo: <+artifact.image>
            attestation:
              type: keyless
              spec:
                oidcProvider: harness
          timeout: 15m
- step:
    identifier: rolling_deployment
    type: K8sRollingDeploy
    spec:
      skipDryRun: false
    timeout: 10m
```

**CD image:** prefer `<+artifact.image>` from the service primary artifact.

**Step id:** use `slsageneration_cd` when CI already has `slsageneration`.

## Phase 3b prerequisites

When adding a new Deploy stage to a CI-only pipeline: service → environment → infrastructure →
step group infra → append stage. Mirror `/create-infrastructure` for missing infra.
