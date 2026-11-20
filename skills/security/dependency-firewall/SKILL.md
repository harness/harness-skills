---
name: dependency-firewall
description: >-
  Check whether a package/version is safe to add, and diagnose an install or build failure
  caused by Harness Dependency Firewall (artifact_scan / firewall_exception), for any package
  type. Covers listing registries/packages/versions, CVE/license/policy checks, fix-version
  suggestions, and firewall exception (waiver) lifecycle.
  Use when a user asks whether a package is safe to add ("can I use dayjs?"), or an install or
  build fails with a 403 on a Harness registry artifact — worth checking even if the error
  doesn't say "firewall". Also covers "no matching version", "blocked by policy", and "my waiver
  was approved but it still fails". Do NOT use for Docker pulls (firewall not enabled there) or
  generic registry auth errors. Trigger phrases: dependency firewall, is this package safe,
  package blocked by policy, firewall exception, waiver, 403 on install, fix version available.
metadata:
  author: Harness
  version: 2.2.0
  mcp-server: harness-mcp-server
  summary: Check package safety and diagnose Dependency Firewall blocks, fix versions, and waivers
license: Apache-2.0
compatibility: Requires a Harness MCP server connection exposing the registries-firewall toolset (artifact_scan, firewall_exception, bulk_scan_evaluation).
---

# Dependency Firewall

Helps a developer get an answer *before* they hit a block, and a plain-language cause *after* they hit one. Three
entry points below — pick the one that matches what the developer asked.

You need: the account, which org/project the registry lives in, and which registry — ask if not given (don't
guess "account" scope just because a project-scoped lookup is more typing, and don't reuse a registry/account
from a prior conversation or a different environment).

## Instructions

### Picking the right MCP server

More than one Harness MCP connection can be present in a session (e.g. `harness`, `harness-qa`,
`harness-qa-local`, `harness-docker`) — they point at different environments and don't all expose the same
toolsets. `artifact_scan`/`firewall_exception`/`bulk_scan_evaluation` live in the `registries-firewall`
toolset, which is **not guaranteed to be on every connected server**. If `harness_list`/`harness_describe`
for these resource types errors or comes back empty on one server, don't conclude the feature or data doesn't
exist — run `harness_describe(search_term: "firewall")` against the other connected MCP servers to find the
one that actually has `registries-firewall`, or ask the user which server/environment to use. Once you've
confirmed which server has the data (e.g. `pkg.qa0.harness.io` → the `harness-qa-local` connection), use that
one for every call in the investigation rather than mixing servers.

**Never fall back to raw `curl`/REST calls against the Harness gateway** (e.g. `/gateway/har/api/...`) to
work around an MCP lookup that failed or came back empty on the wrong server — that's almost always a sign
you're on the wrong MCP connection or using the wrong resource_scope, not that the data doesn't exist. Only
drop to REST if no connected MCP server exposes `registries-firewall` at all.

### Recognizing a dependency-firewall block

If a package fetch fails with a **403**, that is reason enough to suspect Dependency Firewall and check —
don't wait for the error message to literally say "firewall", "policy", or "blocked". 403 specifically (not
401, not a timeout, not a DNS/connection error, not a plain 404) is the download-time enforcement point: the
artifact exists and the registry recognizes the request, but the policy engine refused to serve the bytes.
That's true regardless of:

- **Who's asking** — a developer running `npm install`/`pip install`/`mvn` locally, or a CI pipeline step
  pulling the same dependency during a build. The firewall doesn't care who the caller is; a build failing on
  a 403 for some transitive dependency is just as likely to be a firewall block as a direct `npm install` is,
  and is worth checking the same way.
- **What it looks like on the surface** — a raw `403 Forbidden`, an install tool's generic "request failed
  with status code 403" wrapper, or a build tool reporting "could not resolve dependency" / "failed to
  download artifact" where the underlying HTTP call (visible in `-v`/verbose/debug output, or the CI log) was
  a 403. If you can't see the raw status code, ask for verbose/debug output or the raw CI log line rather than
  guessing from the high-level error alone.
- **Which package type** — npm, pip, Maven, cargo, nuget, ruby, go etc. all go through the same registry +
  firewall enforcement path; the symptom (a 403 specifically on the artifact fetch, not on auth/login) looks
  the same shape regardless of ecosystem. Docker is the exception: Dependency Firewall is not enabled for
  Docker pulls, so a 403 there has a different cause — don't point a Docker-pull failure at this skill.

Once you've confirmed it's a 403 specifically, treat it as the Path B flow below: pull the `artifact_scan`
record for that exact package+version+registry rather than guessing from the error text, and get the real
policy/CVE/license reason before telling the developer anything. Don't tell them "it's probably the firewall"
without pulling that record — confirm it.

A 403 is **not** automatically a firewall block, though — it's just the signal worth checking first. Also
possible: a registry-level permission/RBAC issue (the caller's token lacks access to that registry at all,
independent of any artifact), or an auth/credential problem on the registry itself. If the `artifact_scan`
record shows no `BLOCKED` status for that package+version+registry, say so and point the investigation at
permissions/auth instead of insisting it must be the firewall.

### Pin down the exact registry and its scope before checking or creating anything

Every `artifact_scan` and `firewall_exception` record lives at the **same scope as the registry it's
attached to** (account, org, or project) — there is no ancestor-walk, so querying at the wrong scope doesn't
error, it just silently returns an empty or unrelated result set (see the filter-key gotcha below). Before
doing any lookup:

1. **Resolve which registry actually served the artifact.** A virtual registry has no public packages of its own —
   every artifact pulled "from" one really came from an upstream behind it, and that upstream is where it was
   scanned and (if applicable) blocked. A `BLOCKED` scan's own `registryId` tells you the real registry directly; don't
   assume it's the one the developer's client config (`.npmrc`, `pip.conf`, etc.) points at if that's a
   virtual registry.
2. **Determine that registry's actual scope** (account vs org vs project) from its `path` field (format
   `account/org/project/registry`, with `org`/`project` segments absent for an account-level registry) —
   **not** from the `openInHarness` link. `openInHarness` can render an account-level URL shape for a
   registry that is genuinely project-scoped; it is not a reliable signal of scope and has caused a wrong
   account-vs-project call before. Always check `path`.
3. Use that resolved scope (and matching `org_id`/`project_id` if project/org-scoped) for every subsequent
   `artifact_scan` or `firewall_exception` list/get/create call on that registry. The same rule applies to
   exceptions: an exception is tied to one registry, so it must be raised against (and looked up at the scope
   of) the registry that actually served the artifact — the upstream, not the virtual registry in front of
   it, if that's what served it.

### Listing registries, packages, and versions

Use the `harness-mcp-server` generic tools (`harness_list`/`harness_get`) with these `resource_type`s. Run
`harness_describe(resource_type: "<type>")` first if a field name is unclear — don't guess one.

**Filter keys fail silently, not loudly.** Passing a wrong/guessed filter key (e.g. `registryId` instead of
the real `registry_ids`, or `packageName` instead of `search_term` for `artifact_scan`) does not error — the
API just ignores the unknown key and returns an unfiltered or differently-scoped page of results, which can
look like a plausible answer (e.g. a page of real `BLOCKED` scans) when it has nothing to do with the
package/registry you asked about. Always confirm exact filter field names via `harness_describe(resource_type:
"<type>")` before filtering, and sanity-check that returned items actually match the registry/package/version
you intended before trusting an empty *or* non-empty result.

| Want | resource_type | Scope needed | Notes |
|---|---|---|---|
| List registries | `registry` | Supports all three: `resource_scope: "account"`, `"org"` (+ `org_id`), or `"project"` (+ `org_id`+`project_id`). `get`/`create`/`update` remain project-scoped, keyed by the registry's slug. | Filters: `search_term`, `type` (`UPSTREAM`/`VIRTUAL`), `package_type`, `sort_field`, `sort_order`, and `scope` (`none`/`ancestors`/`descendants`) — `scope` widens the list *relative to* `resource_scope`: `ancestors` adds parent levels, `descendants` adds child orgs/projects. Combine `resource_scope: "account"` + `scope: "descendants"` + `search_term` to find a registry by name anywhere in the account without knowing its org/project first. |
| List packages in a registry | `artifact` | project-scoped only: account + org + project + `registry_id` | v1 term for package; `search` filter |
| List versions of a package | `artifact_version` | project-scoped only: account + org + project + `registry_id` + `artifact_id` | `search` filter |
| List files in a version | `artifact_file` | project-scoped only: + `version` | |

`registry` is the one resource type here with real multi-scope support — don't assume a registry must be
project-scoped, and don't guess that the error "does not support account scope" exists; `resource_scope: "account"`
is valid and is the right call when you don't yet know which org/project a registry lives in (pair it with
`scope: "descendants"` and `search_term`). `artifact`/`artifact_version`/`artifact_file` are always
project-scoped (they hang off a specific `registry_id`, which you resolve first via `registry` list/get) — for
these three, don't guess a default `org_id`/`project_id` and don't omit them expecting a tool-level default to
match; omitting them silently returns an empty result (wrong scope, not "not found"). If you don't know the
org/project yet, ask, or search the environment's known test org/project before concluding a registry doesn't
exist.

A newer `registries-v3` toolset exposes the same data as `package`/`package_version`/`package_file` (flatter
v3 paths, project-scoped), but it's opt-in — don't assume it's available; fall back to `registry`/`artifact`/
`artifact_version` above if a `harness_describe` lookup shows it isn't enabled.

If no MCP tool is connected, the equivalent is the package type's own index/metadata endpoint (e.g. an npm
packument) for versions, and the Harness v1 registry API (`GET .../registries`, `GET .../artifacts`, `GET
.../artifact/{name}/versions`) for registries/packages — resolve the exact base URL and path shape for the
environment you're in rather than assuming one from memory.

### Path A — "Is this safe to add?" (pre-install check)

This has two shapes depending on what the developer actually asked — check which one applies before starting:

**A1. A specific package *and* version was named** ("is dayjs@1.11.13 safe?", "can I use lodash 4.17.21?").
Don't list versions or step back — just resolve that exact one:
1. Check its firewall scan status with `resource_type: "artifact_scan"` (`harness_list` filtered by
   `package_name`/`version`/`registry_id`, or `harness_get`).
2. If no scan record exists yet (unscanned), trigger one (`harness_execute` evaluate, or
   `bulk_scan_evaluation` for several at once) and wait for/poll the result — don't report "unknown" without
   running the check.
3. Report the resulting status (`ALLOWED`/`BLOCKED`/`WARN`) with the policy/CVE/license detail if blocked or
   warned. If blocked or warned, also read that same scan's `fixVersionDetails`
   (`currentVersion`/`fixVersion`/`fixVersionAvailable`) — it comes back on the scan record itself, no extra
   lookup needed. Don't silently substitute a different version — say what's blocked, mention the `fixVersion`
   if one's available, and let the developer decide whether to switch to it, ask for a different alternative,
   or request a waiver (Path C), rather than auto-picking one yourself.

**A2. Only a package was named, no specific version** ("what's the latest version of dayjs I'm allowed to
use?", "can I add dayjs?"):
1. List available versions for the package (see table above, or the package type's index/metadata response).
   Sort newest first.
2. For the newest version, check its firewall scan status the same way as A1 — if no scan record exists,
   trigger one rather than skipping it.
3. If `BLOCKED`: read the scan's policy/CVE/license detail, **and** its `fixVersionDetails`
   (`currentVersion`/`fixVersion`/`fixVersionAvailable`) before stepping back manually — if
   `fixVersionAvailable` is true, that `fixVersion` is a direct, already-known answer and you can skip
   straight to checking it (step 2) instead of walking down the version list one at a time. Only fall back to
   manually stepping to the next-newest version and repeating step 2 if `fixVersionAvailable` is false (or run
   out of versions).
4. If `WARN`: surface the warning but treat it as usable — ask the developer whether to proceed, don't
   auto-reject it the way you would `BLOCKED`.
5. Report: the version you landed on, its approval status, the CVEs/license found (or "none found"), and
   offer to actually add it to the project's dependency manifest + install — don't do that step unprompted.

If every version is `BLOCKED` with no `fixVersionAvailable`, say so plainly and don't suggest an unapproved
one as a workaround.

**A3. A whole dependency manifest, before a build/install** ("will this build pass firewall checks?", "check
my package.json before I run install", or proactively whenever you're about to add/modify dependencies in
bulk rather than one at a time):
1. Parse the project's dependency manifest into a flat list of exact package+version pairs. Prefer a
   lockfile's resolved versions over a manifest's ranges when one exists (`package-lock.json`/`yarn.lock`,
   `requirements.txt` with pinned versions, a Maven `effective-pom`, etc.) — a range doesn't tell you which
   actual version would be installed.
2. Evaluate them in bulk against the firewall with `artifact_scan`'s execute actions, not one-by-one. Both
   actions take `{ registryId, artifacts: [{ packageName, version }, ...] }` — the list field is `artifacts`,
   not `packages` (a natural but wrong guess that the API rejects outright):
   - **≤50 packages**: `evaluate_packages` (`bulk-evaluate-sync`) — synchronous, returns one scan detail per
     artifact immediately, nothing is stored.
   - **>50, up to 10000**: `bulk_evaluate` (`bulk-evaluate`) — async, returns an `evaluationId`; poll
     `harness_get` on `resource_type: "bulk_scan_evaluation"` with that id until `status` is `SUCCESS` or
     `FAILURE`, then read its `scans` (paginated, 100/page, non-`ALLOWED` by default).
3. For every result that's `BLOCKED` or `WARN`, read that scan's `fixVersionDetails`
   (`currentVersion`/`fixVersion`/`fixVersionAvailable`) — it comes back directly in the same evaluation
   response, so don't separately list versions to hunt for a replacement when this is already available.
   - If `fixVersionAvailable` is true: that `fixVersion` is the concrete suggested replacement.
   - If `fixVersionAvailable` is false: fall back to A2's step-back approach for that one package, or note
     that a waiver (Path C) may be the only option.
4. Report every blocked/warned package together (package, current version, policy reason, suggested
   `fixVersion` if any), then propose the manifest edits (bump each affected dependency to its `fixVersion`
   in `package.json`/`requirements.txt`/etc.) — list the proposed changes and ask before actually editing the
   file or re-running install, same as any other path here.

### Path B — Diagnose a failed install

First figure out which failure mode this is — they have different causes on Harness:

| Symptom | What it means on Harness |
|---|---|
| Package manager says a version/resolution doesn't exist, but you can see it on the upstream source | Possible index-time hiding, but **don't assume it's active** — it depends on registry type, firewall mode, a feature flag, and what's deployed in this specific environment. Check directly: query `artifact_scan` for that exact package+version+registry and see if it's `BLOCKED` or quarantined, then check whether the version still appears in the index/listing response. Missing from the index → index-time hiding is active here right now. Still listed → the 403 below is the only enforcement for this combination. |
| `403` with `"Artifact is blocked due to policy violations"` (or similar) on download, but the version *was* listed | Download-time block — this is the one path that is **always** enforced, independent of any flag or environment. Pull the `artifact_scan` record for that registry/package/version to get the policy name, category (Security/License/MaliciousPackage/PackageAge/OssRiskLevel) and matched rule. |
| `404`/network error, or the package/version genuinely doesn't exist upstream | Not a firewall block — don't misdiagnose this as policy. Check the upstream source directly. |

Then:
1. Pull the scan/audit record for the exact `package_name` + `version` + `registryId` (not just the package —
   different registries can have different outcomes for the same version).
2. Report the policy category and specific match (CVE ID, license name, age threshold, etc.) in plain
   language, with the registry/scan id as evidence.
3. Read that same scan's `fixVersionDetails` — if `fixVersionAvailable` is true, that `fixVersion` is where to
   look next, but **don't apply it to the manifest unverified** — the suggestion can be stale or itself
   blocked for an unrelated CVE (seen in practice: a blocked version's `fixVersion` pointed at another version
   that was also `BLOCKED`, for a different CVE). Confirm the `fixVersion` itself is `ALLOWED` first — via an
   existing scan record, or by running `evaluate_packages` on it directly — before editing any file or
   reporting it as the fix. Only fall back to listing and stepping through newer versions by hand if
   `fixVersionAvailable` is false, or the suggested `fixVersion` also comes back blocked, and mention that a
   waiver (Path C) is the other option either way.

### Path C — How exceptions (waivers) work, and "my waiver was approved but it still fails"

A firewall exception (`resource_type: "firewall_exception"`) is a request to let a specific, already-blocked
package+version(s) through on one registry:

- **Required fields to create one**: `registryId` (the registry that blocked the artifact — not the
  developer's project in general), `packageName`, `businessJustification`. Optional: `versionList` (specific
  versions; empty/omitted means *all* versions of that package on that registry), `expireAfter` (days after
  approval until it auto-expires; omit for never-expires), `remediationPlan`.
- **Lifecycle**: created as `PENDING` → someone with approval rights runs the `approve` or `reject` action
  (`harness_execute`, with optional `notes`) → `APPROVED` or `REJECTED`. An approved exception can later become
  `EXPIRED` once its `expireAfter` window passes. Only a `PENDING` exception can be updated (`harness_update`);
  once it's `APPROVED`/`REJECTED` you create a new one instead of editing it.
- **Scoping — the important part**: an exception is keyed strictly by `registryId` + `packageName` + `version`,
  with **no project → org → account ancestor-walk and no inheritance across registries**. Concretely:
  - A virtual registry is just a pointer to one or more upstream registries — it has no public packages of its own.
    Every artifact pulled "from" a virtual registry actually came from one specific upstream behind it, and
    that upstream is where the artifact was evaluated and (if applicable) blocked — so that upstream's
    `registryId` is the one the exception must be raised against, never the virtual registry's. A common
    setup is a project-scoped virtual registry fronting a single shared, account-level upstream; every
    package pulled through that virtual registry is really coming from the account-level upstream, so the
    exception has to be raised at the account level, on that upstream's `registryId`. The confusing part: the
    developer only ever interacts with the virtual registry, so it's easy to assume the exception lives
    there — it doesn't. Before raising or looking up an exception, always identify which upstream actually
    served that artifact (the `BLOCKED` scan record's `registryId` tells you this directly) rather than
    assuming it's the virtual registry the developer is pulling from.
  - An "account-level" exception is just an exception on a registry that itself has no org/project (e.g. an
    account-wide upstream) — it is not a broader override that reaches into unrelated project-scoped
    registries.
  - When listing exceptions, pass `org_id`/`project_id` matching **that registry's own** scope. Calling list
    with only `account_identifier` does **not** return the full account-wide set — it silently returns only
    exceptions on registries that themselves have no org/project, omitting project-scoped ones entirely.
- `resource_type: "firewall_exception_version"` lists the versions of a package available to pick from when
  authoring a new exception for it (needs `registry_id` + `package_name`).

To diagnose "approved but still fails":
1. Get the `BLOCKED` scan/403 for the artifact and read its `registryId`.
2. List `firewall_exception` with `org_id`/`project_id` set to that registry's own scope (per the gotcha
   above).
3. Check: does an exception exist for that exact `registryId` + `packageName`? Is `status` `APPROVED` (not
   still `PENDING`)? Does the version fall in `versionList` (empty = all versions)?
4. If the exception is on a *different* registryId than the one that blocked (e.g. approved on a virtual
   registry, but the actual block happened on its upstream, or vice versa) — that's almost always the cause.
   Say so explicitly and point at the correct registryId to raise it against.
5. Only if the registryId matches and the exception is genuinely `APPROVED` for that version, consider a
   stale/cached index response (Path B's index-hiding case) as the secondary possibility.

### Reporting back

Always state: the package+version, the verdict (allowed/blocked/warn/excepted), the concrete evidence (policy
name, CVE id, registryId, scan id, exception id), and the next action — not just "it's blocked."
