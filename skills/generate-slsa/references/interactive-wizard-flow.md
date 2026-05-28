# SLSA Generation — Interactive Wizard

Use with `/generate-slsa` **Interaction model**. Each phase = **one** `AskQuestion` (or one free-text
prompt) per assistant turn.

## Progress breadcrumb

`Pipeline · Placement · Source · Details · Attestation · Submit · Run`

Highlight the active phase. Completed phases may be summarized in one line above the question.

---

## Phase 0 — Pipeline readiness

**AskQuestion title:** `Generate SLSA — pipeline`

| Option id | Label |
|-----------|--------|
| `has_url` | Yes, I have the pipeline ID/URL |
| `need_help` | Not yet — help me find it |

If `need_help`, use `harness_list` (resource_type: `pipeline`) after org/project are known.

---

## Phase 1 — Pipeline URL or identifiers

Ask in prose for pipeline URL or id (+ org/project). Then `harness_get(url=..., resource_type="pipeline")`.

---

## Phase 2 — Show pipeline structure (no question)

After fetch, print stages/steps. **Call out:**

- `BuildAndPushDockerRegistry`, `BuildAndPushECR`, Kaniko/`Run` push steps (SLSA placement targets)
- Existing `provenance` (SLSA Generation), `SscaOrchestration` steps
- Stage types: `CI`, `Deployment`, `Security`
- Registry connectors from build/push steps

**Recommend in prose:** SLSA Generation should run **immediately after** the step that completes
image build/push. If SBOM exists, place SLSA **after** SBOM in the same stage (sequential).

---

## Phase 3 — Placement (mandatory — never skip)

**AskQuestion title:** `Placement`

### Turn A — Stage

List every **CI**, **Deployment**, and **Security** stage. Note existing `provenance` (SLSA Generation) steps.

| Option id | Label |
|-----------|--------|
| `<stage_identifier>` | `<stage_name>` (type: CI \| Deployment \| Security) |
| `add_cd_stage` | Add a new CD Deploy stage (CI-only pipeline) |
| `other_pipeline` | Use a different pipeline |

### Turn B — Position within stage

| Option id | Label | Notes |
|-----------|--------|--------|
| `after_build_push` | After image build/push step (Recommended) | Pick step from Phase 2 list |
| `after_sbom` | After Generate SBOM / SscaOrchestration | When SBOM already in stage |
| `ci_end` | End of CI stage | |
| `cd_before_deploy` | CD — before deploy in containerized group | → `cd-containerized-step-group.md` |
| `cd_new_containerized_group` | CD — new containerized group before deploy | |
| `security_end` | Security stage — end | |

**Do not offer** CD top-level `execution.steps` for SLSA in Deploy stages — use step group rules.

If user picks `add_cd_stage` or CD path with no Deploy stage → **Phase 3b**.

---

## Phase 3b — CD prerequisites (CI-only → Deploy stage)

One topic per turn: service → environment → infrastructure → step group K8s connector + namespace →
deploy step type (`K8sRollingDeploy` default). See `cd-containerized-step-group.md`.

---

## Phase 4 — Source tile

**AskQuestion title:** `Source`

| Option id | Label |
|-----------|--------|
| `third_party` | Third-Party registry (Recommended for Docker Hub / ECR / GCR / GAR / ACR) |
| `har` | Harness Artifact Registry |
| `local` | Harness Local Stage (non-container artifacts: jar, war, helm, yaml) |

---

## Phase 5 — Registry provider (Third-Party only)

| Option id | Label |
|-----------|--------|
| `docker` | Docker Registry (Recommended) |
| `ecr` | Amazon ECR |
| `gcr` | Google GCR |
| `gar` | Google GAR |
| `acr` | Azure ACR |

---

## Phase 6 — Connector

**AskQuestion** unless obvious from build/push or prior SBOM step YAML.

Skip when pipeline already uses one Docker registry connector unambiguously.

---

## Phase 7 — Image / repo (+ optional digest)

Free text. **Never guess tags.**

| Source | Ask for |
|--------|---------|
| `docker` | Full image ref for `repo` — e.g. `lavakush07/easy-buggy-app:blog` |
| `ecr` / `gcr` / `gar` / `acr` | Provider-specific fields per `slsa-generation-step.md` |
| `har` | Registry id + image |
| `local` | Workspace path; auto vs manual artifact name/version |

**Optional follow-up (one turn):** use digest expression from prior build step?

| Option id | Label |
|-----------|--------|
| `tag_only` | Tag in repo field only (Recommended for Docker Registry) |
| `digest_expression` | Add digest expression from build/push output |

When `digest_expression`, ask which build step id to reference (default: last `BuildAndPush*` in stage).

---

## Phase 8 — Attestation

**AskQuestion title:** `Attest SLSA`

| Option id | Label |
|-----------|--------|
| `attest_keyless_harness` | Attest — Keyless — Harness OIDC (Recommended on Harness Cloud builds) |
| `attest_keybased` | Attest — Key-based (Cosign private key + password secrets) |
| `attest_vault` | Attest — Secret Manager (HashiCorp Vault) |
| `no_attest` | Generate provenance only — no attestation |

If **keybased**, ask in the **next turn** for private key secret id and password secret id (defaults
from reference: `account.cosign_private_key`, `account.cosign_password`). Verify secrets exist via
`harness_list` (resource_type: `secret`) or direct user to `/create-secret`.

If **keyless non-harness**, warn that account Connector for Keyless Signing must be configured.

---

## Phase 9 — Submit

Summary of pipeline, placement, source, image/repo, attestation. **AskQuestion:** confirm `harness_update`?

---

## Phase 10 — Run

Auto `harness_execute` + monitor when CI-only and inputs inferrable. Skip full CD auto-run when deploy
inputs missing (same rules as CI-only SBOM + SLSA updates).

---

## Defaults shortcut

When the user says **“use defaults”**:

- Third-Party · Docker Registry
- Connector from pipeline build/push step
- Attest SLSA · Keyless · Harness OIDC
- Placement: after build/push (still ask which step if multiple push steps)
- **Still ask** for image/repo in Phase 7
