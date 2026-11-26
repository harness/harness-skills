---
name: ci-risk-scan
description: >-
  Delta on chaos-code-risk-scan for Harness CI Risk Scan (scanType
  CIRiskScan / Build Scans). Follow chaos-code-risk-scan for inventory,
  mapping, custom rules, onboarding, evidence, and submit. Use when a
  Worker Agent or CI pipeline runs a CI risk scan. Do not use for ad-hoc
  CodeRepository MCP scans.
metadata:
  author: Harness
  version: 1.2.0
  mcp-server: harness-mcp-v2
  module: CHAOS
  summary: CI Risk Scan deltas on chaos-code-risk-scan
license: Apache-2.0
compatibility: >-
  Requires Harness MCP v2 with chaos_risk_scan submit_findings, Python 3.9+,
  git, and chaos-code-risk-scan/scripts. SKILL_DIR must point at that scripts
  parent (the chaos-code-risk-scan skill directory).
---

# CI Risk Scan (delta)

Follow [chaos-code-risk-scan](../chaos-code-risk-scan/SKILL.md) with these
replacements. Do not invert the parent phases. Do not attach a discovered
service during the scan. Do not add a second skill or a PRRiskScan type.
One submit per scan.

Scripts: `python3 "$SKILL_DIR/scripts/<script>.py"` where `SKILL_DIR` is
`chaos-code-risk-scan` (exported by the pipeline as
`/harness/harness-skills/skills/observability-governance/chaos-code-risk-scan`).

## Inputs

Read `/harness/scan-context.json`. `scanIdentity` is required. Never create
a second scan. Never call `build_payload.py scan` when an identity was
provided.

Use `repoURL` from that file (connector repository). Do not key services
off a fork `origin` URL.

Scope, PR number, target branch, base SHA, and head SHA come from that
file. Branch comes from the file when `git rev-parse --abbrev-ref HEAD`
is `HEAD`.

## Phase 2 — skip and baseline (per scope)

List `harness_list(resource_type="chaos_risk_scan", filters={scan_type:
"CIRiskScan", repo_url: <normalized>, sort_field: "lastUpdated",
sort_ascending: false}, limit=100)`. Use `repo_url` (MCP query key), not
`repoURL`. Never list CodeRepository. Exclude `scanIdentity`. Client-filter
status, scope, branch, PR number, and SHAs over that page (there is no
server-side scope filter yet; if the newest same-scope COMPLETED scan is
older than the page, treat it as missing). A commit or pullRequest scan is
never the baseline for a branch scan.

Skip (submit `[]` plus HEAD SHA, do not inventory) only inside one scope:

| Scope | Skip when a COMPLETED CIRiskScan exists with |
|---|---|
| branch | same repo, branch, scope branch, same HEAD |
| commit | same repo, scope commit, same HEAD |
| pullRequest | same PR number, same HEAD, same base SHA |

If the target branch moved and the head did not, the PR diff changed; do
not skip.

Branch inventory otherwise:

| Baseline | Action |
|---|---|
| None, or SHA not an ancestor of HEAD | Full: `inventory.py` without `--since`. Say so. |
| Different ancestor SHA | `inventory.py --since <sha>` (whole file). |

Commit and pullRequest never use `--since`. They use hunks. Empty facts
still submit `[]` plus HEAD SHA.

## Inventory

`--repo-url` is the connector repo from scan-context.

```bash
# branch
python3 "$SKILL_DIR/scripts/inventory.py" --repo "$REPO" --repo-url "$REPO_URL" \
  --out "$TMP/inventory.json" --max-per-kind 80 [--since COMMIT]

# commit (tip commit only)
python3 "$SKILL_DIR/scripts/inventory.py" --repo "$REPO" --repo-url "$REPO_URL" \
  --hunk-from "$BASE_SHA" --out "$TMP/inventory.json" --max-per-kind 80

# pullRequest (union: PR diff + tip-commit tags)
python3 "$SKILL_DIR/scripts/inventory.py" --repo "$REPO" --repo-url "$REPO_URL" \
  --hunk-from "$BASE_SHA" --commit-hunk-from "$PARENT_SHA" \
  --out "$TMP/inventory.json" --max-per-kind 80
```

`BASE_SHA` for commit is `HEAD^`. For pullRequest it is
`merge-base(origin/$TARGET, HEAD)` (three-dot against the target, not
`target..HEAD`). `PARENT_SHA` is `HEAD^`.

A PR trigger is scope `pullRequest` and uses the union command. Copy
`ciRange` onto finding `tags` as `ciRange:commit` or `ciRange:pullRequest`.
A fact in both ranges is stored once with `ciRange:commit`. The pipeline
`comment_on_pr` step (not this skill) posts the Build Scan risks URL onto
the GitHub PR after a successful Agent.

Do not walk every commit. Do not scan files whole on commit/PR.

## Phases 5, 8, 9

Same as the previous CI delta: custom rule on no match, 409 reuse; one
custom service and one chaos service per module, no attach; one
`submit_findings` with `commitSHA`. Always pass `--scan-type CIRiskScan`
so `--commit-sha` is enforced. `build_payload.py findings` forwards
`tags`. Non-`ciRange` tags are stripped by CM before store.
