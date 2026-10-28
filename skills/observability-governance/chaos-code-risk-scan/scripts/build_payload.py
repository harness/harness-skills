#!/usr/bin/env python3
"""Build the MCP payloads for a CodeRepository risk scan.

  scan      body for harness_create(resource_type=chaos_risk_scan)
  findings  body for harness_execute(resource_type=chaos_risk_scan, action=submit_findings)

Usage:
  build_payload.py scan --inventory INVENTORY.json [--link MODULE=SERVICE ...] [--out FILE]
  build_payload.py findings --findings VALID.json [--out FILE]
"""

import argparse
import re
import sys
import time
from typing import List, Optional

from _common import MAX_FINDINGS, load_json, normalize_module, unwrap_list, write_json

FINDING_FIELDS = (
    "riskRuleId", "riskName", "description", "impact", "module",
    "evidence", "remediation", "resilienceTestingRec", "codeLocations", "callSiteCount",
)
PROVIDERS = {"github.com": "github", "gitlab.com": "gitlab", "bitbucket.org": "bitbucket"}


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


def build_scan(inventory: dict, links: List[str]) -> dict:
    repo = inventory["repo"]
    repo_url, commit = repo.get("repoURL"), repo.get("commitSHA")
    if not repo_url:
        raise SystemExit("error: the repository has no origin remote; set one so risks can be keyed to it")
    repo_name = repo_url.rsplit("/", 1)[-1]
    short = commit[:8]
    identity = "code-scan-{}-{}-{}".format(slug(repo_name)[:30], short, time.strftime("%Y%m%d%H%M"))

    modules = {m["path"] for m in inventory.get("modules", [])}
    linked = parse_links(links)
    unknown = [l["module"] for l in linked if l["module"] not in modules]
    if unknown:
        print("warning: linked modules not detected by inventory: {}".format(", ".join(unknown)), file=sys.stderr)

    source = {"repoURL": repo_url, "commitSHA": commit, "provider": provider_for(repo_url)}
    if repo.get("branch"):
        source["branch"] = repo["branch"]
    if linked:
        source["linkedServices"] = linked
    return {
        "identity": identity,
        "name": "Code scan {}@{}".format(repo_name, short),
        "tags": ["code-scan"],
        "scanType": "CodeRepository",
        "detectionMethod": "External",
        "source": {"codeRepository": source},
    }


def build_findings(validated) -> dict:
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
    return {"findings": findings}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    scan = sub.add_parser("scan")
    scan.add_argument("--inventory", required=True)
    scan.add_argument("--link", action="append", default=[], help="MODULE=CHAOS_SERVICE_IDENTITY (repeatable)")
    scan.add_argument("--out", default="-")
    fnd = sub.add_parser("findings")
    fnd.add_argument("--findings", required=True, help="validate_evidence.py output")
    fnd.add_argument("--out", default="-")
    args = parser.parse_args(argv)

    if args.cmd == "scan":
        write_json(args.out, build_scan(load_json(args.inventory), args.link))
    else:
        write_json(args.out, build_findings(load_json(args.findings)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
