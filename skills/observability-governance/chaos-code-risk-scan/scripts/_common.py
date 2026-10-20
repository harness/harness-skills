"""Helpers shared by the chaos-code-risk-scan scripts. Standard library only."""

import json
import os
import re
import subprocess
import sys
from typing import Dict, Iterable, List, Optional

# Mirrors the server's chaos fault allowlist; the server rejects anything else.
KNOWN_CHAOS_FAULTS = [
    "pod-delete", "pod-cpu-hog", "pod-memory-hog",
    "pod-network-latency", "pod-network-loss", "pod-network-corruption", "pod-network-duplication",
    "pod-dns-error", "pod-dns-spoof",
    "pod-http-latency", "pod-http-status-code", "pod-http-modify-body", "pod-http-modify-header",
    "pod-http-reset-peer",
    "pod-io-stress", "pod-autoscaler",
    "node-drain", "node-cpu-hog", "node-memory-hog", "node-io-stress", "node-restart", "node-taint",
    "container-kill", "disk-fill",
    "jvm-cpu-hog", "jvm-memory-hog", "jvm-method-latency",
]
_FAULTS_BY_LENGTH = sorted(KNOWN_CHAOS_FAULTS, key=len, reverse=True)

# Server-side limits on submitted findings.
MAX_FINDINGS = 100
MAX_CODE_LOCATIONS = 5
MAX_SNIPPET = 2000
MAX_NAME = 200
MAX_TEXT = 2000
MAX_BULLETS = 10
MAX_BULLET = 1000
MAX_PATH = 512
SEVERITY_ORDER = {"Critical": 4, "High": 3, "Medium": 2, "Low": 1}

SUPPRESSION_RE = re.compile(r"harness-chaos-ignore:\s*(code-[a-z0-9-]{3,60})\s+\S")

_EXCLUDED_DIR_PARTS = {
    "test", "tests", "__tests__", "testdata", "testing", "e2e", "it",
    "vendor", "node_modules", "third_party",
    "example", "examples", "sample", "samples", "demo", "docs",
    "mock", "mocks", "fixtures", "generated",
    "dist", "build", "target", ".git", ".venv", "venv", "site-packages",
    "scripts", "hack", "benchmark", "benchmarks",
}
_EXCLUDED_FILE_RE = re.compile(
    r"(_test\.go|\.pb\.go|_pb2(_grpc)?\.py|\.gen\.go|_generated\.\w+|"
    r"\.(test|spec)\.(js|jsx|ts|tsx|mjs|cjs)|Test\.java|Tests\.java|IT\.java|"
    r"^test_.*\.py|.*_test\.py|conftest\.py|\.min\.js|\.d\.ts)$"
)


def is_excluded(path: str) -> bool:
    """Test, example, vendor, generated, build and tooling code never yields findings."""
    parts = path.split("/")
    if any(p.lower() in _EXCLUDED_DIR_PARTS for p in parts[:-1]):
        return True
    return bool(_EXCLUDED_FILE_RE.search(parts[-1]))


def is_safe_relative_path(p: str) -> bool:
    if not p or len(p) > MAX_PATH:
        return False
    if p.startswith("/") or "\\" in p or ":" in p:
        return False
    return all(seg not in ("", "..") for seg in p.split("/"))


def normalize_module(module: Optional[str]) -> str:
    module = (module or "").strip()
    if module.startswith("./"):
        module = module[2:]
    module = module.rstrip("/")
    return module or "."


def parse_fault_names(sentences: Iterable[str]) -> List[str]:
    """Same matching as the server: whole tokens, longest fault name first."""
    seen = set()
    out = []
    for sentence in sentences:
        for fault in _faults_in_sentence(sentence.lower()):
            if fault not in seen:
                seen.add(fault)
                out.append(fault)
    return out


def _is_boundary(s: str, i: int) -> bool:
    if i < 0 or i >= len(s):
        return True
    c = s[i]
    return not (c.isascii() and (c.isalnum() or c in "-_"))


def _faults_in_sentence(sentence: str) -> List[str]:
    claimed = [False] * len(sentence)
    matches = []
    for fault in _FAULTS_BY_LENGTH:
        offset = 0
        while True:
            idx = sentence.find(fault, offset)
            if idx < 0:
                break
            end = idx + len(fault)
            offset = idx + 1
            if not _is_boundary(sentence, idx - 1) or not _is_boundary(sentence, end):
                continue
            if any(claimed[idx:end]):
                continue
            for i in range(idx, end):
                claimed[i] = True
            matches.append((idx, fault))
    return [f for _, f in sorted(matches)]


def git(repo: str, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", repo] + list(args),
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True,
    )
    return result.stdout


def git_or_none(repo: str, *args: str) -> Optional[str]:
    try:
        return git(repo, *args).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def normalize_repo_url(url: Optional[str]) -> Optional[str]:
    """Return host/org/repo with no scheme, credentials or .git suffix."""
    if not url:
        return None
    url = url.strip()
    m = re.match(r"^[\w.-]+@([^:]+):(.+)$", url)
    if m:
        host, path = m.group(1), m.group(2)
    else:
        url = re.sub(r"^[a-z][a-z0-9+.-]*://", "", url)
        url = url.split("@", 1)[-1]
        host, _, path = url.partition("/")
        host = host.split(":", 1)[0]
    path = path.strip("/")
    if path.endswith(".git"):
        path = path[:-4]
    return "{}/{}".format(host.lower(), path) if path else host.lower()


def load_json(path: str):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: str, data) -> None:
    if path == "-":
        json.dump(data, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def unwrap_list(data, *keys: str) -> list:
    """Accept a bare list or an object wrapping it under one of keys."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = unwrap_list(value, *keys)
                if nested:
                    return nested
    return []


def rules_by_identity(raw) -> Dict[str, dict]:
    rules = {}
    for rule in unwrap_list(raw, "data", "items", "riskRules", "rules", "content"):
        if isinstance(rule, dict) and rule.get("identity"):
            rules[rule["identity"]] = rule
    return rules


def rule_data_sources(rule: dict) -> List[str]:
    ds = (rule.get("spec") or {}).get("dataSource") or []
    return [ds] if isinstance(ds, str) else list(ds)


def rule_faults(rule: dict) -> List[str]:
    return list((rule.get("spec") or {}).get("faults") or [])
