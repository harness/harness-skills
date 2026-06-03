# CD Deployment Stage — Containerized Step Group for SBOM

Use with `/create-sbom` when Placement (Phase 3) targets a **`type: Deployment`** (CD) stage, or the
user chose **add a new CD Deploy stage** (Phase 3b).

**Phase 3 Placement is mandatory** even when the pipeline is CI-only or already has SBOM in CI —
see `interactive-wizard-flow.md`.

Harness requires **SBOM Orchestration** (`SscaOrchestration`) in Deploy stages to run inside a
**containerized step group** with **container-based execution** enabled (`stepGroupInfra`).
See [Generate SBOM for Artifacts](https://developer.harness.io/docs/software-supply-chain-assurance/open-source-management/generate-sbom-for-artifacts)
and [Containerized step groups](https://developer.harness.io/docs/continuous-delivery/x-platform-cd-features/cd-steps/containerized-steps/containerized-step-groups/).

## Rules (mandatory for CD)

| Rule | Detail |
|------|--------|
| **Where** | `stage.spec.execution.steps[].stepGroup.steps[]` — **not** top-level `execution.steps` |
| **Container infra** | Step group must have `stepGroupInfra` (`KubernetesDirect` or `VM`) |
| **When** | **Before** the deploy step (K8s rolling, Helm, ECS, etc.) — image must exist in registry |
| **Order** | After SBOM (and SLSA if present) in the **same** group — run **sequentially**, not parallel |
| **Nested groups** | Containerized step groups **cannot** contain nested `stepGroup` — only `step` / `parallel` |

## Phase 2 — Detect containerized step groups

When listing a **Deployment** stage, annotate each step group:

```
Stage 2: Deploy_Prod (type: Deployment)
  stepGroup: scs_steps (containerized: KubernetesDirect, connector: k8s_prod, ns: harness-delegate-ng)
    1: generate_sbom (SscaOrchestration)
  step: K8sRollingDeploy (K8sRollingDeploy) — deploy
```

**Containerized** = `stepGroup.stepGroupInfra` exists and `type` is `KubernetesDirect` or `VM`.

**Not containerized** = step group has no `stepGroupInfra`, or only delegate-based steps.

Also note:

- Service / environment refs (`service.serviceRef`, `environment.environmentRef`)
- Primary artifact connector from `service` or prior `execution` steps
- Existing `SscaOrchestration` inside any CD step group (reuse group + connector patterns)

## Phase 3 — CD placement options

Only offer these when the chosen stage `type` is `Deployment`:

| Option id | Behavior |
|-----------|----------|
| `cd_containerized_end` | Append SBOM to end of an **existing** containerized step group |
| `cd_containerized_after_step` | Insert after a named step **inside** that group |
| `cd_new_containerized_group` | Create a new containerized step group **before** the first deploy step |

If multiple containerized groups exist, **AskQuestion** which group id to use.

If **no** containerized group exists → use `cd_new_containerized_group` or stop (see below).

## Phase 8 — CD image field

For CD, prefer **runtime expressions** over hard-coded tags when the deploy stage consumes a
service artifact:

| Pattern | When to use |
|---------|-------------|
| `<+artifact.image>` | Primary service artifact image (verify in Pipeline Studio expression selector) |
| `<+artifact.tag>` | With image name if split in your service definition |
| `org/repo:<+artifact.tag>` | Docker Hub style when name is fixed |
| Literal `org/repo:tag` | Fixed tag pipelines only — same cautions as CI |

Copy expressions from an existing **SscaOrchestration** or **BuildAndPush** step in the same
pipeline when present. **Never guess** tags.

Registry **connector** for SBOM: use connector from service artifact source, existing SCS step,
or `harness_search` — same as CI.

## Insert paths

### A — Append to existing containerized step group (most common)

YAML path:

`stages[].stage.spec.execution.steps[j].stepGroup.steps` (append)

### B — New containerized step group before deploy

Insert a new wrapper **before** the first deploy `step` at `execution.steps`:

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
                image: <+artifact.image>
            tool:
              type: Syft
              spec:
                format: spdx-json
          timeout: 15m
- step:
    identifier: rolling_deployment
    name: Rolling Deployment
    type: K8sRollingDeploy
    # ... existing deploy step unchanged ...
```

**Infra resolution** for `stepGroupInfra.spec` (in order):

1. Copy from another **containerized** `stepGroup` in the same pipeline
2. Copy `connectorRef` / `namespace` from stage `infrastructure` if `KubernetesDirect`
3. Ask user for Kubernetes cluster connector + namespace (one turn) — do not invent

### C — Full Deployment stage example (abbreviated)

```yaml
- stage:
    name: Deploy Production
    identifier: Deploy_Production
    type: Deployment
    spec:
      deploymentType: Kubernetes
      service:
        serviceRef: my_service
      environment:
        environmentRef: prod
        infrastructureDefinitions:
          - identifier: prod_k8s_infra
      execution:
        steps:
          - stepGroup:
              identifier: scs_before_deploy
              name: SCS
              stepGroupInfra:
                type: KubernetesDirect
                spec:
                  connectorRef: account.k8s_connector
                  namespace: harness-delegate-ng
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
                          connector: dockerhub_connector
                          image: <+artifact.image>
                      tool:
                        type: Syft
                        spec:
                          format: spdx-json
                    timeout: 15m
          - step:
              identifier: rolling_deployment
              name: Rolling Deployment
              type: K8sRollingDeploy
              spec:
                skipDryRun: false
              timeout: 10m
```

## When no containerized step group exists

1. **Recommend** `cd_new_containerized_group` with infra from stage/pipeline (above).
2. If the user has no K8s connector for `stepGroupInfra`, stop and explain:
   - Enable **container based execution** on a step group in Pipeline Studio, or
   - Add a **KubernetesDirect** `stepGroupInfra` (cluster connector + namespace).
3. **Do not** place `SscaOrchestration` at the top level of `execution.steps` on a Deployment
   stage — it will fail validation or runtime.

## When the pipeline has no Deployment stage (Phase 3b)

Typical flow when Phase 2 shows **only CI** (e.g. a single `Build` stage):

1. **Warn** — SBOM in CD requires a `Deployment` stage; CI Cloud runtime is not sufficient.
2. **AskQuestion** — add Deploy stage, different pipeline, or CI-only SBOM (wizard Phase 3).
3. If adding Deploy stage, collect in separate turns:
   - `service.serviceRef` — artifact registry on the service drives SBOM `connector` + `<+artifact.image>`
   - `environment.environmentRef`
   - `environment.infrastructureDefinitions[].identifier` — **required**; list with
     `harness_list(resource_type="infrastructure", params={ environment_id: "<env>" })`; create with
     `harness_create` if missing (`KubernetesDirect`, same connector/namespace pattern as `/create-infrastructure`)
   - `stepGroupInfra` — K8s cluster connector + namespace for the SSCA pod (may match or differ from deploy infra)
4. Append the Deploy stage **after** existing CI stages unless the user wants a different order.
5. **Duplicate SBOM** — if CI already has `generate_sbom`, use `generate_sbom_cd` in CD; offer
   “keep both” vs “CD only” in Placement / Phase 10 confirm.

**Validation error:** `infrastructureDefinitions or infrastructureDefinition should be present` —
add an infra identifier; `deployToAll: true` alone is not enough unless the API accepts it for
that environment.

## Duplicate step identifiers (CI + CD)

| Location | Suggested identifier |
|----------|----------------------|
| CI stage | `generate_sbom` |
| CD step group | `generate_sbom_cd` |

`DUPLICATE_IDENTIFIER` on update — rename the CD step.

## Running CD pipelines

CD runs often need **service**, **environment**, and **infra** runtime inputs. This skill only
**configures** the pipeline — it does not execute it.

After `harness_update`, direct the user to `/run-pipeline` to run the pipeline. If deploy inputs
are required, the user provides them at run time via `/run-pipeline` or Harness UI Run.

## Troubleshooting (CD-specific)

| Symptom | Fix |
|---------|-----|
| SBOM step not in Initialize / no SSCA plugin pod | Step not in containerized group — move under `stepGroup` + `stepGroupInfra` |
| `connectorRef` required on stepGroupInfra | Add `KubernetesDirect.spec.connectorRef` |
| Manifest unknown at SBOM time | Image not in registry yet — move SBOM **before** deploy but **after** artifact is published (often prior CI stage or rolling tag) |
| Wrong image scanned | Use `<+artifact.image>` / service artifact expressions instead of stale literal tag |
| Parallel SBOM + SLSA failures | Run attestation steps **sequentially** in the same group |

## Harness docs

- [Generate SBOM for Artifacts — Deploy stage](https://developer.harness.io/docs/software-supply-chain-assurance/open-source-management/generate-sbom-for-artifacts)
- [Containerized step groups](https://developer.harness.io/docs/continuous-delivery/x-platform-cd-features/cd-steps/containerized-steps/containerized-step-groups/)
