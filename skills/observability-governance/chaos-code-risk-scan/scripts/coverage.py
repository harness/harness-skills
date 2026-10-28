#!/usr/bin/env python3
"""Fail when an actionable inventory fact is neither reported nor explicitly cleared.

Two scans of the same commit must agree. The inventory is deterministic, so every
fact that signals a risk has to end the run in exactly one of two states:

  * covered   - a validated finding exists for the same (module, rule), or
  * cleared   - dispositions.json names the fact and cites the mitigation that
                makes it a non-finding (a file and line that exist at the commit).

Anything else is "uncovered" and the script exits 1. "Low impact", "just a
notifier" and "not verified" are not accepted reasons; verify the code or report it.

Actionable facts (see FACT_RULES):
  outbound_client   timeout is none or unknown       -> code-outbound-call-without-timeout
  retry_construct   backoff is none/constant, or the attempt cap is not bounded
                                                     -> code-retry-without-backoff
  health_endpoint   every fact                       -> code-health-check-masks-dependency-state
  serving_entrypoint every fact                      -> code-missing-graceful-shutdown
  local_state       every fact                       -> code-local-state-assumption

dispositions.json:
  {"dispositions": [
     {"module": "subscriber", "file": "subscriber/pkg/common/restCall.go", "startLine": 61,
      "kind": "outbound_client", "reason": "shared_factory_timeout",
      "mitigation": {"file": "subscriber/pkg/common/restCall.go", "line": 70},
      "note": "client.Timeout is set to 40s right after construction"}
  ]}

Usage: coverage.py --repo PATH --inventory INV.json --findings VALID.json
                   [--dispositions DISP.json] [--commit SHA] [--out FILE]
"""

import argparse
import sys
from typing import Dict, List, Optional, Tuple

from _common import git_or_none, load_json, normalize_module, unwrap_list, write_json

KIND_RULE = {
    "outbound_client": "code-outbound-call-without-timeout",
    "retry_construct": "code-retry-without-backoff",
    "health_endpoint": "code-health-check-masks-dependency-state",
    "serving_entrypoint": "code-missing-graceful-shutdown",
    "local_state": "code-local-state-assumption",
}

# A disposition must name a mitigation, never an opinion about importance.
ALLOWED_REASONS = {
    "shared_factory_timeout",     # client or factory sets a timeout
    "context_deadline",           # call site passes a context with a deadline
    "mesh_timeout",               # destination timeout configured in repo
    "resilience_library",         # backoff/breaker library wraps the call
    "bounded_backoff",            # exponential backoff with jitter and a cap
    "graceful_shutdown_present",  # Shutdown/Stop is called on SIGTERM
    "health_check_correct",       # readiness returns non-2xx when the dependency is down
    "external_store",             # state lives in a DB, cache or object store
    "not_serving_path",           # startup-only, CLI, or one-shot job; cite the main/entry line
    "suppressed",                 # harness-chaos-ignore comment at the location
    "pattern_absent",             # the match is not the risk (e.g. an import used only to parse); cite the real usage
}


def actionable(fact: dict) -> bool:
    kind = fact.get("kind")
    attrs = fact.get("attrs") or {}
    if kind == "outbound_client":
        return attrs.get("timeout") in ("none", "unknown")
    if kind == "retry_construct":
        return attrs.get("backoff") in ("none", "constant") or attrs.get("attempt_cap") not in ("bounded",)
    return kind in KIND_RULE


def fact_key(module: str, file: str, line: int, kind: str) -> Tuple[str, str, int, str]:
    return (normalize_module(module), file, int(line), kind)


def mitigation_exists(repo: str, commit: str, mitigation: Optional[dict]) -> bool:
    if not isinstance(mitigation, dict):
        return False
    path, line = mitigation.get("file"), mitigation.get("line")
    if not path or not isinstance(line, int) or line < 1:
        return False
    text = git_or_none(repo, "show", "{}:{}".format(commit, path))
    return text is not None and line <= len(text.splitlines())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--findings", required=True, help="validated findings from validate_evidence.py")
    parser.add_argument("--dispositions", help="dispositions.json for facts that are not findings")
    parser.add_argument("--commit", help="defaults to the commit recorded in the inventory")
    parser.add_argument("--out", default="-")
    args = parser.parse_args()

    inventory = load_json(args.inventory)
    commit = args.commit or inventory["repo"]["commitSHA"]
    findings = unwrap_list(load_json(args.findings), "findings", "valid")
    dispositions = unwrap_list(load_json(args.dispositions), "dispositions") if args.dispositions else []

    reported = {(normalize_module(f.get("module")), f.get("riskRuleId")) for f in findings}
    cleared: Dict[Tuple[str, str, int, str], dict] = {}
    problems: List[str] = []
    for d in dispositions:
        key = fact_key(d.get("module", "."), d.get("file", ""), d.get("startLine", 0), d.get("kind", ""))
        if d.get("reason") not in ALLOWED_REASONS:
            problems.append("{}:{} reason '{}' is not an allowed mitigation".format(key[1], key[2], d.get("reason")))
        elif not mitigation_exists(args.repo, commit, d.get("mitigation")):
            problems.append("{}:{} cites no mitigation file/line that exists at {}".format(key[1], key[2], commit[:8]))
        else:
            cleared[key] = d

    covered, clear, uncovered = [], [], []
    for fact in inventory.get("facts", []):
        if not actionable(fact):
            continue
        key = fact_key(fact["module"], fact["file"], fact["startLine"], fact["kind"])
        rule = KIND_RULE[fact["kind"]]
        item = {"module": key[0], "file": key[1], "startLine": key[2], "kind": key[3], "rule": rule}
        if (key[0], rule) in reported:
            covered.append(item)
        elif key in cleared:
            clear.append(dict(item, reason=cleared[key]["reason"]))
        else:
            uncovered.append(item)

    report = {
        "summary": {"actionable": len(covered) + len(clear) + len(uncovered), "covered": len(covered),
                    "cleared": len(clear), "uncovered": len(uncovered), "badDispositions": len(problems)},
        "uncovered": uncovered,
        "badDispositions": problems,
        "cleared": clear,
    }
    write_json(args.out, report)
    s = report["summary"]
    print("coverage: {actionable} actionable facts, {covered} covered, {cleared} cleared, "
          "{uncovered} uncovered, {badDispositions} bad dispositions".format(**s), file=sys.stderr)
    return 1 if uncovered or problems else 0


if __name__ == "__main__":
    sys.exit(main())
