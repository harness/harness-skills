---
name: enforce-slsa
description: >-
  Add an SLSA Verification (SlsaVerification) step to an existing Harness pipeline to verify SLSA
  provenance attestations and optionally enforce OPA policy sets on provenance data. Supports CI and
  CD (Deployment) including CI-only pipelines — append a Deploy stage via Phase 3b when verifying
  before deploy. Supports Docker, ECR, GCR, GAR, ACR, HAR, and Local artifacts. Only works with
  existing pipelines. Use when asked to verify SLSA, enforce SLSA policies, add SLSA verification
  step, validate SLSA attestation, or gate deploy on SLSA provenance.
  Trigger phrases: enforce SLSA, SLSA verification, verify SLSA, SLSA policy enforcement,
  SlsaVerification, verify SLSA attestation, add SLSA verify step.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Enforce SLSA

Add an **SLSA Verification** (`SlsaVerification`) step to an existing Harness pipeline. The step
verifies SLSA provenance attestations (when enabled) and optionally evaluates OPA policy sets against
provenance data.

This skill only works with **existing pipelines** — do not create standalone verification-only pipelines.

**Prerequisites:** SLSA provenance must already exist for the artifact (typically from a `provenance`
step via `/generate-slsa` — UI label SLSA Generation). Optional **policy sets** for provenance
enforcement (`/create-policy`, `harness_list` `policy_set`).

**Supported stages:** CI, CD (`Deployment`), and Security. CD requires a **containerized step group**.
Unlike SBOM enforcement, CI and CD both use **`SlsaVerification`** (no separate CD step type).

Guide the user through a **step-by-step interactive wizard** (same UX as `/generate-slsa`):

- Wizard: `references/interactive-wizard-flow.md`
- UI ↔ YAML: `references/slsa-verification-step.md`
- CD containerized step groups: `skills/generate-slsa/references/cd-containerized-step-group.md`

---

## Interaction model (mandatory)

1. **One question per turn** — use `AskQuestion` when available; otherwise numbered options with `(Recommended)`.
2. **Opening message** — add SLSA Verification; mention generation + optional policy prerequisites.
3. **Progress breadcrumb** — after pipeline fetch:
   `Pipeline · Placement · Source · Details · Verify · Policy · Submit · Run`
4. **Record answers** — running summary; do not re-ask unless the user changes direction.
5. **Fetch before configure** — `harness_get` before placement/source questions.
6. **Show pipeline structure** — highlight `provenance` (SLSA Generation) and connectors.
7. **Infer source from generation** — when one `provenance` step exists (or `identifier: slsageneration`), reuse its source (map `repo` → `image_path`, lowercase → PascalCase types).
8. **Never guess image tags** — default from generation step; ask if ambiguous.
9. **Confirm before write** — summary + `harness_update` only after user confirms.
10. **Auto-run after update** — `harness_execute` + monitor; do not ask the user to run manually.
11. **CD on CI-only pipeline** — do not reject CD verify; run Phase 3b to add Deploy stage + containerized group.
12. **Verify method must match generation** — keyless ↔ keyless, keybased ↔ public key from same key pair.

Full phase prompts: `references/interactive-wizard-flow.md`.

---

## Instructions

### Wizard phases

| Phase | Breadcrumb | Action |
|-------|------------|--------|
| 0 | Pipeline | AskQuestion: pipeline URL ready? |
| 1 | Pipeline | Collect URL → `harness_get` |
| 2 | Pipeline | Display structure; note missing `provenance` (SLSA Generation) step |
| 3 | Placement | AskQuestion: after generation, CD before deploy, etc. |
| 3b | Placement (CD) | Service, env, infra, step group if new Deploy stage |
| 4 | Source | Infer from generation or pick registry tile |
| 5 | Source | Registry provider (Third-Party only) |
| 6 | Details | Connector (skip if obvious) |
| 7 | Details | Image / image_path (default from generation) |
| 8 | Verify | AskQuestion: verify attestation method |
| 9 | Policy | AskQuestion: policy set(s) or skip |
| 10 | Submit | AskQuestion: confirm pipeline update |
| 11 | Run | Auto-trigger + monitor |

### Supported stage types

| Stage type | Step `type` | Placement notes |
|------------|-------------|-----------------|
| `CI` | `SlsaVerification` | **After** `provenance` / `slsageneration` in the same stage |
| `Deployment` | `SlsaVerification` | Containerized step group; **before** deploy |
| `Security` | `SlsaVerification` | After generation when artifact is in registry |

### CD edge case

If no `Deployment` stage and user chose CD verify:

> No CD Deploy stage yet. We can add a **Deployment** stage with a **containerized step group** and
> place **SLSA Verification** before deploy.

Run Phase 3b (service, environment, infrastructure, `stepGroupInfra`) — mirror `/generate-slsa` Phase 3b.
Use `skills/generate-slsa/references/cd-containerized-step-group.md` with `SlsaVerification`.

**CD auto-run:** skip when new Deploy stage needs service/env/infra inputs.

### After the wizard — backend steps

#### Check prerequisites

1. **SLSA generation** — pipeline contains `type: provenance` (SLSA Generation) or user confirms provenance exists.
2. **Policy sets** (optional) — `harness_list(resource_type="policy_set")`. If user wants policy
   enforcement and none exist, direct to `/create-policy` before continuing.

#### Extract context from pipeline YAML

From `provenance` step (if present — also match `identifier: slsageneration`), copy and transform:

| Generation | Verification |
|------------|--------------|
| `source.type: docker` | `source.type: Docker` |
| `source.spec.repo` | `source.spec.image_path` |
| `source.spec.connector` | `source.spec.connector` |
| `spec.attestation` | matching `verify_attestation` (private → public key for keybased) |

#### Generate SLSA verification step YAML

**CI / Security — Docker Registry, keyless verify:**

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
    timeout: 15m
```

**Key-based verify** (generation used `keybased` + private key):

```yaml
      verify_attestation:
        type: keybased
        spec:
          publicKey: account.cosign_public_key
```

If API validation rejects flat `keyless` / `keybased`, retry with nested `cosign` wrapper — see
`references/slsa-verification-step.md`.

**Policy enforcement** (Advanced tab — step-level `enforce`):

```yaml
    enforce:
      policySets:
        - slsa_provenance_rules
```

**No attestation verify** (policy-only): omit `verify_attestation`.

**CD Deploy** — same step type inside containerized `stepGroup`; use `<+artifact.image>` for
`image_path` when verifying service artifacts.

Full provider mapping: `references/slsa-verification-step.md`.

#### Insert step into pipeline YAML

- Insert at Phase 3 placement — **after** `slsageneration` when possible.
- Do not modify unrelated steps.
- Step identifier: `slsaverification` (use `slsaverification_cd` in CD when CI already has one).
- **CD:** inside containerized step group only.

#### Update pipeline via MCP

```
harness_update
  resource_type: pipeline
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  body: { yamlPipeline: "<updated pipeline YAML>" }
```

On validation errors, check PascalCase `source.type`, `image_path` vs `repo`, and `verify_attestation`
shape (prefer flat `keyless`; fallback nested `cosign`).

#### Auto-run pipeline

```
harness_execute
  resource_type: pipeline
  action: run
  resource_id: <pipeline_identifier>
  org_id: <organization>
  project_id: <project>
  inputs: <branch/tag if codebase pipeline>
```

Poll execution every 20–30s. On failure, `harness_diagnose`. Report verification outcome on Supply Chain tab.

#### Provide summary

```
## SLSA Verification Configured

**Pipeline:** <pipeline_name>
**Step:** SLSA Verification (SlsaVerification)
**Location:** Stage "<stage_name>", <position>
**Source:** Docker — <connector> — <image_path>
**Verify attestation:** Keyless (Harness OIDC) — or as configured
**Policy sets:** <list or none>

**Execution:** <id> — <Success | Failed | Running>
**Execution URL:** <openInHarness>

### Next Steps
1. If **Failed**, confirm verify method matches generation attestation; check public key for keybased
2. Tune policies via `/create-policy`
3. Add generation with `/generate-slsa` if provenance was missing
4. Automate with `/create-trigger`
```

---

## Examples

### Verify after SLSA Generation

```
/enforce-slsa
Add SLSA verification after slsa-generation — keyless verify, policy set slsa_prod_rules
```

### CD before deploy

```
/enforce-slsa
Verify SLSA in deploy stage before K8s rolling deploy for easy-buggy-app:blog
```

### Key-based verify (matches keybased generation)

```
/enforce-slsa
Verify SLSA with public key account.cosign_public_key — same image as generation step
```

---

## Performance Notes

- Only **existing pipelines** (may append Deploy stage).
- **Wizard UX mandatory** — one question per turn.
- **Reuse generation source** — scan for `type: provenance` or `identifier: slsageneration`; map `repo` → `image_path`, lowercase → PascalCase types.
- **Verification `source.type` is PascalCase** (`Docker`) — generation uses lowercase (`docker`).
- **`verify_attestation`** is snake_case (not `verifyAttestation`). Prefer flat `type: keyless` + `oidcProvider` (same shape as generation `attestation`).
- Policy sets on step **`enforce.policySets`** — not `spec.policy` like SBOM enforcement.
- List `policy_set` via MCP — do not invent identifiers.
- **CD:** containerized step group only; see `skills/generate-slsa/references/cd-containerized-step-group.md`.
- Pair with `/generate-slsa` (generate) and `/create-policy` (OPA rules).

---

## Troubleshooting

### No SLSA Generation Step
- Add `/generate-slsa` first with attestation enabled (`type: provenance` in YAML).
- Verification needs `.att` in registry or provenance in SCS Artifacts.
- Scan for `provenance` steps — not `SlsaGeneration` (API uses `provenance`).

### Attestation Verification Failed
- Verify method must match generation (`keyless` vs `keybased`).
- Keybased: use **public** key secret (generation uses **private** key).
- Keyless non-harness: configure Connector for Keyless Signing.

### Wrong Image / No Provenance
- Use same `image_path` as generation `repo` field.
- Symptom: verify passes wrong artifact — image mismatch.

### Policy Evaluation Failed
- Review policy set Rego rules; check Supply Chain tab for violations.
- Confirm policy set identifier (not display name) in `enforce.policySets`.

### YAML Validation Errors
- `source.type` must be PascalCase for verification (`Docker`, not `docker`).
- Docker source uses `image_path`, not `repo`.
- `verify_attestation`: use flat `type: keyless` + `spec.oidcProvider: harness` — not nested `cosign` unless API rejects flat shape.
- `DUPLICATE_IDENTIFIER` — rename `slsaverification`.

### CD Step Errors
- Place inside `stepGroup` with `stepGroupInfra` — not top-level `execution.steps`.
- See `skills/generate-slsa/references/cd-containerized-step-group.md`.

### User Chose CD on CI-Only Pipeline
- Expected — run Phase 3b; do not force CI-only unless user changes direction.

### MCP Errors
- `CONNECTOR_NOT_FOUND` — verify connector in Project Settings.
- `ACCESS_DENIED` — PAT needs pipeline edit and policy read permissions.
