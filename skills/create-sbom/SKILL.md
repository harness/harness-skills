---
name: create-sbom
description: >-
  Add an SBOM (Software Bill of Materials) generation step to an existing Harness pipeline
  using Harness SCS SscaOrchestration (SBOM Orchestration). Supports container images and code
  repositories. Sources: docker, ECR, GCR, GAR, ACR, Harness AR (har), repository, and local workspace.
  Syft or cdxgen, SPDX or CycloneDX, optional SBOM attestation.
  Only works with existing pipelines. Use when asked to create an SBOM, generate a bill of
  materials, add SBOM to a pipeline, scan a container image or repo for components, or set up
  SBOM Orchestration.
  Trigger phrases: create SBOM, generate SBOM, add SBOM step, SBOM for image, SBOM for repo,
  scan for dependencies, SBOM Orchestration, add Generate SBOM step.
metadata:
  author: Harness
  version: 2.8.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Create SBOM

Add an **SBOM Orchestration** (`SscaOrchestration`) step to an existing Harness pipeline for a
container image or code repository. This skill only works with **existing pipelines** — do not
create standalone SBOM pipelines.

**Supported stages:** SBOM Orchestration runs in **CI**, **CD** (`Deployment`), and **Security**
(`Security`) stages. Show stage type in Phase 2 and offer placement options that match the stage
type (see `references/interactive-wizard-flow.md`).

Guide the user through a **step-by-step interactive wizard** (same UX as `/configure-repo-scan`):
one decision per turn, recommended options marked, pipeline structure
shown after fetch, then confirm before `harness_update`.

- Wizard scripts: `references/interactive-wizard-flow.md`
- UI ↔ YAML mapping: `references/sbom-orchestration-step.md`
- CD containerized step groups: `references/cd-containerized-step-group.md`

---

## Interaction model (mandatory)

Follow this UX for every invocation. **Do not** dump all Pipeline Studio fields in one message.

1. **One question per turn** — use the `AskQuestion` tool when available. If unavailable, use a
   numbered option list with `(Recommended)` on the default choice (same pattern as container scan).
2. **Opening message** — briefly state the goal: add SBOM Orchestration to an existing pipeline.
3. **Progress breadcrumb** — after pipeline fetch, show on each wizard turn:
   `Pipeline · Placement · Method · Source · Details · Attestation · Submit · Run`
4. **Record answers** — keep a running summary of choices; do not re-ask unless the user changes direction.
5. **Fetch before configure** — `harness_get` (URL or id) before placement/source questions.
6. **Show pipeline structure** — list stages and steps (Phase 2) before asking placement.
7. **Infer, don’t assume** — suggest connector/source from YAML; skip connector question if unambiguous.
8. **Never guess image tags** — always ask for image or repo+branch in Phase 8.
9. **Confirm before write** — Phase 10 summary + `harness_update` only after user confirms.
10. **“Defaults” shortcut** — apply recommended wizard choices (see reference) but still ask for image/repo.
11. **Auto-run after update** — after a successful `harness_update`, **automatically** trigger the
    pipeline with `harness_execute` (action: `run`) for **CI-only** changes when inputs are
    inferrable. For **CD** placement or new Deploy stages, see **CD auto-run** below — do not guess
    service/env/infra inputs.
12. **Phase 3 Placement is never optional** — always run Phase 2 (structure) then Phase 3
    (`AskQuestion` for stage + position) **before** method/source/attestation, even when:
    - The pipeline has only one CI stage
    - An `SscaOrchestration` step already exists in CI
    - The user said “add SBOM to the pipeline” without naming a stage
    - A prior chat configured the same pipeline (do **not** reuse that to skip Placement)
13. **Never assume pipeline or stage from session history** — confirm pipeline URL/ID in Phase 0/1
    unless the user pasted it **in the current message**. Prior workspace context may inform
    suggestions, not replace the wizard.
14. **CD is a different placement path** — if the user chooses a `Deployment` stage (or asks for CD),
    follow `references/cd-containerized-step-group.md` end to end (step group, `<+artifact.image>`,
    infra). Do not place CD SBOM under `execution.steps` at the stage top level.
15. **CI-only pipeline + CD SBOM** — if Phase 2 shows **no** `Deployment` stage and the user wants
    CD, run the **CD prerequisites** sub-flow (service, environment, infrastructure, K8s connector
    for `stepGroupInfra`) before `harness_update`. See **CD edge case** below.

Full phase prompts and option ids: `references/interactive-wizard-flow.md`.

---

## Instructions

### Wizard phases (user-facing)

Run in order. **Stop after each phase** until the user answers.

| Phase | Breadcrumb | Action |
|-------|------------|--------|
| 0 | Pipeline | AskQuestion: pipeline URL ready? |
| 1 | Pipeline | Collect URL or org/project/id → `harness_get` |
| 2 | Pipeline | Display pipeline structure (no question) |
| 3 | Placement | **Mandatory** `AskQuestion`: target stage (CI / Deployment / Security) + position; see **CD edge case** if no Deploy stage |
| 3b | Placement (CD only) | If no `Deployment` stage: service, environment, infra, `stepGroupInfra` connector — then add stage + SBOM |
| 4 | Method | AskQuestion: Syft/SPDX, CycloneDX, cdxgen, or ingestion |
| 5 | Source | AskQuestion: source tile (Third-Party, HAR, Repository, Local) |
| 6 | Source | AskQuestion: registry provider (Third-Party only) |
| 7 | Details | AskQuestion: connector (skip if obvious from YAML) |
| 8 | Details | Ask: image, repo URL, or local artifact (free text) |
| 9 | Attestation | AskQuestion: attest or not; keyless vs cosign |
| 10 | Submit | AskQuestion: confirm pipeline update |
| 11 | Run | Auto-trigger pipeline + monitor (no user prompt) |

### Supported stage types

| Stage type (YAML) | Module | SBOM placement notes |
|-------------------|--------|----------------------|
| `CI` | CI | End of stage or after build/push; repository source needs `cloneCodebase: true` + codebase |
| `Deployment` | CD | Inside a **containerized step group** with `stepGroupInfra`; **before** deploy — see `references/cd-containerized-step-group.md` |
| `Security` | STO / SCS | End of `spec.execution.steps` (alongside other security steps) |

When listing stages in Phase 2, include the stage **type** (`CI`, `Deployment`, `Security`, etc.).
For **Deployment** stages, label each `stepGroup` as **containerized** or **not** (presence of
`stepGroupInfra`). In Phase 3, only offer placement options valid for the chosen stage (see wizard
reference). **Never** insert `SscaOrchestration` at the top level of a CD stage `execution.steps`.

### CD edge case (mandatory workflow)

Use when Placement targets a **`Deployment`** stage, or the user wants SBOM at deploy time.

#### Phase 2 — CI-only pipeline warning

If the pipeline has **only** `CI` (or `Security`) stages and **no** `type: Deployment` stage, print:

> This pipeline has no CD Deploy stage yet. SBOM in CD must run in a **Deployment** stage inside a
> **containerized step group** before the deploy step.

Then **AskQuestion**: add a new Deploy stage, use a different pipeline URL, or keep SBOM in CI only.
Do **not** default to the existing CI stage without asking.

#### Phase 3 — Placement (always ask)

Even with a single `Build` CI stage, ask:

1. **Which stage?** — list every `CI`, `Deployment`, and `Security` stage by identifier.
2. **Position in that stage?** — `ci_*`, `cd_*`, or `security_*` options per wizard reference.

If `SscaOrchestration` already exists in CI, include options such as:

| Option | Meaning |
|--------|---------|
| Keep CI SBOM + add CD SBOM | New step (e.g. `generate_sbom_cd`) in Deploy stage |
| CD only | User will remove or skip CI SBOM (confirm in Phase 10) |
| Replace / move | Rare — confirm source and target stages explicitly |

#### Phase 3b — CD prerequisites (no Deploy stage yet)

Run **one topic per turn** (`AskQuestion` where possible):

| Step | Action |
|------|--------|
| Service | `harness_list` / user pick → `serviceRef` (artifact connector drives registry SBOM connector) |
| Environment | User pick → `environmentRef` |
| Infrastructure | `harness_list` with `params: { environment_id: "<env>" }`; if none, `harness_create` (`KubernetesDirect`) per `/create-infrastructure` — **never** omit `infrastructureDefinitions` on the Deploy stage |
| Step group infra | `AskQuestion`: K8s cluster connector + namespace for `stepGroupInfra` (copy from stage infra when possible) |
| Deploy step type | Default `K8sRollingDeploy` for `deploymentType: Kubernetes` services |

Append a new stage after CI (typical):

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
                    identifier: generate_sbom_cd
                    name: Generate SBOM
                    type: SscaOrchestration
                    # ... wizard spec; image: <+artifact.image> for service artifacts ...
          - step:
              identifier: rolling_deployment
              type: K8sRollingDeploy
              spec:
                skipDryRun: false
              timeout: 10m
      rollbackSteps:
        - step:
            identifier: rollback
            type: K8sRollingRollback
            spec: {}
            timeout: 10m
    failureStrategies:
      - onFailure:
          errors: [AllErrors]
          action:
            type: StageRollback
```

Full rules and examples: `references/cd-containerized-step-group.md`.

#### CD step identifiers and image

- Use a **unique** step id in CD (e.g. `generate_sbom_cd`) when CI already has `generate_sbom`.
- **CD image:** prefer `<+artifact.image>` from the service primary artifact; literal tags only if
  the user provides them in Phase 8.
- **Registry connector:** from `service.serviceDefinition.spec.artifacts` or existing CI SBOM step.

#### CD auto-run (differs from CI)

After `harness_update` that adds or changes a **Deployment** stage:

- **Do not** auto-run the full pipeline if execute fails on missing **service artifact**,
  **environment**, or **infrastructure** inputs.
- **May** auto-run when the change is **CI-only** (same pipeline, no new CD stage) and branch/tag
  inputs are inferrable.
- On CD input failure: report required runtime fields and link to Pipeline Studio / Run — do not
  silently pick `aiskillstest` or any pipeline from prior sessions.

### After the wizard — backend steps

#### Extract connectors from pipeline YAML

**Container / Third-Party:** `connectorRef` or `connector` in `BuildAndPushDockerRegistry`, `Run`,
`Plugin`, `StoAgent`, `SscaOrchestration`, `SscaArtifactSigning`.

**Repository:** v0 `pipeline.properties.ci.codebase.connectorRef`; v1 codebase connector →
`spec.overrideConnectorRef`.

If repository SBOM and no codebase connector → stop and explain. If container SBOM and no registry
connector → `harness_search` (connectors) or `/create-connector`.

#### Generate SBOM step configuration

Using **only the options recorded in the wizard**, generate native `SscaOrchestration` YAML — not a
`Run: syft` step. If the user chose the **defaults** shortcut, use Generation + Syft + SPDX +
Third-Party/docker + keyless attestation.

**Third-Party — Docker Registry (default):**

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
          connector: <docker_registry_connector_from_step_2>
          image: <repo/name:tag_or_digest>
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

**Repository:**

```yaml
- step:
    identifier: generate_sbom
    name: Generate SBOM
    type: SscaOrchestration
    spec:
      mode: generation
      overrideConnectorRef: <git_connector_from_step_2>
      source:
        type: repository
        spec:
          url: <full_repo_url>
          variant_type: branch
          variant: <branch>
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

**Amazon ECR (`source.type: ecr`):**

```yaml
      source:
        type: ecr
        spec:
          connector: <registry_connector>
          image: <repo/name:tag_or_digest>
          region: <aws_region>
          account: <aws_account_id>
```

**Google GCR (`source.type: gcr`):**

```yaml
      source:
        type: gcr
        spec:
          connector: <docker_registry_connector>
          host: gcr.io
          project_id: <gcp_project_id>
          image: <repo/name:tag_or_digest>
```

**Google GAR (`source.type: gar`):**

```yaml
      source:
        type: gar
        spec:
          connector: <docker_registry_connector>
          host: <region>-docker.pkg.dev
          project_id: <gcp_project_id>
          image: <repo/name:tag_or_digest>
```

**Azure ACR (`source.type: acr`):**

```yaml
      source:
        type: acr
        spec:
          connector: <docker_registry_connector>
          image: <registry>.azurecr.io/<repo>:<tag>
          subscription_id: <azure_subscription_id>
```

**Harness Artifact Registry (`source.type: har`):**

```yaml
      source:
        type: har
        spec:
          registry: <harness_artifact_registry_identifier>
          image: <image_name:tag_or_digest>
```

**Harness Local Stage (`source.type: local`):**

```yaml
      source:
        type: local
        spec:
          artifact_name: <artifact_name>
          workspace: <optional_workspace_path>
          version: <optional_version>
```

Use when the artifact already exists in the stage workspace. For JAR/Helm/non-container artifacts
without a registry image, users may need **ingestion** mode instead — see Harness ingest SBOM docs.

**CycloneDX (when requested):** change `format` to `cyclonedx-json`.

**No attestation (when requested):** omit the `attestation` block.

Full UI mapping and notes: `references/sbom-orchestration-step.md`.

**Image formatting (docker / ecr / gcr / gar / acr / har):**
- Docker Hub: `lavakush07/myapp:v7` — no leading `/`, no `https://`, no `docker.io/` unless required
- Use one `image` field for `docker` source — not split `url` + `variant`

---

#### Insert step into pipeline YAML

Insert at the placement chosen in Phase 3. Ensure proper indentation.

**Key rules:**
- Insert only the new step — do not modify existing steps, variables, or failure strategies
- **CI / Security:** add under `stage.spec.execution.steps` (or inside a non-CD step group if user chose one)
- **CD (Deployment):** **mandatory** — insert under `stepGroup.steps` of a containerized group (`stepGroupInfra` set). See `references/cd-containerized-step-group.md`
- **CI + repository source:** ensure `cloneCodebase: true` and `properties.ci.codebase` on the CI stage
- **CD placement:** before the deploy step; use artifact expressions for `image` when possible (`<+artifact.image>`)
- **CD — no containerized group:** create `cd_new_containerized_group` (new `stepGroup` + `stepGroupInfra`) or stop and instruct user — do not use top-level `execution.steps`
- **Security:** append to stage `execution.steps`; registry or repository per source choice
- Step identifier: `generate_sbom` in CI; use `generate_sbom_cd` (or suffix) in CD when CI already has `generate_sbom`

**CD containerized step group (summary):**

```yaml
- stepGroup:
    identifier: <scs_step_group_id>
    name: Supply Chain Security
    stepGroupInfra:
      type: KubernetesDirect
      spec:
        connectorRef: <k8s_cluster_connector>
        namespace: <namespace>
    steps:
      - step:
          identifier: generate_sbom
          type: SscaOrchestration
          # ... spec from wizard ...
- step:
    identifier: <deploy_step>
    type: K8sRollingDeploy   # unchanged; SBOM group must appear BEFORE this
```

Copy `stepGroupInfra` from an existing containerized group in the pipeline when possible.

Create the full updated pipeline YAML string.

---

#### Update pipeline via MCP

```
Call MCP tool: harness_update
Parameters:
  resource_type: "pipeline"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  body: { yamlPipeline: "<updated pipeline YAML string>" }
```

On validation errors, read the API message, fix the field, and retry.

---

#### Auto-run pipeline (mandatory after successful update)

Do **not** stop after `harness_update` or ask the user to run the pipeline. Immediately execute:

```
Call MCP tool: harness_execute
Parameters:
  resource_type: "pipeline"
  action: "run"
  resource_id: "<pipeline_identifier>"
  org_id: "<organization>"
  project_id: "<project>"
  inputs: <auto-resolved from wizard — see below>
```

**Runtime input resolution (no user prompt):**

| Wizard / pipeline signal | Pass to `inputs` |
|--------------------------|------------------|
| Repository SBOM + `variant` (branch) | `{ "branch": "<variant>" }` or `{ "build": { "type": "branch", "spec": { "branch": "<variant>" } } }` if API expects nested build |
| Codebase `build: <+input>` on pipeline | Same branch/tag recorded in Phase 8 |
| Container-only pipeline, no `<+input>` | Omit `inputs` or `{}` |
| MCP `_inputResolution.matched` on prior run | Reuse same shape Harness accepted |

If `harness_execute` fails on missing inputs, read the error, derive values **only** from wizard
answers (never ask the user for run inputs), retry once. If still blocked (e.g. required deploy
variables with no default), report the missing YAML field and the execution link — do not run an
interactive “provide inputs” flow.

**Monitor execution** (poll `harness_get` resource_type: `execution` every 20–30s until terminal
status or ~10 minutes). On failure, use `harness_diagnose` and summarize the failing step.

**Production CD pipelines:** if the target stage deploys to Production, still auto-run only when
the user already confirmed Phase 10 for that pipeline; do not add an extra run confirmation.

**CD placement or new Deploy stage added:** skip auto-run unless the user explicitly asks to run
the full pipeline in the same turn **and** prior executions show Harness accepted the same
`inputs` shape for service/env/infra. Otherwise summarize what to select at **Run** in the UI.

---

#### Provide summary and next steps

```
## SBOM Orchestration Configured

**Pipeline:** <pipeline_name>
**Step:** Generate SBOM (SscaOrchestration)
**Location:** Stage "<stage_name>", <position description>
**Mode:** Generation
**Source:** Third-Party → Docker Registry (or Repository / HAR as configured)
**Connector:** <connector_identifier>
**Image / repo:** <image_or_repo_url>
**Tool / format:** Syft / SPDX (spdx-json)
**Attestation:** Keyless (Harness OIDC) — or as configured

**Execution:** <execution_id> — <Success | Failed | Running>
**Execution URL:** <openInHarness from harness_execute or harness_get>

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/ci/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

**Note:** Review the SBOM Orchestration step in Pipeline Studio to adjust Advanced settings
(resources, SBOM drift, expressions on image field).

### Next Steps
1. If execution **Failed**, fix the reported step (connectors, credentials, image tag) and re-run
2. View the SBOM on the **Supply Chain** tab of the execution and in SCS **Artifacts**
3. Download SBOM via Artifacts UI or [SBOM API](https://apidocs.harness.io/sbom/downloadsbomforartifact)
4. Enforce SBOM policies via `/enforce-sbom` (pipeline step) and `/create-policy` (OPA rules)
5. For automatic runs on push/PR, add a trigger via `/create-trigger`
```

---

## Examples

### Add SBOM to existing CI pipeline (container)

```
/create-sbom
Add SBOM generation to my backend-api pipeline in the platform project for lavakush07/myapp:v7
```

### Repository SBOM

```
/create-sbom
Add Generate SBOM to my PR pipeline — repository source, branch main
```

### SPDX + attestation defaults

```
/create-sbom
Configure SBOM Orchestration on ci-build-deploy after docker push — Syft, SPDX, keyless attest
```

### CycloneDX, no attestation

```
/create-sbom
Add SBOM step with CycloneDX only, no attestation
```

### CD Deploy stage (containerized step group)

```
/create-sbom
Add Generate SBOM to Deploy_Production before K8s rolling deploy — use artifact image expression
```

### CI-only pipeline — add SBOM in new CD stage

```
/create-sbom
Pipeline has only a Build CI stage — add a Deploy Dev stage with containerized Generate SBOM before K8s rolling deploy
```

### Placement must be explicit (anti-pattern)

```
/create-sbom
add the sbom step to the pipeline
```

Agent must still run Phase 2 + Phase 3 (stage picker), not assume CI or prior session config.

---


## Performance Notes

- Only works with **existing pipelines** — do not offer to create new pipelines
- **Wizard UX is mandatory** — one `AskQuestion` (or one numbered menu) per turn; see `references/interactive-wizard-flow.md`
- **Phase 3 Placement is mandatory every invocation** — never skip because of one CI stage, existing SBOM, or prior chat context
- **Do not assume pipeline/stage** from workspace history — confirm in Phase 0/1 unless URL/ID is in the current user message
- Do **not** paste the full Pipeline Studio checklist in a single message
- `harness_get` once after Phase 1; show structure before Placement
- Extract connectors from YAML; skip Phase 7 when unambiguous
- **Defaults** shortcut: Syft + SPDX + Third-Party/docker + keyless — still ask for image/repo in Phase 8
- Container SBOM after image push; repository SBOM needs `cloneCodebase: true` + codebase
- Never infer image tags from `Run` scripts
- Use `source.type: docker` with `connector` + `image` — not legacy `url`/`variant` on docker source
- Run SBOM and SLSA attestation **sequentially**, not in parallel (Cosign registry race)
- YAML per provider: `references/sbom-orchestration-step.md`
- **Supported stages:** CI, CD (`Deployment`), Security — label types in Phase 2; filter Phase 3 options
- **CD edge case:** SBOM only inside `stepGroup` with `stepGroupInfra`; CI-only → CD needs Phase 3b — `references/cd-containerized-step-group.md`
- **Auto-run:** CI changes → `harness_execute` + monitor when inputs inferrable; CD/new Deploy stage → report run requirements unless execute succeeds without deploy inputs

---

## Troubleshooting

### Pipeline Not Found
- Verify `org_id` and `project_id` are correct
- Confirm the pipeline exists with `harness_list` (resource_type: `pipeline`)

### Connector Not Found in Pipeline
- **docker / image / ecr / gcr / gar / acr:** search pipeline YAML for `connectorRef` or `harness_search` for registry connectors
- **har:** user must provide Harness Artifact Registry identifier (`registry` field)
- **repository:** set `properties.ci.codebase.connectorRef` (v0) or v1 codebase block
- **local:** no registry connector — artifact must exist in workspace from a prior step

### Wrong Source Type for Registry
- Docker Hub / generic registry → `docker` (not `ecr` unless image is in ECR)
- ECR images → `ecr` + `region` + `account`
- GCR vs GAR → `gcr` vs `gar` with correct `host` and `project_id`
- ACR → `acr` + full image path under `.azurecr.io`

### Image Not Found / Invalid Reference
- Symptom: `invalid reference format` or `skopeo fallback failed`
- Use single `source.spec.image` — e.g. `lavakush07/myapp:v7`, not `/lavakush07/myapp` or split fields

### SBOM Attestation Failed (Keyless)
- Harness OIDC requires Harness CI execution context
- **non-harness:** SCS → Manage → Configuration → **Connector for Keyless Signing**
- JFrog: connector needs `Read`, `Annotate`, `Create/Deploy`, `Delete` for `.att` upload

### Repo SBOM — 0 Components
- `cloneCodebase: false` or missing `properties.ci.codebase` on CI stage

### Pipeline Update Validation Errors
- Step identifier pattern: `^[a-zA-Z_][0-9a-zA-Z_]{0,127}$`
- Valid `source.type` and required `spec` fields per provider
- `DUPLICATE_IDENTIFIER` — rename `generate_sbom`

### No SBOM in Artifacts After Run
- Confirm execution reached success on the SBOM Orchestration step
- Check step logs; verify image exists in registry at scan time
- List components later via `/security-report` or `scs_artifact_component` MCP resources

### MCP Errors
- `CONNECTOR_NOT_FOUND` — verify connector identifier in Project Settings → Connectors
- `ACCESS_DENIED` — PAT with pipeline edit permission

### Skipped Placement / Wrong Stage
- Symptom: SBOM added to CI when user wanted CD (or vice versa)
- Cause: agent skipped Phase 3 or assumed stage from prior session
- Fix: re-run wizard from Phase 2; ask stage + `cd_*` vs `ci_*` placement; move step under CD `stepGroup.steps`

### CD — infrastructureDefinitions Missing
- Symptom: `infrastructureDefinitions or infrastructureDefinition should be present in stage`
- Fix: add `environment.infrastructureDefinitions[].identifier` or create infra via `harness_create` (`/create-infrastructure`)

### Auto-run Failed After Update
- **Bad credentials (codebase-sync):** fix Git connector on CI/repository SBOM pipelines
- **Missing runtime inputs:** map Phase 8 branch/tag into `inputs` for `properties.ci.codebase.build`
- **CD containerized:** SBOM must be under `stepGroup.steps` with `stepGroupInfra` (`KubernetesDirect` or `VM`) — not top-level `execution.steps`; see `references/cd-containerized-step-group.md`
- **CD — no Initialize / SSCA pod:** step group missing `stepGroupInfra` or container-based execution not enabled
- **CD — wrong image:** use `<+artifact.image>` (or expression from service artifact), not a stale literal tag
- **Security stage:** confirm stage `type: Security` and artifact source matches prior steps (registry vs repo)
