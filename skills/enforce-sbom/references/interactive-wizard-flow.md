# SBOM Policy Enforcement — Interactive Wizard

Use with `/enforce-sbom` **Interaction model**. Each phase = **one** `AskQuestion` (or one free-text
prompt) per assistant turn.

## Progress breadcrumb

Show on every wizard turn after pipeline fetch:

`Pipeline · Placement · Source · Details · Verify · Policy · Submit · Run`

Highlight the active phase. Completed phases may be summarized in one line above the question.

---

## Phase 0 — Pipeline readiness

**AskQuestion title:** `Enforce SBOM — pipeline`

**Prompt:** Do you have the pipeline identifier or Harness UI URL ready?

| Option id | Label |
|-----------|--------|
| `has_url` | Yes, I have the pipeline ID/URL |
| `need_help` | Not yet — help me find it |

If `need_help`, use `harness_list` (resource_type: `pipeline`) after org/project are known.

---

## Phase 1 — Pipeline URL or identifiers

**Do not use AskQuestion** — ask in prose for pipeline URL or id (+ org/project).

Then `harness_get(url=..., resource_type="pipeline")`.

---

## Phase 2 — Show pipeline structure (no question)

After fetch, print stages/steps. **Call out:**

- Existing `SscaOrchestration` / `SscaEnforcement` steps
- Stage types: `CI`, `Deployment`, `Security`
- Connectors and **image** from orchestration step (reuse for enforcement)

If **no** `SscaOrchestration` exists, warn that SBOM must be generated or ingested first (`/create-sbom`).

For **Deployment** stages, label each `stepGroup` as **containerized** or **not** (`stepGroupInfra` present).

**CI-only pipeline (no `Deployment` stage):** after the structure table, add:

> No CD Deploy stage yet. You can still add **SBOM Policy Enforcement in CD** — we will create a Deploy stage with a containerized step group (Phase 3b).

Do **not** reject `cd_before_deploy` or `add_cd_stage` because the pipeline is CI-only today.

---

## Phase 3 — Placement

**AskQuestion title:** `Placement`

### Turn A — Where to enforce (always offer CD)

**Prompt:** Where should the SBOM Policy Enforcement step run?

| Option id | Label | Notes |
|-----------|--------|--------|
| `after_sbom` | CI — right after Generate SBOM / SscaOrchestration (Recommended when enforcing in CI) | `CI`, `Security` |
| `cd_before_deploy` | CD — before deployment in containerized group (Recommended for deploy-time gate) | Existing **or new** Deploy stage → Phase 3b if none |
| `add_cd_stage` | Add a new CD Deploy stage with enforcement before deploy | CI-only pipeline → Phase 3b |
| `after_step` | After a specific step (name in follow-up) | Named stage/step |
| `security_end` | Security stage — at the end | `Security` |
| `ci_and_cd` | Keep CI enforcement (optional) and add CD enforcement | When CI already has or will have enforcement |

If the user picks `cd_before_deploy` or `add_cd_stage` and Phase 2 showed **no** `Deployment` stage → **Phase 3b** before Turn B (or merge 3b into placement flow).

### Turn B — Position within CD stage (when CD path chosen)

Skip if Phase 3b will create the whole Deploy stage (default: new containerized group before deploy).

| Option id | Label |
|-----------|--------|
| `cd_containerized_end` | End of existing containerized step group |
| `cd_containerized_after_step` | After a step inside containerized group |
| `cd_new_containerized_group` | New containerized step group before deploy (Recommended when no group) |

Full CD rules: `skills/create-sbom/references/cd-containerized-step-group.md` — use `CdSscaEnforcement`.

**Recommendations:**

- **CI:** immediately after `generate_sbom` (`SscaOrchestration`).
- **CD:** inside `stepGroup.steps` with `stepGroupInfra`, before `K8sRollingDeploy`.
- **CI-only + CD:** `add_cd_stage` or `cd_before_deploy` → Phase 3b, then `cd_new_containerized_group`.

---

## Phase 3b — CD prerequisites (CI-only → new Deploy stage)

Run when the user chose **`add_cd_stage`**, **`cd_before_deploy`**, or CD placement but Phase 2 had **no**
`type: Deployment` stage. **One decision per turn** (same as `/create-sbom` Phase 3b):

| Turn | Topic |
|------|--------|
| 1 | **Service** — `harness_list` (`service`); match artifact to CI SBOM image when possible |
| 2 | **Environment** — `harness_list` (`environment`) |
| 3 | **Infrastructure** — `harness_list` (`infrastructure`, `params: { environment_id }`) |
| 4 | **Step group K8s** — connector + namespace for `stepGroupInfra` |
| 5 | **CI enforcement** — add `SscaEnforcement` in CI too, or CD-only (confirm in Phase 10) |

Record: `serviceRef`, `environmentRef`, infra identifier, `stepGroupInfra`, new stage id (e.g. `Deploy_Dev`).

Then continue to Phase 4. For CD source image, default **`<+artifact.image>`**; copy verify attestation from CI `SscaOrchestration`.

---

## Phase 4 — Source tile

**AskQuestion title:** `Source`

**Prompt:** Where is the artifact to enforce policies on? (match SBOM Orchestration source)

| Option id | Label | `source.type` |
|-----------|--------|----------------|
| `infer_from_pipeline` | Same as existing SBOM step in pipeline (Recommended) | (from YAML) |
| `third_party` | Third-Party Registry | `docker` / `ecr` / `gcr` / `gar` / `acr` |
| `har` | Harness Artifact Registry | `har` |
| `repository` | Repository | `repository` |

If `infer_from_pipeline` and exactly one `SscaOrchestration` exists, copy its `source` block.

---

## Phase 5 — Provider (Third-Party only)

Skip if source ≠ `third_party`.

Same options as `/create-sbom` Phase 6: `docker`, `ecr`, `gcr`, `gar`, `acr`.

---

## Phase 6 — Connector / registry

Skip if inferred from pipeline or HAR registry is obvious.

Offer connectors from pipeline YAML (`Use from pipeline: <id> (Recommended)`).

---

## Phase 7 — Image / repo details

**Do not use AskQuestion** unless offering branch choices.

| Source | Ask |
|--------|-----|
| Registry types | Image (`org/repo:tag` or digest) — **default:** same as `SscaOrchestration` |
| `repository` | Repo URL + branch/tag |
| `har` | Registry id + image |

Never guess tags if not in pipeline YAML.

---

## Phase 8 — Verify SBOM attestation

**AskQuestion title:** `Verify attestation`

**Prompt:** Should the step verify the SBOM attestation before applying policies?

| Option id | Label |
|-----------|--------|
| `keyless_harness` | Verify SBOM — Keyless with Harness OIDC (Recommended) |
| `keyless_non_harness` | Verify SBOM — Keyless with non-Harness OIDC |
| `keybased` | Verify SBOM — Key-based (public key file secret) |
| `secret_manager` | Verify SBOM — Secret Manager (Vault) |
| `none` | Do not verify attestation |

Default matches UI: **Verify SBOM** checked, **Keyless**, Harness OIDC.

If upstream SBOM step used a different attestation method, recommend matching it.

---

## Phase 9 — Policy sets

**AskQuestion title:** `Policy sets`

**Prompt:** Which SBOM policy set(s) should this step enforce?

1. `harness_list(resource_type="policy_set", org_id, project_id)` — build options from results.
2. If none, explain `/create-policy` (entity `sbom`, event `onstep`) and offer to continue after user creates one.

| Option id | Label |
|-----------|--------|
| `<policy_set_identifier>` | `<name>` (identifier) |
| `create_policy` | I need to create a policy set first |

Allow **multiple** selections when the tool supports `allow_multiple: true`.

---

## Phase 10 — Confirm

**AskQuestion title:** `Submit`

Summary: pipeline, stage, position, source, image/repo, verify method, policy set ids.

| Option id | Label |
|-----------|--------|
| `confirm` | Yes, update the pipeline |
| `cancel` | No, let me change something |

On `confirm` → insert step, `harness_update`.

---

## Phase 11 — Auto-run pipeline (mandatory)

**No AskQuestion** after successful update.

1. `harness_execute` — `action: run`, same org/project/pipeline id.
2. Derive `inputs` from wizard (branch/tag) — do not prompt user.
3. Poll execution; on failure use `harness_diagnose`.
4. Report policy pass/fail and link to **Supply Chain** / **Policy Violations** on execution.

Skip auto-run only if the user explicitly declined in the same session.

---

## Defaults shortcut

If the user says **"defaults"** after pipeline fetch:

- Placement: after `SscaOrchestration` in CI when a CI SBOM step exists; if user asked for CD or pipeline is CD-only, `cd_before_deploy` (create Deploy stage via 3b if missing)
- Source: infer from orchestration step
- Verify: keyless + Harness OIDC
- Policy: first SBOM-related `policy_set` from `harness_list` (or ask if ambiguous)

Still confirm policy set if multiple SBOM sets exist.
