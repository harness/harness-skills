#!/usr/bin/env python3
"""Build the MCP payloads for a CodeRepository or CIRiskScan.

  scan      body for harness_create(resource_type=chaos_risk_scan)
  findings  body for harness_execute(resource_type=chaos_risk_scan, action=submit_findings)

Usage:
  build_payload.py scan --inventory INVENTORY.json [--scan-type CodeRepository|CIRiskScan]
    [--identity ID] [--scope branch|commit|pullRequest] [--pull-request-number N]
    [--target-branch BRANCH] [--base-sha SHA] [--link MODULE=SERVICE ...] [--out FILE]
  build_payload.py findings --findings VALID.json [--scan-type CodeRepository|CIRiskScan]
    [--commit-sha SHA] [--out FILE]
"""

import argparse
import re
import sys
import time
from typing import List, Optional

from _common import MAX_FINDINGS, load_json, normalize_module, unwrap_list, write_json

FINDING_FIELDS = (
    "riskRuleId", "riskName", "description", "impact", "module",
    "evidence", "remediation", "resilienceTestingRec", "codeLocations", "callSiteCount", "tags",
)
PROVIDERS = {"github.com": "github", "gitlab.com": "gitlab", "bitbucket.org": "bitbucket"}
SCAN_TYPES = {"CodeRepository", "CIRiskScan"}


def slug(s: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]", "-", s.lower())).strip("-")


def provider_for(repo_url: str) -> str:
    host = repo_url.split("/", 1)[0]
    if host in PROVIDERS:
        return PROVIDERS[host]
    if "harness" in host:
        return "harness"
    return "git"


def parse_links(links: List[str]) -> List[dict]:
    out, seen = [], set()
    for link in links:
        module, sep, service = link.partition("=")
        module, service = normalize_module(module), service.strip()
        if not sep or not service:
            raise SystemExit("error: --link must be MODULE=SERVICE_IDENTITY, got {!r}".format(link))
        if module in seen:
            raise SystemExit("error: module {} is linked more than once".format(module))
        seen.add(module)
        out.append({"module": module, "chaosServiceIdentity": service})
    return out


def build_scan(
    inventory: dict,
    links: List[str],
    scan_type: str = "CodeRepository",
    identity: Optional[str] = None,
    scope: str = "",
    pull_request_number: str = "",
    target_branch: str = "",
    base_sha: str = "",
) -> dict:
    if scan_type not in SCAN_TYPES:
        raise SystemExit("error: --scan-type must be CodeRepository or CIRiskScan, got {!r}".format(scan_type))
    repo = inventory["repo"]
    repo_url, commit = repo.get("repoURL"), repo.get("commitSHA")
    if not repo_url:
        raise SystemExit("error: the repository has no origin remote; set one so risks can be keyed to it")
    repo_name = repo_url.rsplit("/", 1)[-1]
    short = (commit or "pending")[:8]
    prefix = "ci-risk-scan" if scan_type == "CIRiskScan" else "code-scan"
    if not identity:
        identity = "{}-{}-{}-{}".format(prefix, slug(repo_name)[:30], short, time.strftime("%Y%m%d%H%M"))

    modules = {m["path"] for m in inventory.get("modules", [])}
    linked = parse_links(links)
    unknown = [l["module"] for l in linked if l["module"] not in modules]
    if unknown:
        print("warning: linked modules not detected by inventory: {}".format(", ".join(unknown)), file=sys.stderr)

    source = {"repoURL": repo_url, "provider": provider_for(repo_url)}
    if commit:
        source["commitSHA"] = commit
    if repo.get("branch"):
        source["branch"] = repo["branch"]
    if linked:
        source["linkedServices"] = linked

    if scan_type == "CIRiskScan":
        resolved = (scope or "branch").strip()
        if resolved not in ("branch", "commit", "pullRequest"):
            raise SystemExit("error: --scope must be branch, commit, or pullRequest, got {!r}".format(scope))
        source["scope"] = resolved
        if resolved == "pullRequest":
            if not pull_request_number.strip():
                raise SystemExit("error: --pull-request-number is required for CIRiskScan scope pullRequest")
            source["pullRequestNumber"] = pull_request_number.strip()
            if target_branch.strip():
                source["targetBranch"] = target_branch.strip()
            if base_sha.strip():
                source["baseSHA"] = base_sha.strip()
        else:
            if not source.get("branch"):
                raise SystemExit("error: inventory branch (or CIRiskScan scope branch) is required")
            if base_sha.strip():
                source["baseSHA"] = base_sha.strip()
    elif scope.strip():
        raise SystemExit("error: --scope is only valid with --scan-type CIRiskScan")

    name = (
        "CI risk scan {}@{}".format(repo_name, short)
        if scan_type == "CIRiskScan"
        else "Code scan {}@{}".format(repo_name, short)
    )
    tags = ["ci-risk-scan"] if scan_type == "CIRiskScan" else ["code-scan"]
    return {
        "identity": identity,
        "name": name,
        "tags": tags,
        "scanType": scan_type,
        "detectionMethod": "External",
        "source": {"codeRepository": source},
    }


def build_findings(validated, commit_sha: Optional[str] = None, scan_type: str = "") -> dict:
    if scan_type and scan_type not in SCAN_TYPES:
        raise SystemExit("error: --scan-type must be CodeRepository or CIRiskScan, got {!r}".format(scan_type))
    if scan_type == "CIRiskScan" and not (commit_sha or "").strip():
        raise SystemExit("error: --commit-sha is required for CIRiskScan findings")
    findings = []
    for f in unwrap_list(validated, "valid", "findings"):
        out = {k: f[k] for k in FINDING_FIELDS if f.get(k) not in (None, "", [])}
        out["codeLocations"] = [
            {"file": l["file"], "startLine": l["startLine"], "endLine": l["endLine"], "snippet": l["snippet"]}
            for l in f["codeLocations"]
        ]
        findings.append(out)
    if len(findings) > MAX_FINDINGS:
        raise SystemExit("error: {} findings; at most {} per scan. Re-run validate_evidence.py with a lower "
                         "--max-per-module.".format(len(findings), MAX_FINDINGS))
    body = {"findings": findings}
    if commit_sha:
        body["commitSHA"] = commit_sha
    return body


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("--inventory", required=True)
    scan.add_argument("--scan-type", default="CodeRepository", help="CodeRepository or CIRiskScan")
    scan.add_argument("--identity", default="", help="reuse an existing scan identity instead of minting one")
    scan.add_argument("--scope", default="", help="CIRiskScan only: branch, commit, or pullRequest")
    scan.add_argument("--pull-request-number", default="", help="required when --scope pullRequest")
    scan.add_argument("--target-branch", default="", help="PR target branch (optional on create)")
    scan.add_argument("--base-sha", default="", help="merge-base / parent SHA (optional on create)")
    scan.add_argument("--link", action="append", default=[], help="MODULE=CHAOS_SERVICE_IDENTITY (repeatable)")
    scan.add_argument("--out", default="-")
    fnd = sub.add_parser("findings")
    fnd.add_argument("--findings", required=True, help="validate_evidence.py output")
    fnd.add_argument("--scan-type", default="", help="when CIRiskScan, --commit-sha is required")
    fnd.add_argument("--commit-sha", default="", help="HEAD SHA; required for CIRiskScan submit_findings")
    fnd.add_argument("--out", default="-")
    args = parser.parse_args(argv)

    if args.cmd == "scan":
        write_json(args.out, build_scan(
            load_json(args.inventory), args.link, args.scan_type, args.identity or None,
            args.scope, args.pull_request_number, args.target_branch, args.base_sha,
        ))
    else:
        write_json(args.out, build_findings(load_json(args.findings), args.commit_sha or None, args.scan_type))
    return 0


if __name__ == "__main__":
    sys.exit(main())
