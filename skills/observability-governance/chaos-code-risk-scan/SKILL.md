---
name: chaos-code-risk-scan
description: >-
  Scan a source code repository for resilience risks that a Harness chaos
  experiment can prove (outbound calls without timeouts, retries without
  backoff, missing graceful shutdown, health checks that mask dependency
  state, unbounded queues and pools, local state), map each one to a generic
  SourceCode risk rule, and report them to Harness as a CodeRepository risk
  scan. Use when the user asks to scan a repo or service code for resilience
  or chaos risks, or wants code findings they can verify with chaos
  experiments. Do not use for manifest or pipeline risk scans (those run in
  Harness), to create or run chaos experiments (use chaos-experiment), or for
  security or code quality review. Trigger phrases: scan this repo for
  resilience risks, chaos code scan, find chaos-provable risks, code risk
  scan, resilience review of this service.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp-v2
  module: CHAOS
  summary: Scan a code repository for chaos-provable resilience risks and report them as a risk scan
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 server (harness-mcp-v2) with chaos_risk_rule
  create/update and chaos_risk_scan submit_findings, Python 3.9 or later, and git
---

# Chaos Code Risk Scan

Find resilience risks in a repository that a chaos experiment can turn into a
pass/fail result, and send them to Harness as a `CodeRepository` risk scan.
Harness then scores them, adds them to the scan report and, for modules linked
to a chaos service, recommends experiments.

The work is split so evidence cannot be invented: scripts extract facts and
verify snippets; you only map verified facts to rules and write the
explanation; the server re-validates everything.

One prompt runs the whole flow. Do not ask the user to choose an org, project, module,
service, rule, or to approve a create or a submit. The only stops are a missing
`origin` remote, or a tool error that a single retry does not clear. Report those
at the end; do not pause the scan to ask how to proceed.

Pass `confirm: true` on every `harness_create` and on the attach update below.
If a write is blocked because no confirmation prompt could be shown, retry that
same call once with `confirm: true`. Do not attach a runtime discovered service
during the scan. After the summary, offer that attachment in one sentence and
stop. Ask for the discovered service and probes only after the user asks to attach.

MANDATORY — Tool Result Verification:
- NEVER claim a tool call succeeded without an explicit success response from the tool.
- NEVER fabricate, assume, or pre-empt tool results. If a call did not return a confirmed result, say so and retry.
- NEVER submit a finding that `validate_evidence.py` dropped, and never edit a snippet to make it pass.
- A confirmation card is not a reason to stop. Retry with `confirm: true`, then continue.

## Instructions

`SKILL_DIR` below is the directory containing this file. Run scripts with
`python3 "$SKILL_DIR/scripts/<script>.py"` and keep their JSON output in a
temporary directory, not in the user's repository.

### Phase 1: Scope and preflight

1. Use the org and project already configured for Harness MCP. State them:
   `Working in org=..., project=...`. Do not ask.
2. Repository root: the path the user named, otherwise the workspace root that is a git repo.
3. Run `git status --porcelain`. Evidence is validated against `HEAD`. If the tree is dirty,
   continue and say in the summary that uncommitted files were ignored.
4. The repository needs an `origin` remote; risks are keyed to it. Stop if it has none.

### Phase 2: Last scan of this branch, then inventory

Look up the previous scan of this repository and this branch before reading
any source. Branch and commit live on the scan. One code-repository custom
service covers every branch of a module; reuse it whether this is a first scan,
a diff, or a skip. Do not create another service because the branch changed.

Decide from the newest scan whose `source.codeRepository.repoURL` matches this
origin (host/org/repo, no scheme) and whose `branch` is the current branch.
A scan of any other branch is not a baseline.

| Previous scan of this branch | What to do |
|---|---|
| None | Full inventory. Create a new scan of the whole tree. |
| Same `commitSHA` as `HEAD` | Skip. Do not inventory, fetch rules, create services, or create a scan. Say which branch and commit were already scanned, then stop. |
| Different `commitSHA` | Diff only. Pass that commit as `--since` and scan files changed between it and `HEAD`. Create a new scan that records this commit. |

If that previous commit is not an ancestor of `HEAD` (a rebase, or a commit git
cannot resolve), a diff is not possible. Inventory falls back to a full scan
and you still create the new scan. Say that in the summary.

1. Read the origin URL, the current branch, and `HEAD`:

```bash
git -C "$REPO" remote get-url origin
git -C "$REPO" rev-parse --abbrev-ref HEAD
git -C "$REPO" rev-parse HEAD
```

2. `harness_list(resource_type="chaos_risk_scan", filters={scan_type: "CodeRepository", sort_field: "lastUpdated", sort_ascending: false})`.
   Take the newest scan for this `repoURL` and this `branch`. If a list item has
   no `source`, `harness_get` that scan. A scan with an empty branch matches only
   when no same-branch scan exists. A scan that is listed but returns 404 on
   `harness_get` was deleted: treat it as no baseline, and say so in the summary.
   Keep the baseline scan identity; Phase 4 uses it for the regression check.
   Compare its `commitSHA` to `HEAD` and follow the table above. Stop here when
   they are equal.
3. Run inventory. Pass `--since <commitSHA>` only for a same-branch baseline
   with a different commit. Start at `--max-per-kind 80` so a large module is not scanned twice.

```bash
python3 "$SKILL_DIR/scripts/inventory.py" --repo "$REPO" --out "$TMP/inventory.json" --max-per-kind 80 [--since COMMIT]
```

4. Read `repo.scanMode` before opening any file. The same-commit case already
   stopped in step 2; these are the two modes that continue:

- `diff` — facts cover only files changed since `repo.baseCommit`. Map and submit
  only those. Open only files cited by facts. Create the scan.
- `full` — this branch has no previous scan, or its commit cannot bound a diff.
  Scan the tree as usual and create the scan.
- `unchanged` — `HEAD` is the commit already scanned. This is the same skip as
  step 2. Do not fetch rules, create services, or create a scan. Stop.

5. Before opening any source file, compare `counts` with the facts kept. If any
   module and kind has a higher count than the facts kept for it, re-run
   inventory once with `--max-per-kind` set to that largest count. Do this
   before Phase 3.

The output lists modules and facts (`kind`, `file`, `startLine`, `snippet`, `attrs`).
Facts are candidates, not findings. Test, example, vendor, generated, tooling and
frontend-only code is already excluded. Unchanged files are left as they were on
the previous scan; this run does not re-judge them.

### Phase 3: Fetch rules

`harness_list(resource_type="chaos_risk_rule", filters={data_source: "SourceCode"}, compact=false)`, all pages.
Save the bodies as `{"data": [...]}` in `$TMP/rules.json`. Call
`harness_get(resource_type="chaos_risk_rule", resource_id=<identity>)` only for
a rule whose `spec.faults` is missing. Read
[failure-modes.md](references/failure-modes.md) for the failure modes, faults and probe signals.

### Phase 4: Map facts to rules

The inventory is deterministic, so the verdicts must be too: two scans of the same
commit must report the same risks. Every actionable fact ends in exactly one state:
**reported** in a finding, or **cleared** by a cited mitigation. There is no third
state such as "skipped", "low impact" or "not verified".

Actionable facts, per `scripts/coverage.py`:

| Fact | Actionable when |
|---|---|
| `outbound_client` | `timeout` is `none` or `unknown` |
| `retry_construct` | `backoff` is `none` or `constant`, or `attempt_cap` is not `bounded` |
| `health_endpoint`, `serving_entrypoint`, `local_state` | always (open the file and decide) |

Work module by module, not in the order you find interesting. Group the
actionable facts by file. Read each cited file once, in one batch, and decide
every fact in that file from that read. Open another file only when the
mitigation lives there, such as a shared client factory or the `main` of a
one-shot job. On a `diff` scan, do not open a file the inventory did not cite.
For every actionable fact, look for a mitigation:

- A shared client factory or `client.Timeout` set after construction, a context deadline
  at the call site, a mesh timeout in repo config.
- A resilience library with exponential backoff and jitter wrapping the call.
- `Shutdown`/`Stop` called after SIGTERM; readiness that returns non-2xx when the
  dependency is down; state kept in an external store.
- The code is startup-only, a CLI or a one-shot job (cite the entry point line).
- A `harness-chaos-ignore` comment.

If a mitigation exists, add a disposition (below). If none does, it is a finding.
Do not clear a fact because the call looks minor (a Slack notifier, a reporter, a
library helper): a call that can hang is a risk wherever it sits. Do not clear a
fact you have not opened. `attrs.timeout: unknown` needs a look at the call site;
if you still cannot tell, report it with the uncertainty in `evidence`, not drop it.

A retry with backoff does not bound a single attempt. A client with no `Timeout` is
still a timeout finding even when its retries use backoff.

Write one finding per (rule, module) for every module that has an uncleared fact. Put
up to 5 call sites in `codeLocations` and the total in `callSiteCount`. Count call
sites from the inventory (`grep`-verifiable), not by estimate. Cap: 8 findings per module.

Write `$TMP/dispositions.json` for every cleared fact:

```json
{"dispositions": [
  {"module": "subscriber", "file": "subscriber/pkg/common/restCall.go", "startLine": 61,
   "kind": "outbound_client", "reason": "shared_factory_timeout",
   "mitigation": {"file": "subscriber/pkg/common/restCall.go", "line": 70},
   "note": "client.Timeout is set to 40s right after construction"}
]}
```

`reason` is one of `shared_factory_timeout`, `context_deadline`, `mesh_timeout`,
`resilience_library`, `bounded_backoff`, `graceful_shutdown_present`,
`health_check_correct`, `external_store`, `not_serving_path`, `suppressed`,
`pattern_absent` (the match is not the risk, such as an import used only to parse;
cite the real usage).
`mitigation` must point at a real file and line at `HEAD`.

**Regression check against the baseline.** When Phase 2 found a baseline scan that
still exists, fetch its findings (`harness_execute(resource_type="chaos_risk_scan",
action="report", resource_id=<baseline>)`). For each prior (rule, module), either this
scan reports it again or you confirm at `HEAD` that the cited code changed or was
fixed. Say which in the summary. A prior finding that vanished with unchanged code
means you under-reported: go back and report it.

### Phase 5: Create missing catalog rules

If a confirmed risk has no matching rule, follow [rule-authoring.md](references/rule-authoring.md).

- An existing rule covers the failure mode: use it. Do not update it.
- No rule exists, and the failure mode is in failure-modes.md: `harness_create` that
  catalog rule with `confirm: true`. Do not show a confirmation message and do not wait.
- Anything else: drop the finding and list it in the summary.

After any create, re-fetch rules into `$TMP/rules.json`. The confirmation message in
rule-authoring.md applies only when the user asked to add or edit a rule on its own.

### Phase 6: Draft findings

Write `$TMP/draft.json` as `{"findings": [...]}` using the shape in
[evidence-contract.md](references/evidence-contract.md):

- `codeLocations[].snippet` is copied verbatim from the inventory or the file at `HEAD`.
- `resilienceTestingRec` names at least one fault from the rule's `spec.faults` and the probe signal.
- `module` is the inventory module path (`.` for the root).
- Do not send severity or category; they come from the rule.

### Phase 7: Validate

```bash
python3 "$SKILL_DIR/scripts/validate_evidence.py" --repo "$REPO" \
  --rules "$TMP/rules.json" --findings "$TMP/draft.json" --out "$TMP/valid.json"
```

Read `dropped`. Fix a finding only if the reason is a mistake you made (wrong line
range, missing fault name) and the code really shows the risk; otherwise leave it dropped.
Code marked `harness-chaos-ignore: <rule> <reason>` is suppressed on purpose; respect it.

Then run the coverage gate. It must exit 0 before you onboard or submit anything:

```bash
python3 "$SKILL_DIR/scripts/coverage.py" --repo "$REPO" --inventory "$TMP/inventory.json" \
  --findings "$TMP/valid.json" --dispositions "$TMP/dispositions.json" --out "$TMP/coverage.json"
```

Exit 1 means some actionable fact is neither reported nor cleared, or a disposition
cites an unacceptable reason or a missing mitigation line. Read `uncovered` and
`badDispositions` in `coverage.json`, open each file, then add a finding or a real
disposition and rerun. Do not edit a disposition to make it pass without a mitigation
you have read. If a finding was dropped by the validator, its facts become uncovered
again; fix the finding or clear the facts with a genuine mitigation.
Omit `--dispositions` when nothing was cleared. In `diff` mode the inventory only
holds changed files, so the gate checks only those.

### Phase 8: Onboard each module that has a finding

Findings are stored only when a CodeRepository chaos service matches the repo URL and
module. For each module that still has a valid finding, reuse or create that pair.
Do not ask which service to use, and do not link a runtime discovered service.

Match the inventory `repoURL` and the module path. One custom service and one
   chaos service cover every branch of that module. A different branch is a new
   scan of the same service, not a new service. Do not put the branch in the
   name, the identity, or the create body, and do not update an existing service
   to store the current branch.

Compare repository URLs after normalizing both sides: lowercase, drop the scheme
(`https://`, `http://`, `ssh://`, `git://`), userinfo, a trailing slash, and a
`.git` suffix, then turn `:` into `/`. `github.com/acme/payments` matches
`https://github.com/acme/payments.git`. An empty module and `"."` are the same
module. Ignore any `branch` already stored on a custom service.

1. `harness_list(resource_type="custom_service", filters={type: "CodeRepository"})`.
   Reuse the service whose normalized `repoURL` and module match, even when its
   branch differs from `HEAD` or its identity contains a branch name. When more
   than one matches, reuse the one whose identity is the `{repo}-{module}` slug;
   otherwise reuse the oldest. Do not create another. Create only when none match:
   `harness_create(resource_type="custom_service", confirm=true)` with
   `type=CodeRepository`, `repo_url` set to the origin URL, `module` set to the
   inventory path, `tags=["code-scan"]`, `name` `{repo} {module}`, and `identity`
   a slug of `{repo}-{module}` (`.` becomes `root`). Keep the returned `id`.
   Do not send `branch`. If a create fails because the identity is too long,
   shorten the slug from the end and say so. A duplicate identity means this
   service already exists: look it up and reuse it.
2. `harness_list(resource_type="chaos_service")`. Reuse the service whose
   `externalServiceId` is the custom service id from step 1, on every branch.
   Otherwise
   `harness_create(resource_type="chaos_service", confirm=true)` with the same
   identity and name, `agent_id=custom-discovery-agent`, `external_service_id` set
   to the custom service **id** (not the slug), `tags=["code-scan"]`, and `probes=[]`.
   Omit `environment_id`, `infrastructure_id`, `infrastructure_type`, and
   `linked_discovered_service`.
3. Remember `MODULE=<chaos service identity>` for `--link`.

Create every missing custom service in one batch, then every missing chaos service
in one batch.

If a create fails, leave that module's findings out of the submit and record the error.
Continue with the other modules. A duplicate identity means the service already exists:
look it up and reuse it.

### Phase 9: Create the scan and submit

```bash
python3 "$SKILL_DIR/scripts/build_payload.py" scan --inventory "$TMP/inventory.json" \
  [--link services/api=payments-api ...] --out "$TMP/scan.json"
python3 "$SKILL_DIR/scripts/build_payload.py" findings --findings "$TMP/valid.json" --out "$TMP/findings.json"
```

Pass every remembered module as `--link MODULE=CHAOS_SERVICE_IDENTITY`. Omit a module
that has no chaos service; its findings are not stored.

`scan.json` stores both `source.codeRepository.branch` and `commitSHA`. Confirm
both are present before creating the scan. Omit `branch` only when `HEAD` is detached.

When `scanMode` is `diff` and validation kept no findings, still create the scan
and submit `{"findings": []}`. That records this commit as the next baseline so
the same diff is not read again. Do not do this for `unchanged`.

1. `harness_create(resource_type="chaos_risk_scan", confirm=true, body=<scan.json>)`.
2. `harness_execute(resource_type="chaos_risk_scan", action="submit_findings", resource_id=<identity>, body=<findings.json>)`.
   The first successful submission completes the scan; submit once. Do not wait for a review.
3. If the response lists per-finding `errors`, report them. If the call fails with
   "not accepting findings", the scan was already completed; create a new scan.

### Phase 10: Summarise

Report the scan identity, branch, commit, scan mode (`full`, `diff` from
`<baseCommit>`, or `unchanged`), saved and failed counts, the findings table, any custom
services and chaos services created or reused, any catalog rules created, modules
left out because onboarding failed, and dropped findings with the reason. Add the
coverage line from `coverage.py` (actionable, covered, cleared) with each cleared
fact's reason and mitigation, and the baseline regression result (re-reported, fixed
in code, or none because no baseline existed). Then
explain how to verify each risk:

- A code-repository risk whose chaos service has a mapped discovered service gets an experiment recommendation for that workload and the rule's faults.
- A risk becomes **Confirmed** when an experiment runs against the linked service with a
  probe whose rule details reference the rule identity, and the probe fails. Hand off to
  `chaos-experiment` to build that experiment.
- The scan report is available via `harness_execute(resource_type="chaos_risk_scan", action="report")`.

End with this offer, naming each code-repository chaos service from this run.
Do not list agents, services, or probes, and do not call update:

> You can attach the code-repository chaos service `<identity>` to a discovered
> service so Harness can recommend experiments for these risks. Say if you want
> to do that.

### Attach a discovered service (only when the user asks)

This is a separate turn. Wait until the user asks to attach. Then ask, and do
not update until they have answered:

1. Which code-repository chaos service, when this run produced more than one.
2. Which workload. List `discovered_agent` (skip `custom-discovery-agent`),
   ask them to pick an agent, then list `discovered_service` for that agent and
   its `environmentIdentifier` with `compact: false`. The environment is required;
   an empty environment looks the agent up as missing.
   Offer only records whose `identity` is `namespace:kind:name` and whose kind is
   `Deployment`, `DaemonSet`, or `StatefulSet` (for example `hce:Deployment:frontend`).
   Show that identity, not just the name. A Kubernetes Service such as
   `hce:Service:nginx` cannot be an experiment target. When the user names a
   service ("nginx"), link the workload of that name (`hce:Deployment:nginx`,
   then StatefulSet, then DaemonSet). If the name match is only a Service, read
   `spec.kubernetes.workloads` on that record and link the discovered service
   whose identity is that workload's `namespace:kind:name`. If no such workload
   exists, say so and do not link the Service. Keep the agent's identity, its
   environment, and the workload record's `id`.
3. Which probes to associate. Ask whether to add any. If they do, list
   `chaos_probe` and have them fill each required input. If they do not, keep
   the probes already on the service.

Then `harness_get` the chaos service and `harness_update` it with `confirm: true`.
The update replaces the record, so resend `name`, `description`, `tags`,
`external_service_id`, and `agent_id` (`custom-discovery-agent`) from the get.
`agent_id` stays `custom-discovery-agent`. Also send the discovered service's
infrastructure the same way a chaos service is created for that service: for a
Kubernetes discovery agent, `environment_id` is the agent's `environmentIdentifier`,
`infrastructure_id` is the agent's identity (bare, not environment-prefixed), and
`infrastructure_type` is `KubernetesV2`. Send `probes` as the full set (the
existing ones, plus any they just chose). Send

```json
"environment_id": "<agent environment>",
"infrastructure_id": "<agent identity>",
"infrastructure_type": "KubernetesV2",
"linked_discovered_service": { "agent_id": "<agent identity>", "environment_id": "<agent environment>", "external_id": "<discovered service id>" }
```

`external_id` is the workload record's id, not its name and not the Kubernetes
Service of the same name. After the update, `harness_get` the chaos service and
check `linkedDiscoveredService.identity`. It must be `namespace:Deployment:name`,
`namespace:DaemonSet:name`, or `namespace:StatefulSet:name`. If the kind is
`Service`, the wrong record was linked; find the workload and update again.
Report the chaos service identity, the workload identity, and the infrastructure
that were linked.

## Examples

- "Scan this repo for resilience risks we can test with chaos" — inventory, onboard, submit. No questions.
- "Scan this feature branch" — full inventory when this branch has no previous scan. Reuse the custom service and chaos service for each module. Findings for module `api` on `feature/retry-budget` land on the same `payments-api` service as `main`.
- "Scan again, nothing new committed" — the newest scan of this branch already has this `commitSHA`. Stop. Do not create a scan.
- "Scan again after new commits on the same branch" — reuse those services and pass `--since` the previous scan's `commitSHA`. Only changed files are read.
- "Run a chaos code scan and link `services/api` to the `payments-api` service" — Phase 9 uses that link and still onboards any other module that has findings.
- "Why was my finding dropped?" — read `dropped` in `valid.json` and explain the reason.
- "Add a rule for retries without backoff" — rule authoring only, and this one waits for confirmation.
- "Create a chaos experiment for these risks" — hand off to `chaos-experiment`.
- "Attach this code-repository service to a discovered service" — the attach section only. Ask for a Deployment, DaemonSet, or StatefulSet and for probes, then update.

## Performance Notes

Follow this order. The Harness submit is a few seconds; the time is spent reading source.

1. Same branch, same commit: stop. Do not inventory or create a scan.
2. Same branch, different commit: pass `--since` that scan's `commitSHA`. Inventory
   reads only changed files. A branch with no previous scan is a full inventory.
   Either way, reuse the custom service and chaos service for each module.
3. Start inventory at `--max-per-kind 80`. The script default is 40. If `counts`
   shows a kind was truncated, re-run once with a higher cap before reading source.
4. One read per cited file, in a single batch. Decide every fact in that file from
   that read. On a `diff` scan, do not open a file the inventory did not cite.
5. List rules with `compact: false`. `harness_get` a rule only when `spec.faults` is absent.
6. Create the missing custom services in one batch, then the chaos services in one
   batch. Submit findings once.

`validate_evidence.py` reads each file once at the commit via `git show`. A scan that
misses a risk the previous scan of that branch found erodes trust as much as a false
positive. Precision comes from verifying each fact and citing the mitigation, not from
dropping facts you did not check. `coverage.py` enforces this. At most 8 findings per
module and 100 per scan; the validator enforces both.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `coverage.py` exits 1 with `uncovered` facts | Open each fact's file. Report it, or add a disposition that cites a real mitigation line. "Low impact" and "not verified" are not allowed |
| Custom service exists for the same repo URL and module on another branch | Reuse that custom service and its chaos service. Do not create one for this branch. Branch and commit are stored on the scan |
| `coverage.py` reports a bad disposition | The `reason` must be from the allowed list and `mitigation` must be an existing file and line at `HEAD` |
| Baseline scan listed but `harness_get` returns 404 | It was deleted. Run a full scan and note that no baseline existed |
| `not a git work tree` | Point `--repo` at the repository root |
| Baseline commit is not an ancestor of HEAD | Inventory falls back to a full scan. This happens after a rebase or on a branch with no previous scan |
| `the repository has no origin remote` | Add an `origin` remote; risks are keyed by repo URL |
| `snippet does not match the file` | Copy the snippet from the file at `HEAD`; check the line range covers it |
| `names none of the rule faults` | Mention one of the rule's `spec.faults` in `resilienceTestingRec` |
| `rule ... is not in the fetched rule list` | Re-fetch rules after creating one in Phase 5 |
| Rule create fails on identity | Identity must match `^code-[a-z0-9-]{3,60}$` and name a failure mode |
| Rule create fails on limit | A project allows 30 custom SourceCode rules; update an overlapping rule instead |
| `submit_findings` returns 409 | The scan is no longer accepting findings; create a new scan |
| `chaosServiceIdentity` not found | List `chaos_service` and use an existing identity, or leave the module unlinked |
| Mapped service gets no experiment recommendation | The link is a Kubernetes Service (`namespace:Service:name`). Re-attach the Deployment, DaemonSet, or StatefulSet whose identity is `namespace:kind:name` |
