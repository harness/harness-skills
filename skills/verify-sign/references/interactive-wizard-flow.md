# Artifact Verification — Interactive Wizard

Use with `/verify-sign` **Interaction model**. Each phase = **one** `AskQuestion` (or one free-text
prompt) per assistant turn.

## Progress breadcrumb

`Pipeline · Placement · Source · Details · Verify · Submit · Run`

---

## Phase 0 — Pipeline readiness

**AskQuestion title:** `Verify Sign — pipeline`

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

- Existing `SscaArtifactSigning` / `SscaArtifactVerification` steps
- Stage types: `CI`, `Deployment`, `Security`
- Connectors and image from signing step
- If **multiple** `SscaArtifactSigning` steps, list each with identifier, image, and signing method

If **no** `SscaArtifactSigning` exists, warn that the artifact must be signed (`/sign-artifact`)
before verification can succeed. Note whether existing signing steps have `uploadSignature.upload: true`.

For **Deployment** stages, label step groups as **containerized** or **not**.

**CI-only + CD verify:** CD verification is supported — Phase 3b can add a Deploy stage.

---

## Phase 3 — Placement

**AskQuestion title:** `Placement`

| Option id | Label | Notes |
|-----------|--------|--------|
| `after_signing` | CI — right after Artifact Signing (Recommended) | Same stage as `artifactsigning` |
| `cd_before_deploy` | CD — before deploy in containerized group | Existing or new Deploy stage |
| `add_cd_stage` | Add new CD Deploy stage with verification before deploy | CI-only → Phase 3b |
| `ci_and_cd` | Keep CI verification and add CD verification | When both gates needed |
| `security_end` | Security stage — end | Pre-built registry images |

If `cd_before_deploy` / `add_cd_stage` with no Deploy stage → **Phase 3b**.

Full CD rules: `references/cd-containerized-step-group.md`.

---

## Phase 3b — CD prerequisites

One topic per turn: service → environment → infrastructure → step group K8s connector + namespace.

Append Deploy stage with containerized group containing `SscaArtifactVerification` before
`K8sRollingDeploy`.

---

## Phase 4 — Source

| Option id | Label |
|-----------|--------|
| `infer_from_signing` | Same source as Artifact Signing step (Recommended) |
| `third_party` | Pick Third-Party registry |
| `har` | Harness Artifact Registry (HAR) |
| `local` | Harness Local Stage |

Always include **HAR** when offering source tiles.

When inferring, copy signing `source` unchanged (same lowercase types and `image` field).

If **multiple** signing steps exist, **AskQuestion** which step to mirror:

| Option id | Label |
|-----------|--------|
| `<signing_step_identifier>` | `<step_name>` — `<image>` |

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

Skip if obvious from `SscaArtifactSigning` or build/push steps.

---

## Phase 7 — Image / artifact

Free text; default from signing step. **Never guess tags.**

For CD: offer `<+artifact.image>` expression.

---

## Phase 8 — Verify signature

**AskQuestion title:** `Verify signature`

| Option id | Label |
|-----------|--------|
| `verify_keyless_harness` | Verify — Keyless — Harness OIDC (Recommended when signing used keyless) |
| `verify_keybased` | Verify — Key-based (public key file secret) |
| `verify_vault` | Verify — Secret Manager (Vault public key path) |

If **keybased**, next turn: public key secret id (e.g. `account.cosign_public_key`).

If **vault**, next turn: Vault connector identifier + public key path in Vault.

**Must match** upstream signing method.

---

## Phase 9 — Submit

Summary + confirm `harness_update`.

---

## Phase 10 — Run

Auto `harness_execute` + monitor for CI-only changes. Skip CD auto-run when deploy inputs missing.

---

## Defaults shortcut

- Infer source from `SscaArtifactSigning`
- Verify keyless Harness OIDC (or public key if signing was keybased)
- Placement: after signing step
