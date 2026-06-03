# SBOM Orchestration — Interactive Wizard

Use with `/create-sbom` **Interaction model**. Each phase = **one** `AskQuestion` (or one free-text
prompt) per assistant turn. Claude Code may append **Type something** / **Chat about this** in the UI;
you do not need to list those in skill options.

## Progress breadcrumb

Show on every wizard turn after pipeline fetch:

`Pipeline · Placement · Method · Source · Details · Attestation · Submit`

Highlight the active phase. Completed phases may be summarized in one line above the question.

---

## Phase 0 — Pipeline readiness

**AskQuestion title:** `Create SBOM — pipeline`

**Prompt:** Do you have the pipeline identifier or Harness UI URL ready?

| Option id | Label |
|-----------|--------|
| `has_url` | Yes, I have the pipeline ID/URL |
| `need_help` | Not yet — help me find it |

If `need_help`, use `harness_list` (resource_type: `pipeline`) after org/project are known, or ask
for org + project in a **separate** turn first.

---

## Phase 1 — Pipeline URL or identifiers

**Do not use AskQuestion** — ask in prose:

> Please share your pipeline URL or identifier, along with org and project if you have them. You can
> paste a Harness UI URL and I'll extract the details automatically.

Then:

```
harness_get(url="<url>", resource_type="pipeline")
# or resource_id + org_id + project_id
```

---

## Phase 2 — Show pipeline structure (no question)

After fetch, print:

```
Pipeline: <name> (<identifier>)
Org: <org_id> | Project: <project_id>

Stage 1: <stage_name> (type: CI | Deployment | Security | …)
  1: <step_id> (type: <step_type>) — <short description if obvious>
  stepGroup: <group_id> (containerized: yes | no)   # Deployment stages only
    1: <step_id> (type: <step_type>)
  ...
```

**Stage types for SBOM:** `CI`, `Deployment` (CD), and `Security` are supported. Call out which of
these exist so Phase 3 can offer valid placements.

**Deployment (CD) stages — mandatory:** For each `stepGroup`, set **containerized: yes** when
`stepGroupInfra` is present (`type: KubernetesDirect` or `VM`). If the stage has **no**
containerized group, print a warning: *SBOM must go in a containerized step group — Phase 3 will
offer to create one.* Full rules: `cd-containerized-step-group.md`.

Note existing `SscaOrchestration` steps (including inside CD step groups). Parse connectors
(registry + Git + K8s for `stepGroupInfra`) for later phases.

**CI-only pipeline (no `Deployment` stage):** after the structure table, add a warning line and
proceed to Phase 3 — include options to add a CD stage or stay in CI (see Phase 3b).

---

## Phase 3 — Placement (mandatory — never skip)

**This phase is required on every `/create-sbom` invocation.** Do not skip because:

- The pipeline has only one CI stage
- `SscaOrchestration` already exists
- A prior conversation configured the same pipeline
- The user said “add SBOM to the pipeline” without naming a stage

**AskQuestion title:** `Placement` (breadcrumb: **Placement** active)

### Turn A — Stage picker (always)

**Prompt:** Which stage should contain the SBOM Orchestration step?

List **every** stage whose type is **CI**, **Deployment**, or **Security** — even if there is only
one. If SBOM already exists in a stage, note it in the label (e.g. `Build (CI) — already has generate_sbom`).

| Option id | Label |
|-----------|--------|
| `<stage_identifier>` | `<stage_name>` (type: CI \| Deployment \| Security) |
| `add_cd_stage` | Add a new CD Deploy stage (pipeline is CI-only today) |
| `other_pipeline` | Use a different pipeline — I'll paste URL |

If the user picks `add_cd_stage`, go to **Phase 3b** before Turn B.

### Turn B — Position within the chosen stage

**AskQuestion** in the **next** turn (or second question in the same `AskQuestion` if the UI
supports multiple questions).

| Option id | Label | Valid for stage type |
|-----------|--------|----------------------|
| `ci_end` | CI — at the end of stage | `CI` |
| `ci_after_build` | CI — after image build/push (Recommended when `BuildAndPush*` exists) | `CI` |
| `ci_after_step` | CI — after a specific step | `CI` — follow up: step name |
| `cd_containerized_end` | CD — end of existing containerized step group (Recommended when group exists) | `Deployment` |
| `cd_containerized_after_step` | CD — after a step inside containerized group | `Deployment` |
| `cd_new_containerized_group` | CD — new containerized step group before deploy (Recommended when no group) | `Deployment` |
| `security_end` | Security — at the end of stage | `Security` |
| `security_after_step` | Security — after a specific step | `Security` |
| `ci_and_cd` | Keep CI SBOM and add a separate CD SBOM step | When CI already has SBOM and user chose Deploy stage |

**Do not offer** `ci_*` for `Deployment` stages or `cd_*` for `CI` stages (except `ci_and_cd` as a
meta-choice when explaining dual placement — then run Turn B twice: once for CI, once for CD).

If multiple containerized groups exist in the chosen CD stage, follow up: which `stepGroup`
identifier?

**Recommendations:**
- **CI + repository source:** `ci_end` after clone/build steps; requires `cloneCodebase` + codebase.
- **CI + container image:** after image push or at end of stage.
- **CD:** inside `stepGroup.steps` with `stepGroupInfra` — **before** deploy; see `cd-containerized-step-group.md`.
- **CD + no Deploy stage yet:** `add_cd_stage` → Phase 3b, then `cd_new_containerized_group`.
- **Security:** append alongside STO/SCS steps; registry image is common.

---

## Phase 3b — CD prerequisites (CI-only pipeline → new Deploy stage)

Run when the user chose **`add_cd_stage`** or Placement targets CD but Phase 2 showed **no**
`type: Deployment` stage. **One decision per turn.**

| Turn | AskQuestion / topic |
|------|---------------------|
| 1 | **Service** — `harness_list` (resource_type: `service`); recommend service whose artifact matches the image/repo from CI |
| 2 | **Environment** — `harness_list` (resource_type: `environment`) |
| 3 | **Infrastructure** — `harness_list` (resource_type: `infrastructure`, `params: { environment_id: "<env>" }`); if empty, offer to create `KubernetesDirect` via `harness_create` |
| 4 | **Step group K8s** — connector + namespace for `stepGroupInfra` (not the same as deploy target infra, but may copy connector) |
| 5 | **CI SBOM** — keep existing CI `generate_sbom`, CD-only, or remove CI SBOM (confirm in Phase 10) |

Record: `serviceRef`, `environmentRef`, `infrastructureDefinitions[].identifier`, `stepGroupInfra`
connector/namespace, new stage identifier (e.g. `Deploy_Dev`).

Then continue to Phase 4 (Method). For CD SBOM image in Phase 8, default to **`<+artifact.image>`**.

---

## Phase 4 — SBOM method (tool + format)

**AskQuestion title:** `SBOM method`

**Prompt:** How should the SBOM be produced? (matches Pipeline Studio **SBOM Method**)

| Option id | Label |
|-----------|--------|
| `defaults` | Syft + SPDX — Generation (Recommended) |
| `cyclonedx` | Syft + CycloneDX — Generation |
| `cdxgen` | cdxgen + CycloneDX — Generation (monorepos) |
| `ingestion` | Ingestion — I already have an SBOM file |

If `ingestion`, ask in the **next** turn for file path / ingestion spec (see Harness ingest SBOM docs)
before continuing to Source.

---

## Phase 5 — Source tile

**AskQuestion title:** `Source`

**Prompt:** Where is the artifact for SBOM generation?

| Option id | Label | `source.type` |
|-----------|--------|----------------|
| `third_party` | Third-Party Registry — Docker Hub, ECR, GCR, GAR, ACR, etc. (Recommended) | `docker` / `ecr` / `gcr` / `gar` / `acr` |
| `har` | Harness Artifact Registry | `har` |
| `repository` | Repository — Git source in CI | `repository` |
| `local` | Harness Local Stage — artifact in workspace | `local` |

---

## Phase 6 — Provider (Third-Party only)

Skip if source ≠ `third_party`.

**AskQuestion title:** `Registry provider`

**Prompt:** Which registry provider hosts your image?

| Option id | Label | `source.type` |
|-----------|--------|----------------|
| `docker` | Docker Registry (Recommended) | `docker` |
| `ecr` | Amazon ECR | `ecr` |
| `gcr` | Google GCR | `gcr` |
| `gar` | Google Artifact Registry (GAR) | `gar` |
| `acr` | Azure ACR | `acr` |

---

## Phase 7 — Connector

**AskQuestion** only if pipeline YAML did not yield exactly one obvious connector.

**Prompt:** Which connector should SBOM Orchestration use?

Build options from:
- Connectors found in pipeline YAML (label: `Use from pipeline: <id> (Recommended)`)
- `harness_search` for `docker registry` if none found

If exactly one registry connector exists in YAML, **skip** this phase and use it; tell the user
which connector was auto-selected.

---

## Phase 8 — Image / repo details

**Do not use AskQuestion** unless offering branch/tag as choices.

Ask in prose based on source:

| Source | Ask |
|--------|-----|
| `docker` / `ecr` / `gcr` / `gar` / `acr` / `har` | Image reference (`org/repo:tag` or digest). Do not guess tags. |
| CD (`Deployment`) + service artifact | Prefer `<+artifact.image>` or expression from Pipeline Studio; literal tag only if user insists |
| `ecr` | Also region + AWS account ID if not in pipeline |
| `gcr` / `gar` | Also `host` + GCP `project_id` if not inferrable |
| `acr` | Full image under `.azurecr.io`; subscription ID if needed |
| `har` | Harness registry identifier + image |
| `repository` | Repo URL + branch/tag/commit (`variant_type` + `variant`) |
| `local` | `artifact_name`; optional workspace path |

---

## Phase 9 — Attestation

**AskQuestion title:** `Attestation`

**Prompt:** Should the SBOM be attested?

| Option id | Label |
|-----------|--------|
| `keyless_harness` | Attest SBOM — Keyless with Harness OIDC (Recommended) |
| `keyless_non_harness` | Attest SBOM — Keyless with non-Harness OIDC |
| `cosign` | Attest SBOM — Cosign key pair (secrets required) |
| `none` | Do not attest SBOM |

---

## Phase 10 — Confirm

**AskQuestion title:** `Submit`

**Prompt:** Ready to update the pipeline with this SBOM Orchestration step?

Show a short summary:

- Pipeline, stage, position
- Tool / format / mode
- Source type, connector, image or repo
- Attestation on/off

| Option id | Label |
|-----------|--------|
| `confirm` | Yes, update the pipeline |
| `cancel` | No, let me change something |

On `confirm` → generate YAML, insert step, `harness_update`, then provide configuration summary.
On validation error, fix and retry without re-running the full wizard unless the user asks.

**Do not** call `harness_execute` or monitor executions — direct the user to `/run-pipeline`.

---

## Defaults shortcut

If the user says **"defaults"** at any point after pipeline fetch, set:

- Method: Syft + SPDX, generation
- Source: Third-Party → Docker Registry
- Attestation: keyless + Harness OIDC

**Still run Phase 3 Placement** — defaults do **not** set stage or `ci_end` automatically. After
Placement, use `ci_end` or `ci_after_build` only if the user chose a **CI** stage; use `cd_*` only
for **Deployment**.

Still ask for **image** (or repo URL + branch) in Phase 8 — never guess tags. For CD placement,
offer `<+artifact.image>` as the recommended default in the prompt text.

---

## Anti-patterns (do not do this)

| Anti-pattern | Correct behavior |
|--------------|------------------|
| Skip Phase 3 because pipeline only has `Build` (CI) | Always ask stage + position; offer `add_cd_stage` |
| Reuse prior chat’s pipeline/stage without Phase 0/1 | Confirm URL/ID in current session |
| Auto-run pipeline after configuration | Stop after `harness_update`; use `/run-pipeline` to execute |
| Put `SscaOrchestration` at CD `execution.steps` top level | Use containerized `stepGroup` + `stepGroupInfra` |
| Reuse `generate_sbom` identifier in CI and CD | Use `generate_sbom_cd` (or similar) in CD |
| Default Placement to CI when user asked about CD | Ask explicitly; follow `cd-containerized-step-group.md` |
