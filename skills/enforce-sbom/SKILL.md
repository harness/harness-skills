---
name: enforce-sbom
description: >-
  Add an SBOM Policy Enforcement (SscaEnforcement / CdSscaEnforcement) step to an existing Harness
  pipeline to verify SBOM attestations and apply OPA SBOM policy sets. Supports CI, Security, and CD
  (Deployment) including CI-only pipelines — if no Deploy stage exists, add one via Phase 3b
  (service, environment, infra, containerized step group) then place CdSscaEnforcement before deploy.
  Supports container images and repositories from Artifact Registry, Third-Party registries (docker,
  ECR, GCR, GAR, ACR), and Git. Matches Pipeline Studio SBOM Policy Enforcement UI. Only works with
  existing pipelines (may append a Deploy stage). Use when asked to enforce SBOM policies, add SBOM
  policy enforcement, verify SBOM attestation in pipeline, or block non-compliant components.
  Trigger phrases: enforce SBOM, SBOM policy enforcement, SBOM policy step, verify SBOM policy,
  SscaEnforcement, add policy enforcement after SBOM.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Enforce SBOM

Add an **SBOM Policy Enforcement** (`SscaEnforcement` / `CdSscaEnforcement`) step to an existing
Harness pipeline. The step verifies SBOM attestations (when enabled) and evaluates SBOM OPA policy
sets against the artifact's bill of materials.

This skill only works with **existing pipelines** — do not create standalone enforcement-only pipelines.

**Prerequisites:** An SBOM must already exist for the artifact (typically from `SscaOrchestration` via
`/create-sbom` or SBOM ingestion). SBOM **policy sets** must exist (`/create-policy`).

**Supported stages:** CI, CD (`Deployment`), and Security — same as SBOM Orchestration. CD requires a
**containerized step group** with container-based execution.

Guide the user through a **step-by-step interactive wizard** (same UX as `/create-sbom`):

- Wizard: `references/interactive-wizard-flow.md`
- UI ↔ YAML: `references/sbom-enforcement-step.md`
- CD containerized step groups (new or existing Deploy stage): `skills/create-sbom/references/cd-containerized-step-group.md`

---

## Interaction model (mandatory)

1. **One question per turn** — use `AskQuestion` when available; otherwise numbered options with `(Recommended)`.
2. **Opening message** — add SBOM Policy Enforcement to an existing pipeline; mention SBOM + policy set prerequisites.
3. **Progress breadcrumb** — after pipeline fetch:
   `Pipeline · Placement · Source · Details · Verify · Policy · Submit`
4. **Record answers** — running summary; do not re-ask unless the user changes direction.
5. **Fetch before configure** — `harness_get` before placement/source questions.
6. **Show pipeline structure** — list stages/steps; highlight `SscaOrchestration` and connectors.
7. **Infer source from orchestration** — when one SBOM generation step exists, reuse its `source` and image.
8. **Never guess image tags** — default to orchestration step image; ask if ambiguous.
9. **Confirm before write** — summary + `harness_update` only after user confirms.
10. **Stop after update** — after successful `harness_update`, provide a configuration summary and
    point the user to `/run-pipeline` to execute. Do **not** call `harness_execute`, poll
    executions, or run `harness_diagnose` in this skill (same pattern as `/configure-repo-scan`).
11. **CD placement without an existing Deploy stage** — if the user chooses CD enforcement (`cd_before_deploy`, `add_cd_stage`, or similar) on a CI-only pipeline, **do not** reject or force CI-only. Run **Phase 3b** to add a `Deployment` stage with a containerized step group and `CdSscaEnforcement` before deploy (same prerequisites as `/create-sbom`).
12. **Never block CD on “no Deployment stage”** — warn in Phase 2, then proceed via Phase 3b when the user wants CD.

Full phase prompts: `references/interactive-wizard-flow.md`.

---

## Instructions

### Wizard phases (user-facing)

| Phase | Breadcrumb | Action |
|-------|------------|--------|
| 0 | Pipeline | AskQuestion: pipeline URL ready? |
| 1 | Pipeline | Collect URL or org/project/id → `harness_get` |
| 2 | Pipeline | Display structure; note missing `SscaOrchestration` |
| 3 | Placement | AskQuestion: after SBOM step, CD before deploy, add CD stage, etc. |
| 3b | Placement (CD only) | If no `Deployment` stage: service, environment, infra, `stepGroupInfra` — then add stage + `CdSscaEnforcement` |
| 4 | Source | AskQuestion: infer from pipeline or pick tile |
| 5 | Source | AskQuestion: registry provider (Third-Party only) |
| 6 | Details | Connector (skip if obvious) |
| 7 | Details | Image / repo (free text; default from orchestration) |
| 8 | Verify | AskQuestion: verify attestation method |
| 9 | Policy | AskQuestion: policy set(s) — `harness_list` `policy_set` |
| 10 | Submit | AskQuestion: confirm pipeline update |

After Phase 10 `confirm` → insert step, `harness_update`, then provide summary (do not run the pipeline).

### Supported stage types

| Stage type (YAML) | Step `type` | Placement notes |
|-------------------|-------------|-----------------|
| `CI` | `SscaEnforcement` | **After** `SscaOrchestration` in the same stage |
| `Deployment` | `CdSscaEnforcement` | Containerized step group; **before** deploy |
| `Security` | `SscaEnforcement` | After SBOM generation when artifact is known |

### CD edge case (mandatory workflow)

Use when Placement targets **CD** (`cd_before_deploy`, `add_cd_stage`, or an existing `Deployment` stage).

#### Phase 2 — CI-only pipeline

If there is **no** `type: Deployment` stage, note it in the structure table and add:

> This pipeline has no CD Deploy stage yet. You can still enforce SBOM in CD — we will add a **Deployment** stage with a **containerized step group** and place **SBOM Policy Enforcement** before the deploy step.

**Do not** tell the user CD is invalid for this pipeline. If they chose CD in Phase 3, continue to Phase 3b.

#### Phase 3b — CD prerequisites (no Deploy stage yet)

Mirror `/create-sbom` Phase 3b — **one topic per turn**:

| Step | Action |
|------|--------|
| Service | `harness_list` (`service`) → `serviceRef` |
| Environment | `harness_list` (`environment`) → `environmentRef` |
| Infrastructure | `harness_list` (`infrastructure`, `params: { environment_id }`); create if missing per `/create-infrastructure` |
| Step group infra | K8s connector + namespace for `stepGroupInfra` |
| Deploy step | Default `K8sRollingDeploy` for Kubernetes services |
| CI enforcement | Optional: keep CI `SscaEnforcement` **and** add CD `enforce_sbom_cd`, or CD-only — confirm in Phase 10 |

Append a Deploy stage with containerized group containing `CdSscaEnforcement` **before** `K8sRollingDeploy`. Full YAML patterns: `skills/create-sbom/references/cd-containerized-step-group.md` (use `CdSscaEnforcement` instead of `SscaOrchestration`).

**CD image / source:** prefer `<+artifact.image>` from the service primary artifact; reuse connector from CI `SscaOrchestration` or service artifact source. **Verify attestation** must match the CI generation step (e.g. keyless Harness OIDC).

**Step id:** use `enforce_sbom_cd` when CI already has `enforce_sbom`.

### After the wizard — backend steps

#### Check prerequisites

1. **SBOM generation** — pipeline YAML contains `SscaOrchestration` (or user confirms SBOM was ingested).
2. **Policy sets** — `harness_list(resource_type="policy_set", org_id, project_id)`. If empty, direct user to `/create-policy` (SBOM entity, `onstep` event) before continuing.

#### Extract context from pipeline YAML

From `SscaOrchestration` (if present), copy:

- `spec.source` (type + spec)
- `spec.attestation` (use matching `verifyAttestation` when user chooses verify)
- `connector` / `image` / `registry`

From build/push steps: `connectorRef` in `BuildAndPushDockerRegistry`, `Run`, `Plugin`.

#### Generate SBOM enforcement step YAML

Use **only wizard answers**. Default: verify SBOM + keyless Harness OIDC + policy sets from Phase 9.

**CI / Security — `SscaEnforcement` (Third-Party Docker):**

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

**Policy sets only** (UI Policy Configuration):

```yaml
      policy:
        policySets:
          - sbom_license_allowlist
          - sbom_deny_critical
```

**No verification** (when user unchecks Verify SBOM):

```yaml
      policy:
        policySets:
          - <sbom_policy_set_identifier>
```

Omit `verifyAttestation`.

**Repository source** — add `overrideConnectorRef` on `spec` (see reference doc).

**CD `Deployment`** — use `CdSscaEnforcement` inside a containerized `stepGroup` (`stepGroupInfra`);
include `spec.infrastructure` matching that group (see `references/sbom-enforcement-step.md` and
`skills/create-sbom/references/cd-containerized-step-group.md`). When adding a new Deploy stage, place
enforcement in `stepGroup.steps` **before** the deploy step — not at top-level `execution.steps`.

Source types (`docker`, `ecr`, `gcr`, `gar`, `acr`, `har`, `repository`) match `/create-sbom` — see
`skills/create-sbom/references/sbom-orchestration-step.md` for provider-specific `source.spec` fields.

Full UI mapping: `references/sbom-enforcement-step.md`.

#### Insert step into pipeline YAML

- Insert at Phase 3 placement — **after** `generate_sbom` / `SscaOrchestration` when possible.
- Do not modify unrelated steps, variables, or failure strategies.
- Step identifier: `enforce_sbom` (rename if duplicate).
- **CI:** same `spec.execution.steps` list as orchestration.
- **CD:** inside the containerized step group only.

#### Update pipeline via MCP

```
harness_update
  resource_type: pipeline
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  body: { yamlPipeline: "<updated pipeline YAML>" }
```

On validation errors, read the API message, fix fields (often `verifyAttestation` shape or `policy.policySets`), retry.

#### Provide summary

Report the results to the user (same pattern as `/configure-repo-scan` — do **not** execute the pipeline):

```
## SBOM Policy Enforcement Configured

**Pipeline:** <pipeline_name>
**Step:** SBOM Policy Enforcement (SscaEnforcement | CdSscaEnforcement)
**Location:** Stage "<stage_name>", <position>
**Source:** <type> — <connector/registry> — <image or repo>
**Verify attestation:** Keyless (Harness OIDC) — or as configured
**Policy sets:** <list>

**Pipeline URL:** https://app.harness.io/ng/account/<account_id>/module/ci/orgs/<org_id>/projects/<project_id>/pipelines/<pipeline_id>/pipeline-studio/

**Note:** Review the SBOM Policy Enforcement step in Pipeline Studio to adjust Advanced settings.

### Next Steps
1. Run the pipeline via `/run-pipeline` to verify enforcement executes successfully
2. If the run fails, diagnose with `/debug-pipeline`
3. View policy evaluation on the execution **Supply Chain** tab and Artifacts → **Policy Violations**
4. If **Failed** due to policy deny, tune policies via `/create-policy` (entity-sbom.md)
5. Add or adjust SBOM generation with `/create-sbom` if SBOM was missing
6. Automate with `/create-trigger`
```

**CD pipelines:** note in the summary if runtime inputs (service artifact, environment, infrastructure)
will be required at run time — the user provides those via `/run-pipeline` or Harness UI Run.

---

## Examples

### Enforce after existing SBOM step

```
/enforce-sbom
Add SBOM policy enforcement to backend-api pipeline after Generate SBOM — keyless verify, policy set sbom_prod_rules
```

### CD pipeline before deploy

```
/enforce-sbom
Enforce SBOM policies in deploy stage before K8s rolling deploy for myapp:v7
```

### Defaults

```
/enforce-sbom
Use defaults — same image as SBOM orchestration step, Harness OIDC verify
```

---

## Performance Notes

- Only **existing pipelines** — do not offer to create new pipelines (you may **append** a Deploy stage to an existing pipeline).
- **Wizard UX is mandatory** — one question per turn; see `references/interactive-wizard-flow.md`.
- **CI-only + CD enforcement:** allowed — Phase 3b adds Deploy stage + containerized group; do not redirect to CI unless the user chooses CI placement.
- Reuse `SscaOrchestration` `source` + image when present — avoids drift from generation step.
- List `policy_set` via MCP before Phase 9 — do not invent policy set identifiers.
- Enforcement **after** SBOM exists; orchestration and enforcement run **sequentially**.
- CD: `CdSscaEnforcement` only in **containerized** step groups.
- **Do not execute pipelines** in this skill — use `/run-pipeline` after configuration (same as `/configure-repo-scan`).
- Pair with `/create-sbom` (generate) and `/create-policy` (OPA rules).

---

## Troubleshooting

### No SBOM / Orchestration Step in Pipeline
- Add `/create-sbom` first, or ingest SBOM per Harness docs.
- Enforcement evaluates components from an existing SBOM for the artifact.

### No Policy Sets Found
- `harness_list(resource_type="policy_set")` at project/org/account scope.
- Create SBOM policies (`package sbom`) and a policy set with **onstep** via `/create-policy`.

### Policy Evaluation Failed (Deny)
- Review deny/allow lists in policy Rego (`skills/create-policy/references/entity-sbom.md`).
- Check execution **Supply Chain** → policy violations for component UUIDs.

### Attestation Verification Failed
- Verification method must match **SBOM Orchestration** attestation (keyless vs key-based).
- Keyless non-harness: configure OIDC connector for keyless signing (SCS → Manage → Configuration).
- Key-based: public key file secret must match the key pair used when SBOM was attested.

### Wrong Image / No SBOM for Artifact
- Use the same `source.spec.image` as `SscaOrchestration`.
- Symptom: policy passes but wrong artifact — image mismatch.

### CD Step Validation Errors
- `CdSscaEnforcement` requires `spec.infrastructure` and containerized execution.
- Place inside `stepGroup` with `stepGroupInfra` — not top-level `execution.steps` on a Deployment stage.
- See `skills/create-sbom/references/cd-containerized-step-group.md`.

### User Chose CD on CI-Only Pipeline
- Expected — run Phase 3b; do not re-ask Placement with only CI options unless the user changes direction.
- SBOM must still exist (from CI `SscaOrchestration` or ingestion); enforcement in CD uses the same artifact image/expression.

### Pipeline Update Validation Errors
- `DUPLICATE_IDENTIFIER` — rename `enforce_sbom`.
- Invalid `policy.policySets` — use policy set **identifiers**, not display names.
- `verifyAttestation` shape — align with upstream attestation; see reference doc.

### MCP Errors
- `CONNECTOR_NOT_FOUND` — verify connector in Project Settings.
- `ACCESS_DENIED` — PAT needs pipeline edit and policy read permissions.

### Pipeline Run Failed
- Use `/run-pipeline` to execute and `/debug-pipeline` to diagnose failures
- Missing runtime inputs: provide branch/tag or deploy inputs via `/run-pipeline` or Harness UI Run
- Policy deny fails the step — expected when components violate rules; report violations clearly
