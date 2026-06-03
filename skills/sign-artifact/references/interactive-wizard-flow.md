# Artifact Signing — Interactive Wizard

Use with `/sign-artifact` **Interaction model**. Each phase = **one** `AskQuestion` (or one free-text
prompt) per assistant turn.

## Progress breadcrumb

`Pipeline · Placement · Source · Details · Signing · Upload · Submit`

Highlight the active phase. Completed phases may be summarized in one line above the question.

---

## Phase 0 — Pipeline readiness

**AskQuestion title:** `Sign Artifact — pipeline`

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

- `BuildAndPushDockerRegistry`, `BuildAndPushECR`, `BuildAndPushGCR`, `BuildAndPushGAR`,
  `BuildAndPushACR`, Kaniko/`Run` push steps (signing placement targets)
- Existing `SscaArtifactSigning`, `SscaOrchestration`, `provenance` steps
- For each existing `SscaArtifactSigning`: note `uploadSignature.upload` — warn if `false` or block
  missing (Harness default = no registry upload; user may not see `.sig` in registry)
- Stage types: `CI`, `Deployment`, `Security`
- Registry connectors from build/push steps

**Recommend in prose:** Artifact Signing should run **immediately after** the step that completes
image build/push. If SBOM or SLSA steps exist, place signing **after** them (sequential).

**Warn:** Deploy-stage signing is **not supported** by Harness today — recommend CI stage.

---

## Phase 2b — Existing signing step (when `SscaArtifactSigning` found)

**AskQuestion title:** `Existing signing step`

| Option id | Label |
|-----------|--------|
| `update_existing` | Update existing step (e.g. enable `.sig` upload) |
| `add_second` | Add a second signing step for another image |
| `abort` | Stop — signing already configured |

If user reports **missing `.sig` in registry**, prefer `update_existing` and set
`uploadSignature.upload: true`.

---

## Phase 3 — Placement (mandatory — never skip)

**AskQuestion title:** `Placement`

### Turn A — Stage

List every **CI** and **Security** stage. Note existing `SscaArtifactSigning`. If only Deploy stages
exist, warn about Deploy limitation and offer CI stage append guidance.

| Option id | Label |
|-----------|--------|
| `<stage_identifier>` | `<stage_name>` (type: CI \| Security) |
| `other_pipeline` | Use a different pipeline |

Do **not** offer Deploy stage placement — unsupported for signing.

### Turn B — Position within stage

| Option id | Label | Notes |
|-----------|--------|--------|
| `after_build_push` | After image build/push step (Recommended) | Pick step from Phase 2 list |
| `after_sbom` | After Generate SBOM / SscaOrchestration | When SBOM in stage |
| `after_slsa` | After SLSA Generation (`provenance`) | When SLSA in stage |
| `ci_end` | End of CI stage | |
| `security_end` | Security stage — end | |

### Turn C — Anchor push step (when multiple build/push steps in stage)

List each build/push step from Phase 2 with connector + repo/image. User picks which step signing
follows. Required when stage has more than one push step.

---

## Phase 4 — Source tile

**AskQuestion title:** `Source`

| Option id | Label |
|-----------|--------|
| `third_party` | Third-Party registry (Recommended for Docker Hub / ECR / GCR / GAR / ACR) |
| `har` | Harness Artifact Registry (HAR) |
| `local` | Harness Local Stage (jar, war, helm, yaml, etc.) |

Always include **HAR** — supported in YAML even when UI screenshot shows only Third-Party + Local tiles.

---

## Phase 5 — Registry provider (Third-Party only)

| Option id | Label |
|-----------|--------|
| `docker` | Docker Registry (Recommended) |
| `ecr` | Amazon ECR |
| `gcr` | Google GCR |
| `gar` | Google GAR |
| `acr` | Azure ACR |

Skip when user chose `har` or `local`.

---

## Phase 6 — Connector

**AskQuestion** unless obvious from build/push or prior SBOM step YAML.

Skip when pipeline already uses one Docker registry connector unambiguously. HAR uses `registry` id — ask in Phase 7.

### Mandatory — list ALL connectors (never hand-pick 2–3)

Before `AskQuestion`, fetch every connector of the provider type. **Do not** call unfiltered
`harness_list(resource_type="connector")` and manually pick Docker entries — that misses connectors
and mixes Git/K8s/other types.

**Map Phase 5 provider → `filters.type`:**

| Provider | `filters.type` |
|----------|----------------|
| `docker` | `DockerRegistry` |
| `ecr` | `Aws` |
| `gcr` / `gar` | `Gcp` |
| `acr` | `Azure` |

**Query all scopes** (merge, dedupe by identifier):

```
# 1. Project scope (required)
harness_list(resource_type="connector", org_id=<org>, project_id=<project>,
  filters={type: "<ConnectorType>"}, size=100)

# 2. Org scope (connectors shared across projects in the org)
harness_list(resource_type="connector", org_id=<org>,
  filters={type: "<ConnectorType>"}, size=100)

# 3. Account scope (e.g. account.sscsplayacc)
harness_list(resource_type="connector",
  filters={type: "<ConnectorType>"}, size=100)
```

If `total` > `size`, paginate with `page: 0, 1, …` until all items are retrieved.

**Present every result** in `AskQuestion` — one option per connector:

| Option id | Label pattern |
|-----------|----------------|
| `<identifier>` | `<identifier>` — `<name>` (<scope>, status: SUCCESS \| FAILURE) |

Add a final option: `other` — I'll type an identifier (for connectors not returned by list).

**Wrong patterns (never use):**

- `params: { filterType: "DockerRegistry" }` — ignored by API
- `harness_search(query="docker registry")` — returns hundreds of unrelated hits
- Showing only connectors noticed in an unfiltered first page (default `size: 20`)

If pipeline YAML already has an unambiguous `connectorRef` from build/push, pre-select that connector
in the summary and skip `AskQuestion`.

---

## Phase 7 — Image / artifact details

Free text. **Never guess tags.**

| Source | Ask for |
|--------|---------|
| `docker` | Full image ref for `image` — e.g. `lavakush07/easy-buggy-app:v5` |
| `har` | HAR `registry` identifier + `image` name with tag or digest |
| `ecr` / `gcr` / `gar` / `acr` | Provider-specific fields per `artifact-signing-step.md` |
| `local` | Workspace path; auto vs manual artifact name/version |

**Optional follow-up (one turn):** use digest expression from prior build step?

| Option id | Label |
|-----------|--------|
| `tag_only` | Tag in image field only (Recommended for Docker Registry) |
| `digest_expression` | Add digest expression from build/push output |

---

## Phase 8 — Signing method

**AskQuestion title:** `Sign with`

| Option id | Label |
|-----------|--------|
| `sign_keyless_harness` | Sign — Keyless — Harness OIDC (Recommended on Harness Cloud) |
| `sign_keybased` | Sign — Key-based (Cosign private key + password secrets) |
| `sign_vault` | Sign — Secret Manager (HashiCorp Vault) |

If **keybased**, ask in the **next turn** for private key secret id and password secret id (defaults
from reference: `account.cosign_private_key`, `account.cosign_password`). Verify secrets exist via
`harness_list` (resource_type: `secret`) or direct user to `/create-secret`.

If **vault**, next turn: Vault connector identifier + transit key path
(e.g. `transit/signing-keys/cosign`).

If **keyless**, follow-up only when user needs non-Harness OIDC:

| Option id | Label |
|-----------|--------|
| `oidc_harness` | Harness OIDC (Recommended on Harness Cloud) |
| `oidc_non_harness` | Non-Harness OIDC — requires account Connector for Keyless Signing |

Non-Harness uses `oidcProvider: non-harness` — warn that SSCA account Connector for Keyless Signing
must be configured first.

---

## Phase 9 — Upload signature

**AskQuestion title:** `Attach signature`

Skip for **Harness Local Stage** (`local` source) — upload is container-only.

**Important:** Harness UI defaults this checkbox to **unchecked**. Without `uploadSignature.upload: true`,
signatures are stored in Harness only — **no `.sig` appears in the container registry**.

| Option id | Label |
|-----------|--------|
| `upload_yes` | Attach signature to Artifact Registry — upload `.sig` (Recommended for containers) |
| `upload_no` | Sign only — Harness DB only; no `.sig` pushed to registry |

Maps to `uploadSignature.upload: true/false`. When `upload_yes`, **always** include the block in YAML:

```yaml
uploadSignature:
  upload: true
```

---

## Phase 10 — Submit

Summary of pipeline, placement, source, image, signing, upload. **AskQuestion:** confirm `harness_update`?

On `confirm` → generate YAML, insert step, `harness_update`, then provide configuration summary.

**Do not** call `harness_execute` or monitor executions — direct the user to `/run-pipeline`.

After a successful run (via `/run-pipeline`), check signing step logs for signature push when upload
is enabled. Cosign may store signatures as `sha256-<digest>.sig` tags or OCI referrers — confirm on
Harness Supply Chain tab or use `/verify-sign`.

---

## Defaults shortcut

When the user says **“use defaults”**:

- Third-Party · Docker Registry
- Connector from pipeline build/push step
- Sign · Keyless · Harness OIDC
- Upload `.sig` · Yes
- Placement: after build/push (still ask which step if multiple push steps)
- **Still ask** for image in Phase 7
