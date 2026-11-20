---
name: dependency-firewall
description: >-
  Check whether a package/version is safe to add, and diagnose an install or build failure
  caused by Harness Dependency Firewall (artifact_scan / firewall_exception), for any package
  type. Covers listing registries/packages/versions, CVE/license/policy checks, fix-version
  suggestions, and firewall exception lifecycle.
  Use when a user asks whether a package is safe to add ("can I use dayjs?"), or an install or
  build fails with a 403 on a Harness registry artifact — worth checking even if the error
  doesn't say "firewall". Also covers "no matching version", "blocked by policy", and "my
  exception was approved but it still fails". Do NOT use for Docker pulls (firewall not enabled
  there) or generic registry auth errors. Not for STO/SCS security exemptions (a different
  resource, `security_exemption`) — this skill is scoped to registry artifact firewall
  exceptions only. Trigger phrases: dependency firewall, is this package safe, package blocked
  by policy, firewall exception, 403 on install, fix version available.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  summary: Check package safety and diagnose Dependency Firewall blocks, fix versions, and exceptions
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Dependency Firewall

Helps a developer get an answer *before* they hit a block, and a plain-language cause *after* they hit one. Three
entry points below — pick the one that matches what the developer asked.

You need: the account, which org/project the registry lives in, and which registry — ask if not given (don't
guess "account" scope just because a project-scoped lookup is more typing, and don't reuse a registry/account
from a prior conversation or a different environment).

If no Harness MCP server is connected, or the connected one doesn't expose `registries-firewall`
(`harness_describe(search_term: "firewall")` returns nothing), stop and tell the user rather than falling back
to raw REST calls or guessing — this skill requires MCP v2 per its `compatibility` field.

## Instructions

### Recognizing a dependency-firewall block

If a package fetch fails with a **403**, that is reason enough to suspect Dependency Firewall and check —
don't wait for the error message to literally say "firewall", "policy", or "blocked". 403 specifically (not
401, not a timeout, not a DNS/connection error, not a plain 404) is the download-time enforcement point: the
artifact exists and the registry recognizes the request, but the policy engine refused to serve the bytes.
That's true regardless of who's asking (a local install or a CI pipeline step) or which package type (npm,
pip, Maven, cargo, nuget, ruby, go, etc. all go through the same enforcement path). Docker is the exception:
Dependency Firewall is not enabled for Docker pulls, so a 403 there has a different cause — don't point a
Docker-pull failure at this skill, even though `artifact_scan`'s `package_types` filter does include `DOCKER`
(that's for registries that scan Docker images for other reasons, not pull-time firewall enforcement).

If you can't see the raw status code behind a package manager's wrapped error, ask for verbose/debug output or
the raw CI log line rather than guessing from the high-level error text alone.

Once you've confirmed it's a 403, treat it as the Path B flow below: pull the `artifact_scan` record for that
exact package+version+registry rather than guessing from the error text, and get the real policy/CVE/license
reason before telling the developer anything.

A 403 is **not** automatically a firewall block, though — it's just the signal worth checking first. Also
possible: a registry-level permission/RBAC issue, or an auth/credential problem on the registry itself. If the
`artifact_scan` record shows no `BLOCKED` status for that package+version+registry, say so and point the
investigation at permissions/auth instead of insisting it must be the firewall.

### Pin down the exact registry and its scope before checking or creating anything

Every `artifact_scan` and `firewall_exception` record lives at the **same scope as the registry it's attached
to** (account, org, or project) — there is no ancestor-walk, so querying at the wrong scope doesn't error, it
just silently returns an empty or unrelated result set.

1. **Resolve which registry actually served the artifact.** A virtual registry has no packages of its own —
   every artifact pulled "from" one really came from an upstream behind it, and that upstream is where it was
   scanned and (if applicable) blocked. A `BLOCKED` scan's own `registryId` tells you the real registry
   directly; don't assume it's the one the developer's client config (`.npmrc`, `pip.conf`, etc.) points at if
   that's a virtual registry. This same rule applies everywhere below a registryId is needed — Path A, B, and
   the firewall-exception lifecycle in Path C all key off the registry that actually served/scanned the
   artifact, never the virtual registry in front of it.
2. **Determine that registry's actual scope** (account vs org vs project) from its `path` field (format
   `account/org/project/registry`, with `org`/`project` segments absent for an account-level registry) — not
   from the `openInHarness` link, which can render an account-level URL shape for a registry that is genuinely
   project-scoped.
3. Use that resolved scope (and matching `org_id`/`project_id` if project/org-scoped) for every subsequent
   `artifact_scan` or `firewall_exception` call on that registry.
4. **Every `registryId` you pass in a filter or a create/evaluate body must be the registry's `uuid` field**
   (or the `registryId` already present on a scan record) — never the slug/identifier used in `registry get`
   or in the developer's client config. Passing the slug doesn't error; it just matches nothing.

### Listing registries, packages, and versions

Use the connected Harness MCP server's generic tools (`harness_list`/`harness_get`) with these
`resource_type`s. Run `harness_describe(resource_type: "<type>")` first if a field name is unclear, and to
confirm what this specific environment's server actually supports before relying on anything below —
`registries-firewall` toolset availability and the `registry` type's scope support are both known to vary by
deployed MCP server/version, not just by account configuration.

**Filter keys fail silently, not loudly.** A wrong/guessed filter key does not error — the API ignores the
unknown key and returns an unfiltered or differently-scoped page of results, which can look like a plausible
answer when it has nothing to do with what you asked about. Always confirm exact filter field names via
`harness_describe(resource_type: "<type>")` first, and sanity-check that returned items actually match the
registry/package/version you intended.

| Want | resource_type | Scope needed | Filters |
|---|---|---|---|
| List registries | `registry` | Project-scoped everywhere (`get`/`create`/`update`). `list` additionally supports `resource_scope: "account"`/`"org"`/`"project"` **only where the connected server's `registries-firewall`/multi-scope support is enabled** — check `harness_describe(resource_type: "registry")` for a `supportedScopes` field before assuming account/org scope works; if it's absent, this server only supports project scope and you must ask for org/project rather than passing `resource_scope: "account"`. | `search_term`, `type` (`UPSTREAM`/`VIRTUAL`), `package_type`, `sort_field`, `sort_order`, and (only where multi-scope is supported) `scope` (`none`/`ancestors`/`descendants`) to widen relative to `resource_scope` |
| List packages in a registry | `artifact` | project-scoped: account + org + project + `registry_id` | `search` |
| List versions of a package | `artifact_version` | project-scoped: + `artifact_id` | `search` |
| List files in a version | `artifact_file` | project-scoped: + `version` | — |

Don't guess a default `org_id`/`project_id`; if you don't know them, ask — omitting them doesn't fail loudly,
it silently searches the wrong scope.

A newer `registries-v3` toolset exposes the same data as `package`/`package_version`/`package_file` (flatter
v3 paths, project-scoped), but it's opt-in — don't assume it's available; fall back to `registry`/`artifact`/
`artifact_version` above if `harness_describe` shows it isn't enabled.

### Path A — "Is this safe to add?" (pre-install check)

This has three shapes depending on what the developer asked:

**A1. A specific package *and* version was named** ("is dayjs@1.11.13 safe?"). Resolve that exact one — don't
list versions or step back:
1. Run `artifact_scan`'s `evaluate_packages` action with `{ registryId, artifacts: [{ packageName, version }] }`
   — this is the synchronous "would this pass" check and works whether or not the package has ever been
   scanned/pulled before, so prefer it over listing scans first. (`harness_list` on `artifact_scan` only
   surfaces past `BLOCKED`/`WARN` pulls — absence of a record there is not proof of safety.)
2. Report the resulting `scanStatus` (`ALLOWED`/`BLOCKED`/`WARN`) with the policy/CVE/license detail
   (`policySetFailureDetails`) if blocked or warned, and that same response's `fixVersionDetails`
   (`currentVersion`/`fixVersion`/`fixVersionAvailable`) if one exists. Don't silently substitute a different
   version — say what's blocked, mention the `fixVersion` if available, and let the developer decide whether to
   switch, ask for an alternative, or request an exception (Path C).

**A2. Only a package was named, no specific version** ("what's the latest version of dayjs I'm allowed to
use?"):
1. List available versions for the package (table above, or the package type's index/metadata response).
   Sort newest first.
2. Run `evaluate_packages` on the newest version.
3. If `BLOCKED`: read `fixVersionDetails`. If `fixVersionAvailable` is true, that `fixVersion` is a
   direct answer — evaluate it next instead of walking the version list by hand. Only step to the next-newest
   version manually if `fixVersionAvailable` is false (or you run out of versions).
4. If `WARN`: surface it but treat it as usable — ask the developer whether to proceed; don't auto-reject the
   way you would `BLOCKED`.
5. Report the version you landed on, its status, and the CVEs/license found (or "none found"). Offer to add it
   to the manifest + install — don't do that unprompted.

If every version is `BLOCKED` with no `fixVersionAvailable`, say so plainly and don't suggest an unapproved one
as a workaround.

**A3. A whole dependency manifest, before a build/install** ("will this build pass firewall checks?", or
proactively whenever you're about to add/modify dependencies in bulk):
1. Parse the manifest into exact package+version pairs. Prefer a lockfile's resolved versions over a
   manifest's ranges when one exists — a range doesn't tell you which version would actually install.
2. Evaluate in bulk, not one-by-one. Both actions take `{ registryId, artifacts: [{ packageName, version }] }`
   — the list field is `artifacts`, not `packages`:
   - **≤50 packages**: `evaluate_packages` — synchronous, one scan detail per artifact, nothing stored.
   - **51–10000**: `bulk_evaluate` — async, returns an `evaluationId`; poll `harness_get` on
     `bulk_scan_evaluation` with that id until `status` is `SUCCESS`/`FAILURE`, then read its `scans`
     (paginated, 100/page, non-`ALLOWED` by default).
3. For every `BLOCKED`/`WARN` result, read `fixVersionDetails` from that same response — don't separately list
   versions to hunt for a replacement when it's already there.
4. Report every blocked/warned package together (package, current version, policy reason, suggested
   `fixVersion` if any), then propose manifest edits bumping each to its `fixVersion`. Before presenting the
   final edit, re-run `evaluate_packages` on the proposed `fixVersion`s to confirm they're actually `ALLOWED` —
   a suggested fix version can itself be blocked for an unrelated reason (see Path B step 3). List the proposed
   changes and ask before editing the file or re-running install.

### Path B — Diagnose a failed install

First figure out which failure mode this is:

| Symptom | What it means on Harness |
|---|---|
| Package manager says a version/resolution doesn't exist, but it's visible upstream | Possibly index-time hiding — depends on registry type/mode/flag, don't assume. Check `artifact_scan` for that exact package+version+registry, and check whether the version still appears in the index/listing response. Missing from the index → hiding is active here. Still listed → the 403 below is the only enforcement. |
| `403` ("Artifact is blocked due to policy violations" or similar) on download, version *was* listed | Download-time block — always enforced, independent of any flag/environment. Pull the `artifact_scan` record for that registry/package/version for the policy category (`Security`/`License`/`MaliciousPackage`/`PackageAge`/`OssRiskLevel`) and matched rule. |
| `404`/network error, or the package/version genuinely doesn't exist upstream | Not a firewall block. Check the upstream source directly. |

Then:
1. Get the scan record for the exact package+version+registry: `harness_list` on `artifact_scan` filtered by
   `search_term` and `registry_ids` (not a package_name/version filter — list only returns past `BLOCKED`/`WARN`
   pulls, so if nothing comes back, run `evaluate_packages` instead to get a definitive answer), or
   `harness_get` directly if you already have the `scan_id`.
2. Report the policy category and specific match (CVE ID, license name, age threshold) in plain language, with
   the registry/scan id as evidence.
3. If `fixVersionDetails.fixVersionAvailable` is true, **don't apply it to the manifest unverified** — the
   suggestion can be stale or itself blocked for an unrelated CVE. Confirm the `fixVersion` is `ALLOWED` first
   (an existing scan record, or `evaluate_packages` on it directly) before editing any file or reporting it as
   the fix. Only fall back to stepping through newer versions by hand if `fixVersionAvailable` is false or the
   suggested version is also blocked — and mention a firewall exception (Path C) as the other option either way.

### Path C — How firewall exceptions work, and "my exception was approved but it still fails"

A firewall exception (`resource_type: "firewall_exception"`) lets a specific, already-blocked package+version(s)
through on one registry. This is a registry-artifact-firewall exception, distinct from an STO/SCS
`security_exemption` (pipeline scan-step waivers) — don't conflate the two or use one skill's resource for the
other's use case.

- **Create** needs `registryId` (the registry that actually blocked the artifact — see "Pin down the exact
  registry" above), `packageName`, `businessJustification`. Optional: `versionList` (empty/omitted = all
  versions), `expireAfter` (days after approval until auto-expiry; omit for never-expires), `remediationPlan`.
- **Update** only works while `status` is `PENDING`; once `APPROVED`/`REJECTED` create a new one instead.
- **Delete** removes an exception by `exception_id` regardless of status.
- **Approve/reject** (`harness_execute`, optional `notes`) moves a `PENDING` exception to `APPROVED`/`REJECTED`.
  An `APPROVED` exception can later become `EXPIRED` once `expireAfter` elapses.
- Before calling `create`, `update`, `approve`, `reject`, or `delete`, echo the full request back to the user
  (registryId, packageName, versions, justification, and for approve/reject which exception and decision) and
  get explicit confirmation first — these mutate state other developers rely on. Don't call them speculatively
  while just answering "is this safe" (Path A) or "why did this fail" (Path B).
- **Scoping**: keyed strictly by `registryId` + `packageName` + `version`, no ancestor-walk, no inheritance
  across registries. The same virtual-registry-vs-upstream distinction from "Pin down the exact registry"
  applies: raise the exception against the upstream that actually blocked the artifact, never the virtual
  registry the developer pulls from. When listing exceptions, pass `org_id`/`project_id` matching that
  registry's own scope — a list call scoped only to the account does not return project-scoped exceptions, it
  silently returns just the ones on registries that themselves have no org/project.
- `firewall_exception_version` lists the versions of a package available to pick from when authoring a new
  exception (needs `registry_id` + `package_name`).

To diagnose "approved but still fails":
1. Get the `BLOCKED` scan/403 for the artifact and read its `registryId`.
2. List `firewall_exception` with `org_id`/`project_id` set to that registry's own scope.
3. Check: exception exists for that exact `registryId` + `packageName`? `status` is `APPROVED` (not still
   `PENDING`)? Version falls in `versionList` (empty = all)?
4. If the exception is on a *different* `registryId` than the one that actually blocked (e.g. approved on a
   virtual registry, but the block happened on its upstream) — that's almost always the cause. Say so and point
   at the correct `registryId`.
5. If the registryId matches and the exception is genuinely `APPROVED` for that version, re-run `evaluate` on
   the blocking scan (`{ scanId }`) to refresh its status — a stale/cached scan result is the secondary
   possibility once scope is ruled out.

### Reporting back

Always state: the package+version, the verdict (allowed/blocked/warn/excepted), the concrete evidence (policy
name, CVE id, registryId, scan id, exception id), and the next action — not just "it's blocked."

## Examples

**"Is dayjs@1.11.13 safe to add to this project's npm registry (registry uuid `reg-abc123`)?"**
→ `harness_execute(resource_type: "artifact_scan", action: "evaluate_packages", body: {registryId: "reg-abc123",
artifacts: [{packageName: "dayjs", version: "1.11.13"}]})` → response shows `scanStatus: "BLOCKED"`, category
`Security`, CVE-2023-XXXXX, `fixVersionDetails: {fixVersion: "1.11.14", fixVersionAvailable: true}` → report:
"1.11.13 is blocked for CVE-2023-XXXXX (Security policy). 1.11.14 fixes it — want me to check 1.11.14 and bump
the manifest?"

**"npm install is failing with a 403 on lodash@4.17.15"**
→ Confirm it's a 403 (Path B) → `harness_list(resource_type: "artifact_scan", filters: {search_term: "lodash",
registry_ids: ["reg-abc123"]})` → find the `BLOCKED` record, read `policySetFailureDetails` and
`fixVersionDetails` → verify the suggested fix version is itself `ALLOWED` via `evaluate_packages` before
recommending it.

**"Check my package-lock.json before I run npm install"**
→ Parse resolved versions from the lockfile → batch them into `evaluate_packages` (≤50) or `bulk_evaluate`
(>50) against the registry → report every `BLOCKED`/`WARN` package with its `fixVersion`, re-verify each
proposed `fixVersion` is `ALLOWED`, then propose the manifest diff and wait for confirmation before editing.

**"We raised an exception for left-pad on the virtual registry but it's still blocked"**
→ Pull the blocking scan's `registryId` → it's the upstream behind the virtual registry, not the virtual
registry itself → list `firewall_exception` scoped to the upstream's org/project → exception doesn't exist
there → explain the exception needs to be raised against the upstream's `registryId`, not the virtual
registry's, and offer to create it there (with confirmation).

## Performance Notes

- Prefer `evaluate_packages` (≤50 artifacts, synchronous) over looping one `evaluate_packages`/`evaluate` call
  per package — it's one round trip for the whole batch.
- For >50 packages use `bulk_evaluate` and poll `bulk_scan_evaluation`; don't split a large lockfile into
  dozens of sequential `evaluate_packages` calls under 50 each just to avoid the async flow.
- `artifact_scan` list only returns non-`ALLOWED` records — don't page through it hunting for a specific
  package's status; use `evaluate_packages`/`get` by `scan_id` instead.
- Don't re-list `registry`/`artifact`/`artifact_version` to re-resolve a `registry_id`/`artifact_id` you
  already have in this conversation; reuse it.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `registry` list with `resource_scope: "account"` errors or returns nothing useful | This server's deployed `registry` resource doesn't support multi-scope (no `supportedScopes` in `harness_describe`) | Ask for the exact org/project instead of guessing account scope |
| `artifact_scan`/`firewall_exception` lookups return empty even though you're sure the artifact/exception exists | Queried at the wrong scope (org/project not matching the registry's own scope), or filtered with a guessed key instead of the real one (`search_term`, `registry_ids`, not `package_name`/`registry_id`) | Re-check the registry's `path` for its real scope; confirm filter keys via `harness_describe` |
| Exception `APPROVED` but the artifact still 403s | Exception was raised on the wrong `registryId` (virtual registry instead of the upstream that blocked it), or the version isn't in `versionList` | Compare the exception's `registryId` to the blocking scan's `registryId`; re-raise on the correct one if they differ |
| `evaluate_packages`/`bulk_evaluate` rejects the body | Used `packages` instead of `artifacts` as the list field, or passed a registry slug instead of its `uuid` | Use `artifacts: [{packageName, version}]`; resolve the registry's `uuid` via `registry get` first |
| A `fixVersion` you recommended is also blocked | `fixVersionDetails` suggestions aren't guaranteed `ALLOWED` — they can be stale or blocked for an unrelated CVE | Always verify a suggested `fixVersion` with `evaluate_packages` before recommending or applying it |
| `registries-firewall` resource types (`artifact_scan`, `firewall_exception`, ...) aren't in `harness_describe`'s output at all | Connected MCP server/version doesn't expose this toolset | Stop and tell the user — don't fall back to raw REST or a different unrelated resource |
