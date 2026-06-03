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

**CD image:** **default to** `<+artifact.image>` from the service primary artifact — do not copy the
static signing tag unless user explicitly chooses it. Warn when static tag ≠ service artifact tag.

**Step id:** use `artifactverification_cd` when CI already has `artifactverification`.

## Full Deploy stage example (copy when appending)

Includes required `failureStrategies`, `rollbackSteps`, and `spec: {}` on rollback — omitting these
causes `harness_update` validation errors.

```yaml
    - stage:
        name: Deploy
        identifier: Deploy
        type: Deployment
        spec:
          deploymentType: Kubernetes
          service:
            serviceRef: buggyapp
          environment:
            environmentRef: prod
            infrastructureDefinitions:
              - identifier: prodinfra
          execution:
            steps:
              - stepGroup:
                  identifier: scs_before_deploy
                  name: Supply Chain Security
                  stepGroupInfra:
                    type: KubernetesDirect
                    spec:
                      connectorRef: account.sscsplayacc
                      namespace: default
                  steps:
                    - step:
                        identifier: artifactverification_cd
                        name: Artifact Verification
                        type: SscaArtifactVerification
                        spec:
                          source:
                            type: docker
                            spec:
                              connector: lavakush07
                              image: <+artifact.image>
                          verifySign:
                            type: keyless
                            spec:
                              oidcProvider: harness
                        timeout: 15m
              - step:
                  identifier: rolling_deployment
                  name: Rolling Deployment
                  type: K8sRollingDeploy
                  spec:
                    skipDryRun: false
                  timeout: 10m
            rollbackSteps:
              - step:
                  identifier: rollback
                  name: Rollback
                  type: K8sRollingRollback
                  spec: {}
                  timeout: 10m
        failureStrategies:
          - onFailure:
              errors: [AllErrors]
              action:
                type: StageRollback
```

## Delegate preflight (before CD update)

Containerized step groups run on a delegate via the K8s connector in `stepGroupInfra`. Before
`harness_update`:

1. `harness_get(resource_type="connector", resource_id=<k8s_connector>)` — check `delegateSelectors`.
2. `harness_list(resource_type="delegate")` — confirm at least one **active** delegate matches.
3. If no match, warn the user and offer infra/connectors with active delegates (e.g. `slsaconnector`).

## Phase 3b prerequisites

When adding a new Deploy stage to a CI-only pipeline: service → environment → infrastructure →
step group infra → append stage. Mirror `/create-infrastructure` for missing infra.

## Contrast with signing

| Step | CI | CD Deploy |
|------|-----|-----------|
| `SscaArtifactSigning` | Supported | **Not supported** (roadmap) |
| `SscaArtifactVerification` | Supported | Supported (containerized group) |

Sign in CI with `/sign-artifact`; verify in CD with `/verify-sign` before deploy.
