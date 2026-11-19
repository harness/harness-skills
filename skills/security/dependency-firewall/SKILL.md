---
name: dependency-firewall
description: >-
  Check whether a package/version is safe to add, and diagnose an install or build failure
  caused by Harness Dependency Firewall (artifact_scan_v3 / firewall_exception_v3), for any
  package type. Covers listing registries/packages/versions, CVE/license/policy checks,
  fix-version suggestions, and firewall exception (waiver) lifecycle.
  Use when a user asks whether a package is safe to add ("can I use dayjs?"), or an install or
  build fails with a 403 on a Harness registry artifact — worth checking even if the error
  doesn't say "firewall". Also covers "no matching version", "blocked by policy", and "my waiver
  was approved but it still fails". Do NOT use for Docker pulls (firewall not enabled there) or
  generic registry auth errors. Trigger phrases: dependency firewall, is this package safe,
  package blocked by policy, firewall exception, waiver, 403 on install, fix version available.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  summary: Check package safety and diagnose Dependency Firewall blocks, fix versions, and waivers
license: Apache-2.0
compatibility: Requires Harness MCP v2 server (harness-mcp-v2)
---

# Dependency Firewall

Helps a developer get an answer before they hit a block, and a plain-language cause after they
do. This is Harness's own Dependency Firewall (`artifact_scan_v3` / `firewall_exception_v3`), not JFrog
curation — don't assume JFrog's exact mechanics apply here without checking.

You need the account, and which org/project/registry the package lives in — ask if not given.
Don't guess account scope just because a project-scoped lookup is more typing, and don't reuse a
registry or account from a prior conversation or a different environment.

## Instructions

### Recognizing a dependency-firewall block

A package fetch failing with a **403** is reason enough to suspect Dependency Firewall and check
— don't wait for the error message to literally say "firewall", "policy", or "blocked". 403
specifically (not 401, not a timeout, not a DNS/connection error, not a plain 404) is the
download-time enforcement point: the artifact exists and the registry recognizes the request, but
the policy engine refused to serve the bytes. That holds regardless of:

- **Who's asking** — a developer running `npm install`/`pip install`/`mvn` locally, or a CI
  pipeline step pulling the same dependency during a build.
- **What it looks like on the surface** — a raw `403 Forbidden`, an install tool's generic
  "request failed with status code 403" wrapper, or a build tool reporting "could not resolve
  dependency" where the underlying HTTP call (visible in verbose/debug output or the CI log) was a
  403. If you can't see the raw status code, ask for verbose/debug output or the raw log line
  rather than guessing from the high-level error alone.
- **Which package type** — npm, pip, Maven, etc. all go through the same registry + firewall
  enforcement path. Docker is the exception: Dependency Firewall is not enabled for Docker pulls,
  so a 403 there has a different cause — don't point a Docker-pull failure at this skill.

Once confirmed as a 403, pull the `artifact_scan_v3` record for that exact package + version +
registry rather than guessing from the error text, and get the real policy/CVE/license reason
before telling the developer anything. Don't say "it's probably the firewall" without pulling
that record.

A 403 is not automatically a firewall block — it's just the signal worth checking first. Also
possible: a registry-level permission/RBAC issue (the caller's token lacks access to that
registry), or an auth/credential problem on the registry itself. If the `artifact_scan_v3` record
shows no `BLOCKED` status for that package + version + registry, say so and point the
investigation at permissions/auth instead of insisting it must be the firewall.

### Listing registries, packages, and versions

Use `harness_list` / `harness_get` with these `resource_type`s. Run
`harness_describe(resource_type: "<type>")` first if a field name is unclear — don't guess one.

| Want | resource_type | Scope needed | Notes |
|---|---|---|---|
| List registries in a project | `registry` | account + org + project | Filters: `search`, `type` (`UPSTREAM`/`VIRTUAL`), `package_type` |
| List packages in a registry | `artifact` | account + org + project + `registry_id` | `search` filter |
| List versions of a package | `artifact_version` | account + org + project + `registry_id` + `artifact_id` | `search` filter |
| List files in a version | `artifact_file` | + `version` | |

A newer `registries-v3` toolset exposes the same data as `package`/`package_version`/
`package_file` (flatter v3 paths, project-scoped), but it's opt-in — fall back to the table above
if `harness_describe` shows it isn't enabled.

Dependency Firewall itself lives under a separate toolset, `registries-firewall`, with
`resource_type`s `artifact_scan_v3`, `firewall_exception_v3`, `firewall_exception_version_v3`, and
`bulk_scan_evaluation_v3`. This toolset is still rolling out — run `harness_describe()` first and
confirm it's listed before using any of these; if it isn't, say so rather than guessing at a
non-`_v3` fallback name (none exists). `artifact_scan_v3` defaults to project scope; pass
`resource_scope: "account"` with `filters: {scope: "descendants"}` to search across every org and
project at once.

### Path A1 — A specific package and version was named

For "is dayjs@1.11.13 safe?" style requests, resolve that exact pair, don't list versions:

1. Check its firewall scan status with `resource_type: "artifact_scan_v3"`. There's no exact
   `package_name`/`version` filter — use `harness_list` with `filters: {search_term: "<package
   name>", registry_ids: "<registry id>"}` and match the exact `version` client-side from the
   results, or `harness_get` if you already have the `scan_id`.
2. If no scan record exists yet, trigger one with `harness_execute(resource_type:
   "artifact_scan_v3", action: "evaluate", params: {version_id: "<artifact version id>"})` — this
   is async (`PENDING`/`PROCESSING`/`SUCCESS`/`FAILED`); poll `harness_get` on the resulting scan
   until it settles. Don't report "unknown" without running the check.
3. Report the status (`ALLOWED`/`BLOCKED`/`WARN`) with the policy/CVE/license detail if blocked or
   warned. If blocked or warned, also read that same scan's `fixVersionDetails`
   (`currentVersion`/`fixVersion`/`fixVersionAvailable`) — it comes back on the scan record
   itself, no extra lookup needed. Don't silently substitute a different version — say what's
   blocked, mention the `fixVersion` if one's available, and let the developer decide whether to
   switch to it, ask for a different alternative, or request a waiver (see the exceptions section
   below), rather than auto-picking one yourself.

### Path A2 — Only a package was named, no specific version

For "what's the latest version of dayjs I'm allowed to use?":

1. List available versions for the package, sorted newest first.
2. For the newest version, check its firewall scan status the same way as A1 — trigger a scan if
   none exists.
3. If `BLOCKED`: read the scan's policy/CVE/license detail, **and** its `fixVersionDetails`
   before stepping back manually. If `fixVersionAvailable` is true, that `fixVersion` is a
   direct, already-known answer — skip straight to checking it instead of walking down the
   version list one at a time. Only fall back to manually stepping to the next-newest version if
   `fixVersionAvailable` is false (or you run out of versions).
4. If `WARN`: surface the warning but treat it as usable — ask the developer whether to proceed,
   don't auto-reject it the way you would `BLOCKED`.
5. Report: the version you landed on, its approval status, the CVEs/license found (or "none
   found"), and offer to add it to the project's dependency manifest and install — don't do that
   step unprompted.

If every version is `BLOCKED` with no `fixVersionAvailable`, say so plainly and don't suggest an
unapproved one as a workaround.

### Path A3 — A whole dependency manifest, before a build/install

For "will this build pass firewall checks?", or proactively whenever you're about to add/modify
dependencies in bulk rather than one at a time:

1. Parse the project's dependency manifest into a flat list of exact package + version pairs.
   Prefer a lockfile's resolved versions over a manifest's ranges when one exists
   (`package-lock.json`/`yarn.lock`, pinned `requirements.txt`, a Maven effective-pom, etc.) — a
   range doesn't tell you which actual version would be installed.
2. There is currently **no MCP action to kick off a new bulk evaluation** —
   `bulk_scan_evaluation_v3` only supports `list`/`get` (for polling an evaluation that was
   started some other way, e.g. the REST API directly), and `artifact_scan_v3`'s only execute
   action, `evaluate`, re-evaluates one artifact at a time (`scanId` or `versionId`). So for a
   whole manifest via MCP today:
   - First `harness_list resource_type=artifact_scan_v3` (filtered by `registry_ids` and, if
     useful, `search_term`) to pick up any package+version pairs that already have a recent scan
     — don't re-trigger those.
   - For every remaining pair with no scan (or a stale one), resolve its artifact `version_id`
     (via `artifact_version`/`package_version`) and call `evaluate` for each — this is a loop of
     single-artifact calls, not a true bulk call, so expect it to be slow for a large manifest.
   - If the manifest is large enough that this loop is impractical, say so explicitly and suggest
     the direct `bulk-evaluate`/`bulk-evaluate-sync` REST endpoints as the faster path outside MCP,
     rather than silently looping hundreds of times.
3. For every result that's `BLOCKED` or `WARN`, read that scan's `fixVersionDetails` — it comes
   back directly in the same evaluation response, so don't separately list versions to hunt for a
   replacement.
   - If `fixVersionAvailable` is true: that `fixVersion` is the concrete suggested replacement.
   - If `fixVersionAvailable` is false: fall back to A2's step-back approach for that one package,
     or note that a waiver may be the only option.
4. Report every blocked/warned package together (package, current version, policy reason,
   suggested `fixVersion` if any), then propose the manifest edits (bump each affected dependency
   to its `fixVersion`) — list the proposed changes and ask before actually editing the file or
   re-running install.

### Path B — Diagnose a failed install

First figure out which failure mode this is — they have different causes on Harness:

| Symptom | What it means |
|---|---|
| Package manager says a version doesn't exist, but you can see it upstream | Possible index-time hiding — don't assume it's active, it depends on registry type, firewall mode, and what's deployed in this environment. Check directly: query `artifact_scan_v3` for that exact package + version + registry and see if it's `BLOCKED` or quarantined, then check whether the version still appears in the index/listing response. Missing from the index → index-time hiding is active. Still listed → the 403 below is the only enforcement. |
| `403` with "Artifact is blocked due to policy violations" (or similar), but the version *was* listed | Download-time block — always enforced, independent of any flag or environment. Pull the `artifact_scan_v3` record to get the policy name, category (Security/License/MaliciousPackage/PackageAge/OssRiskLevel) and matched rule. |
| `404`/network error, or the package/version genuinely doesn't exist upstream | Not a firewall block — check the upstream source directly. |

Then:

1. Pull the scan/audit record for the exact package + version + `registryId` (via
   `search_term`/`registry_ids` on `artifact_scan_v3`, matching the exact version from the
   results — not just the package, since different registries can have different outcomes for
   the same version).
2. Report the policy category and specific match (CVE ID, license name, age threshold, etc.) in
   plain language, with the registry/scan id as evidence.
3. Read that same scan's `fixVersionDetails` — if `fixVersionAvailable` is true, suggest the given
   `fixVersion` directly rather than manually searching for the next-newest `ALLOWED` version.
   Only fall back to listing and stepping through newer versions by hand if
   `fixVersionAvailable` is false, and mention that a waiver is the other option either way.

### Firewall exceptions (waivers)

A firewall exception (`resource_type: "firewall_exception_v3"`) lets a specific, already-blocked
package + version(s) through on one registry:

- **Required fields to create one**: `registryId` (the registry that blocked the artifact — not
  the developer's project in general), `packageName`, `businessJustification`. Optional:
  `versionList` (specific versions; empty/omitted means all versions of that package on that
  registry), `expireAfter` (days after approval until it auto-expires; omit for never-expires),
  `remediationPlan`.
- **Lifecycle**: created as `PENDING` → someone with approval rights runs the `approve` or
  `reject` action (`harness_execute`, with optional `notes`) → `APPROVED` or `REJECTED`. An
  approved exception can later become `EXPIRED` once its `expireAfter` window passes. Only a
  `PENDING` exception can be updated (`harness_update`); once `APPROVED`/`REJECTED` you create a
  new one instead of editing it.
- **Scoping — the important part**: an exception is keyed strictly by `registryId` +
  `packageName` + `version`, with no project → org → account ancestor-walk and no inheritance
  across registries.
  - A virtual registry is just a pointer to one or more upstream registries — it has no packages
    of its own. Every artifact pulled "from" a virtual registry actually came from one specific
    upstream behind it, and that upstream is where the artifact was evaluated and (if applicable)
    blocked — so that upstream's `registryId` is the one the exception must be raised against,
    never the virtual registry's. Before raising or looking up an exception, always identify
    which upstream actually served the artifact (the `BLOCKED` scan record's `registryId` tells
    you this directly) rather than assuming it's the virtual registry the developer is pulling
    from.
  - An "account-level" exception is just an exception on a registry that itself has no
    org/project (e.g. an account-wide upstream) — it is not a broader override that reaches into
    unrelated project-scoped registries.
  - When listing exceptions, pass `org_id`/`project_id` matching that registry's own scope.
    Calling list with only `account_identifier` does not return the full account-wide set — it
    silently returns only exceptions on registries that themselves have no org/project, omitting
    project-scoped ones entirely.
- `resource_type: "firewall_exception_version_v3"` lists the versions of a package available to pick
  from when authoring a new exception for it (needs `registry_id` + `package_name`).

To diagnose "approved but still fails":

1. Get the `BLOCKED` scan/403 for the artifact and read its `registryId`.
2. List `firewall_exception_v3` with `org_id`/`project_id` set to that registry's own scope.
3. Check: does an exception exist for that exact `registryId` + `packageName`? Is `status`
   `APPROVED` (not still `PENDING`)? Does the version fall in `versionList` (empty = all
   versions)?
4. If the exception is on a different `registryId` than the one that blocked (e.g. approved on a
   virtual registry, but the actual block happened on its upstream, or vice versa) — that's
   almost always the cause. Say so explicitly and point at the correct `registryId`.
5. Only if the `registryId` matches and the exception is genuinely `APPROVED` for that version,
   consider a stale/cached index response (Path B's index-hiding case) as the secondary
   possibility.

### Reporting back

Always state: the package + version, the verdict (allowed/blocked/warn/excepted), the concrete
evidence (policy name, CVE id, registryId, scan id, exception id), and the next action — not just
"it's blocked."

## Examples

### Example 1 — Specific package and version

User: *"Is dayjs@1.11.13 safe to use?"*

1. `harness_list resource_type=artifact_scan_v3` filtered by `search_term: "dayjs"` and
   `registry_ids`, then match the exact `version: "1.11.13"` from the results.
2. Status comes back `ALLOWED` → report it's safe to add, no further action.

### Example 2 — Blocked version with a fix available

User: *"Can I add lodash 4.17.4?"*

1. Scan status is `BLOCKED` (known prototype-pollution CVE), and the same scan record's
   `fixVersionDetails` shows `fixVersionAvailable: true`, `fixVersion: "4.17.21"`.
2. Report: lodash@4.17.4 is blocked for CVE-XXXX-XXXXX; version 4.17.21 has a fix available.
   Offer to check 4.17.21 or add it, but don't switch versions without asking.

### Example 3 — 403 during CI build

User: *"Our CI build just failed with a 403 pulling some npm package, can you check if it's the
firewall?"*

1. Confirm this is a 403 on the package fetch itself (not a login/auth 401) from the build log.
2. Pull the `artifact_scan_v3` record for the exact package + version + registry the CI step was
   resolving.
3. If `BLOCKED`: report the policy/CVE reason and `fixVersionDetails`. If no `BLOCKED` record
   exists for that exact triple: say this isn't a firewall block and point at registry
   permissions/auth instead.

### Example 4 — Approved waiver still failing

User: *"I got my exception approved for `left-pad@1.3.0` but install still 403s."*

1. Re-pull the `BLOCKED` scan to confirm the exact `registryId` that blocked it.
2. List `firewall_exception_v3` scoped to that same registry's org/project.
3. Find the exception was approved against the virtual registry's id, not the upstream that
   actually served the artifact. Explain the mismatch and point at the correct `registryId` to
   re-raise the exception against.

## Performance Notes

- There's no MCP bulk-create action today — list existing `artifact_scan_v3` records first and
  only call `evaluate` for the pairs that are actually missing or stale, instead of looping
  `evaluate` over every package in a large manifest unconditionally.
- `fixVersionDetails` comes back directly on the scan record — never issue a separate lookup for
  it, and never manually walk a version list when `fixVersionAvailable` is already `true`.
- A scan record often already carries its exemption status inline as `exemptionStatus`
  (`id`/`status`/`createdAt`/`expirationAt`) — check that before doing a separate
  `firewall_exception_v3` list, it's frequently a free shortcut.
- Listing firewall exceptions at account scope silently narrows to registries that have no
  org/project — always scope the list call to the blocking registry's own org/project to avoid
  missing project-scoped exceptions.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Reported "unknown" status for a package | No scan has been triggered yet for that exact package + version + registry. | Trigger an evaluation (single or bulk) and wait for/poll the result before reporting anything. |
| 403 on download but no `BLOCKED` artifact_scan_v3 record exists | Not a firewall block. | Point the investigation at registry-level permissions/RBAC or an auth/credential problem instead. |
| 403 on a Docker pull | Dependency Firewall is not enabled for Docker. | Don't diagnose this as a firewall block; look elsewhere. |
| "Approved but still fails" | The exception was raised against the wrong `registryId` — usually the virtual registry instead of the upstream that actually served the artifact. | Read the `registryId` off the `BLOCKED` scan record and re-raise or re-point the exception there. |
| Listing exceptions at account scope returns fewer than expected | Account-scoped listing only returns exceptions on registries with no org/project. | Re-list scoped to the blocking registry's own org/project. |
| Version listed in the package index but download still 403s | Download-time enforcement (the one always-active path) is blocking it even though index-time hiding isn't active here. | Pull the `artifact_scan_v3` record for that exact triple to confirm and get the policy reason. |
| Every version of a package is `BLOCKED` with no fix version | No approved alternative exists yet. | Say so plainly; don't suggest an unapproved version as a workaround — offer a waiver as the only path forward. |
