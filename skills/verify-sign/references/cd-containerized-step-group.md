# CD Deployment Stage — Containerized Step Group for Artifact Verification

Use with `/verify-sign` when Placement targets a **`type: Deployment`** (CD) stage. Unlike artifact
**signing** (not supported in Deploy today), **verification is supported** in Deploy stages inside a
containerized step group.

Harness requires SCS steps in Deploy stages to run inside a **containerized step group** with
`stepGroupInfra`. See [Containerized step groups](https://developer.harness.io/docs/continuous-delivery/x-platform-cd-features/cd-steps/containerized-steps/containerized-step-groups/).

## Rules (mandatory for CD)

| Rule | Detail |
|------|--------|
| **Where** | `stage.spec.execution.steps[].stepGroup.steps[]` — **not** top-level `execution.steps` |
| **Container infra** | `stepGroupInfra` (`KubernetesDirect` or `VM`) |
| **When** | Before deploy; artifact must be signed |
| **Order** | After other SCS steps in the **same** group — sequentially |

## Example — verify before deploy

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
    type: K8sRollingDeploy
    spec:
      skipDryRun: false
    timeout: 10m
```

**CD image:** prefer `<+artifact.image>` from the service primary artifact.

**Step id:** use `artifactverification_cd` when CI already has `artifactverification`.

## Phase 3b prerequisites

When adding a new Deploy stage to a CI-only pipeline: service → environment → infrastructure →
step group infra → append stage. Mirror `/create-infrastructure` for missing infra.

## Contrast with signing

| Step | CI | CD Deploy |
|------|-----|-----------|
| `SscaArtifactSigning` | Supported | **Not supported** (roadmap) |
| `SscaArtifactVerification` | Supported | Supported (containerized group) |

Sign in CI with `/sign-artifact`; verify in CD with `/verify-sign` before deploy.
