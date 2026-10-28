#!/usr/bin/env python3
"""Check drafted findings against the repository and the fetched rules.

Every code location is re-read at the commit SHA and its snippet must appear
verbatim (whitespace-normalised) within the stated line range. Findings whose
rule is unknown, whose testing recommendation names no fault from the rule,
or whose locations are all invalid or suppressed are dropped with a reason.
Duplicate (rule, module) findings are merged and each module is capped.

Usage: validate_evidence.py --repo PATH --rules RULES.json --findings DRAFT.json
                            [--commit SHA] [--max-per-module N] [--out FILE]
"""

import argparse
import re
import subprocess
import sys
from typing import Dict, List, Optional, Tuple

from _common import (
    MAX_BULLET, MAX_BULLETS, MAX_CODE_LOCATIONS, MAX_FINDINGS, MAX_NAME, MAX_SNIPPET, MAX_TEXT,
    SEVERITY_ORDER, SUPPRESSION_RE,
    git, is_excluded, is_safe_relative_path, load_json, normalize_module, parse_fault_names,
    rule_data_sources, rule_faults, rules_by_identity, unwrap_list, write_json,
)

BULLET_FIELDS = ("evidence", "remediation", "resilienceTestingRec")
WS_RE = re.compile(r"\s+")


class FileCache:
    """File contents at one commit, read lazily through git show."""

    def __init__(self, repo: str, commit: str):
        self.repo = repo
        self.commit = commit
        self._lines: Dict[str, Optional[List[str]]] = {}

    def lines(self, path: str) -> Optional[List[str]]:
        if path not in self._lines:
            try:
                text = git(self.repo, "show", "{}:{}".format(self.commit, path))
                self._lines[path] = text.splitlines()
            except subprocess.CalledProcessError:
                self._lines[path] = None
        return self._lines[path]


def squash(s: str) -> str:
    return WS_RE.sub(" ", s).strip()


def check_text(finding: dict) -> Optional[str]:
    name = (finding.get("riskName") or "").strip()
    if not name:
        return "riskName is empty"
    if len(name) > MAX_NAME:
        return "riskName is longer than {} characters".format(MAX_NAME)
    for field in ("description", "impact"):
        if len(finding.get(field) or "") > MAX_TEXT:
            return "{} is longer than {} characters".format(field, MAX_TEXT)
    for field in BULLET_FIELDS:
        bullets = [b.strip() for b in finding.get(field) or [] if isinstance(b, str) and b.strip()]
        if not bullets:
            return "{} is empty".format(field)
        if len(bullets) > MAX_BULLETS:
            return "{} has more than {} bullets".format(field, MAX_BULLETS)
        if any(len(b) > MAX_BULLET for b in bullets):
            return "{} has a bullet longer than {} characters".format(field, MAX_BULLET)
        finding[field] = bullets
    return None


def check_location(loc: dict, module: str, rule_id: str, files: FileCache) -> Tuple[Optional[dict], Optional[str]]:
    if not isinstance(loc, dict):
        return None, "code location is not an object"
    path = (loc.get("file") or "").strip()
    if path.startswith("./"):
        path = path[2:]
    if not is_safe_relative_path(path):
        return None, "unsafe file path {!r}".format(path)
    if is_excluded(path):
        return None, "{} is test, example, vendor, generated or tooling code".format(path)
    if module != "." and not path.startswith(module + "/"):
        return None, "{} is outside module {}".format(path, module)
    try:
        start, end = int(loc.get("startLine")), int(loc.get("endLine", loc.get("startLine")))
    except (TypeError, ValueError):
        return None, "{}: startLine/endLine are not integers".format(path)
    lines = files.lines(path)
    if lines is None:
        return None, "{} does not exist at the commit".format(path)
    if not 1 <= start <= end <= len(lines):
        return None, "{}:{}-{} is outside the file ({} lines)".format(path, start, end, len(lines))
    snippet = loc.get("snippet") or ""
    if not snippet.strip():
        return None, "{}:{}: snippet is empty".format(path, start)
    if len(snippet) > MAX_SNIPPET:
        return None, "{}:{}: snippet is longer than {} characters".format(path, start, MAX_SNIPPET)
    if squash(snippet) not in squash("\n".join(lines[start - 1:end])):
        return None, "{}:{}-{}: snippet does not match the file".format(path, start, end)
    for line in lines[max(0, start - 2):end]:
        m = SUPPRESSION_RE.search(line)
        if m and m.group(1) == rule_id:
            return None, "{}:{}: suppressed by harness-chaos-ignore".format(path, start)
    return {"file": path, "startLine": start, "endLine": end, "snippet": snippet}, None


def validate_one(finding: dict, rules: Dict[str, dict], files: FileCache) -> Tuple[Optional[dict], str]:
    rule_id = (finding.get("riskRuleId") or "").strip()
    rule = rules.get(rule_id)
    if rule is None:
        return None, "rule {!r} is not in the fetched rule list".format(rule_id)
    if "SourceCode" not in rule_data_sources(rule):
        return None, "rule {} is not a SourceCode rule".format(rule_id)
    faults = rule_faults(rule)
    if not faults:
        return None, "rule {} lists no faults".format(rule_id)

    module = normalize_module(finding.get("module"))
    if module != "." and not is_safe_relative_path(module):
        return None, "unsafe module path {!r}".format(module)

    reason = check_text(finding)
    if reason:
        return None, reason
    if not set(parse_fault_names(finding["resilienceTestingRec"])) & set(faults):
        return None, "resilienceTestingRec names none of the rule faults: {}".format(", ".join(faults))

    locations, reasons = [], []
    for loc in finding.get("codeLocations") or []:
        ok, why = check_location(loc, module, rule_id, files)
        if ok:
            locations.append(ok)
        else:
            reasons.append(why)
    if not locations:
        return None, "no valid code location ({})".format("; ".join(reasons) or "none given")

    out = {
        "riskRuleId": rule_id,
        "riskName": finding["riskName"].strip(),
        "description": (finding.get("description") or "").strip(),
        "impact": (finding.get("impact") or "").strip(),
        "module": module,
        "evidence": finding["evidence"],
        "remediation": finding["remediation"],
        "resilienceTestingRec": finding["resilienceTestingRec"],
        "codeLocations": locations,
        "callSiteCount": max(int(finding.get("callSiteCount") or 0), len(locations)),
    }
    return out, "; ".join(reasons)


def merge(findings: List[dict]) -> List[dict]:
    by_key: Dict[Tuple[str, str], dict] = {}
    for f in findings:
        key = (f["riskRuleId"], f["module"])
        if key not in by_key:
            by_key[key] = f
            continue
        kept = by_key[key]
        seen = {(l["file"], l["startLine"]) for l in kept["codeLocations"]}
        for loc in f["codeLocations"]:
            if (loc["file"], loc["startLine"]) not in seen:
                kept["codeLocations"].append(loc)
                seen.add((loc["file"], loc["startLine"]))
        kept["callSiteCount"] += f["callSiteCount"]
        for field in ("evidence", "remediation"):
            for b in f[field]:
                if b not in kept[field] and len(kept[field]) < MAX_BULLETS:
                    kept[field].append(b)
    for f in by_key.values():
        f["codeLocations"] = f["codeLocations"][:MAX_CODE_LOCATIONS]
        f["callSiteCount"] = max(f["callSiteCount"], len(f["codeLocations"]))
    return list(by_key.values())


def rank_key(rules: Dict[str, dict]):
    def key(f: dict):
        severity = SEVERITY_ORDER.get(rules[f["riskRuleId"]].get("severity"), 0)
        return (-severity, -f["callSiteCount"], f["riskRuleId"])
    return key


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--rules", required=True, help="chaos_risk_rule list response saved as JSON")
    parser.add_argument("--findings", required=True, help="drafted findings JSON (list or {findings: [...]})")
    parser.add_argument("--commit", default="HEAD", help="commit the evidence must match (default HEAD)")
    parser.add_argument("--max-per-module", type=int, default=8)
    parser.add_argument("--out", default="-")
    args = parser.parse_args(argv)

    commit = git(args.repo, "rev-parse", args.commit).strip()
    rules = rules_by_identity(load_json(args.rules))
    drafts = unwrap_list(load_json(args.findings), "findings", "valid")
    files = FileCache(args.repo, commit)

    valid, dropped = [], []
    for i, draft in enumerate(drafts):
        rule_id = draft.get("riskRuleId") if isinstance(draft, dict) else None
        if not isinstance(draft, dict):
            dropped.append({"index": i, "riskRuleId": None, "reason": "finding is not an object"})
            continue
        ok, reason = validate_one(dict(draft), rules, files)
        if ok:
            valid.append(ok)
            if reason:
                dropped.append({"index": i, "riskRuleId": rule_id, "reason": "some locations dropped: " + reason})
        else:
            dropped.append({"index": i, "riskRuleId": rule_id, "reason": reason})

    merged = sorted(merge(valid), key=rank_key(rules))
    per_module: Dict[str, int] = {}
    capped = []
    over_cap = 0
    for f in merged:
        n = per_module.get(f["module"], 0)
        if n >= args.max_per_module or len(capped) >= MAX_FINDINGS:
            over_cap += 1
            dropped.append({"index": None, "riskRuleId": f["riskRuleId"],
                            "reason": "over the cap for module {}".format(f["module"])})
            continue
        per_module[f["module"]] = n + 1
        capped.append(f)

    stats = {
        "drafted": len(drafts),
        "rejected": len(drafts) - len(valid),
        "merged": len(valid) - len(merged),
        "overCap": over_cap,
        "valid": len(capped),
    }
    write_json(args.out, {"commitSHA": commit, "valid": capped, "dropped": dropped, "stats": stats})
    print(", ".join("{} {}".format(v, k) for k, v in stats.items()), file=sys.stderr)
    return 0 if capped or not drafts else 1


if __name__ == "__main__":
    sys.exit(main())
