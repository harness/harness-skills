# SLSA Verification — Interactive Wizard

Use with `/enforce-slsa` **Interaction model**. Each phase = **one** `AskQuestion` (or one free-text
prompt) per assistant turn.

## Progress breadcrumb

`Pipeline · Placement · Source · Details · Verify · Policy · Submit`

---

## Phase 0 — Pipeline readiness

**AskQuestion title:** `Enforce SLSA — pipeline`

| Option id | Label |
|-----------|--------|
| `has_url` | Yes, I have the pipeline ID/URL |
| `need_help` | Not yet — help me find it |

---

## Phase 1 — Pipeline URL

Ask in prose for pipeline URL or id (+ org/project). Then `harness_get`.

---

## Phase 2 — Show pipeline structure (no question)

Call out:

- Existing `provenance` (SLSA Generation) / `SlsaVerification` steps
- Stage types: `CI`, `Deployment`, `Security`
- Connectors and image from generation step

If **no** `provenance` step exists (also check `identifier: slsageneration`), warn that SLSA
provenance must exist (`/generate-slsa`) or be imported before verification can succeed.

For **Deployment** stages, label step groups as **containerized** or **not**.

**CI-only + CD verify:** note that CD verification is supported — Phase 3b can add a Deploy stage.

---

## Phase 3 — Placement

**AskQuestion title:** `Placement`

| Option id | Label | Notes |
|-----------|--------|--------|
| `after_slsa_gen` | CI — right after SLSA Generation (Recommended) | Same stage as `slsageneration` |
| `cd_before_deploy` | CD — before deploy in containerized group | Existing or new Deploy stage |
| `add_cd_stage` | Add new CD Deploy stage with verification before deploy | CI-only → Phase 3b |
| `ci_and_cd` | Keep CI verification and add CD verification | When both gates needed |
| `security_end` | Security stage — end | Pre-built registry images |

If `cd_before_deploy` / `add_cd_stage` with no Deploy stage → **Phase 3b**.

Full CD rules: `skills/generate-slsa/references/cd-containerized-step-group.md` — use `SlsaVerification`.

---

## Phase 3b — CD prerequisites

One topic per turn: service → environment → infrastructure → step group K8s connector + namespace.

Append Deploy stage with containerized group containing `SlsaVerification` before `K8sRollingDeploy`.

---

## Phase 4 — Source

| Option id | Label |
|-----------|--------|
| `infer_from_generation` | Same source as SLSA Generation step (Recommended) |
| `third_party` | Pick Third-Party registry |
| `har` | Harness Artifact Registry |
| `local` | Harness Local Stage |

When inferring, copy generation `source` and map:
- `docker` + `repo` → `Docker` + `image_path`
- Lowercase generation types → PascalCase verification types

---

## Phase 5 — Registry provider (Third-Party only)

| Option id | Label |
|-----------|--------|
| `docker` | Docker Registry |
| `ecr` | Amazon ECR |
| `gcr` | Google GCR |
| `gar` | Google GAR |
| `acr` | Azure ACR |

---

## Phase 6 — Connector

Skip if obvious from `provenance` / `slsageneration` or build/push steps.

---

## Phase 7 — Image / image_path

Free text; default from generation step. **Never guess tags.**

For CD: offer `<+artifact.image>` expression.

---

## Phase 8 — Verify attestation

**AskQuestion title:** `Verify SLSA attestation`

| Option id | Label |
|-----------|--------|
| `verify_keyless_harness` | Verify — Keyless — Harness OIDC (Recommended when generation used keyless) |
| `verify_keybased` | Verify — Key-based (public key file secret) |
| `verify_vault` | Verify — Secret Manager (Vault public key path) |
| `no_verify` | Skip attestation verification (policy-only) |

If **keybased**, next turn: public key secret id (e.g. `account.cosign_public_key`).

**Must match** upstream generation attestation method.

---

## Phase 9 — Policy sets

**AskQuestion title:** `Policy enforcement`

| Option id | Label |
|-----------|--------|
| `list_policy_sets` | Pick from existing policy sets (`harness_list`) |
| `skip_policy` | Verify attestation only — no policy sets |
| `create_policy_first` | No policy sets yet — direct to `/create-policy` |

When listing, show identifiers (not display names). Multi-select when UI supports it.

---

## Phase 10 — Submit

Summary + confirm `harness_update`.

On `confirm` → insert step, `harness_update`, then provide configuration summary.

**Do not** call `harness_execute` or monitor executions — direct the user to `/run-pipeline`.

---

## Defaults shortcut

- Infer source from `provenance` step (`identifier: slsageneration`)
- Verify keyless Harness OIDC (or keybased public key if generation was keybased)
- Placement: after generation step
- **Still confirm** policy sets or skip policy in Phase 9
