#!/usr/bin/env python3
"""Extract resilience facts from a git repository.

Each fact is a candidate signal with a verbatim file:line snippet: outbound
clients and their timeout state, retry loops and their backoff, serving
entrypoints, shutdown handling, health endpoints, unbounded pools and queues,
local state, resilience libraries and suppression comments. Facts are not
findings; the agent decides which facts violate a rule.

Usage: inventory.py --repo PATH [--out FILE] [--max-per-kind N] [--since COMMIT]

--since limits facts to files changed between COMMIT and HEAD. COMMIT must be
an ancestor of HEAD. When it is HEAD, the inventory is empty (scanMode
unchanged). When it is missing or not an ancestor, the whole tree is scanned.
"""

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from _common import (
    SUPPRESSION_RE, git, git_or_none, is_excluded, normalize_repo_url, write_json,
)

MAX_FILE_BYTES = 1_000_000
SNIPPET_MAX_LINES = 3

LANG_BY_EXT = {
    ".go": "go",
    ".java": "java", ".kt": "java",
    ".py": "python",
    ".js": "node", ".mjs": "node", ".cjs": "node", ".ts": "node",
}
CONFIG_NAMES = re.compile(r"(^|/)(application[-\w]*\.(ya?ml|properties)|java\.security)$")
MODULE_MARKERS = {
    "go.mod": "go", "pom.xml": "java", "build.gradle": "java", "build.gradle.kts": "java",
    "package.json": "node", "pyproject.toml": "python", "setup.py": "python",
    "requirements.txt": "python", "Pipfile": "python",
}
FRONTEND_DEPS = ("react", "vue", "@angular/core", "svelte")
NODE_SERVER_DEPS = ("express", "fastify", "koa", "@nestjs/core", "@hapi/hapi", "restify", "hono")

COMMENT_RE = re.compile(r"^\s*(//|#|\*|/\*)")
TIMEOUT_RE = re.compile(
    r"(?i)(timeout|deadline|withtimeout|withdeadline|abortsignal|\bsignal\s*:|setconnecttimeout|setreadtimeout|"
    r"responsetimeout|calltimeout|connecttimeout|readtimeout)"
)
SLEEP_RE = re.compile(r"(time\.Sleep|Thread\.sleep|TimeUnit\.\w+\.sleep|time\.sleep|asyncio\.sleep|setTimeout|await\s+sleep|\bdelay\()")
BACKOFF_RE = re.compile(r"(?i)(backoff|exponential|jitter|\*\s*2\b|<<|math\.pow|Math\.pow|\*\*\s*\w)")
DEPENDENCY_CALL_RE = re.compile(r"(?i)(\.ping\(|pingcontext|\bdb\.|redis|\.query|\.exec|sql|mongo|kafka|http\.get|fetch\(|requests\.|\.check\()")
STATIC_OK_RE = re.compile(r"(?i)(statusok|\b200\b|\"ok\"|'ok'|\"up\"|'up'|ok\(\))")
# A signal or context passed in by the caller may carry a deadline we cannot see.
CALLER_SIGNAL_RE = re.compile(r"\bsignal\b|\bctx\b|\bcontext\b")
_DECL_PREFIX = r"^\s*(?:(?:export|public|private|protected|static|async|override|function)\s+)*\w+\s*"
DECLARATION_RE = re.compile(
    _DECL_PREFIX + r"\([^)]*\)\s*(:[^={]+)?\{\s*$"
    + r"|" + _DECL_PREFIX + r"\(\s*\w+\??\s*:\s*\w"
    + r"|^\s*(async\s+)?def\s"
)
ROUTE_CONTEXT_RE = re.compile(
    r"\.(get|route|handle|handlefunc|any|add_api_route|api_route|use)\s*\(|@(get|request)mapping|"
    r"@(app|router|bp|blueprint)\.(get|route)|^\s*\w+\s*(=|:=)\s*[\"'`]",
    re.I,
)
HEALTH_PATH_RE = re.compile(r"[\"'`](/(?:actuator/)?(?:health[z]?|livez?|readyz?|liveness|readiness|ping|status))(?:/[\w-]*)?[\"'`]")


def statement_extent(lines: List[str], i: int, max_lines: int = 25) -> str:
    """Return text from line i until its brackets balance, capped at max_lines."""
    depth = 0
    seen_open = False
    out = []
    for j in range(i, min(len(lines), i + max_lines)):
        out.append(lines[j])
        for ch in lines[j]:
            if ch in "({[":
                depth += 1
                seen_open = True
            elif ch in ")}]":
                depth -= 1
        if seen_open and depth <= 0:
            break
    return "\n".join(out)


def window(lines: List[str], i: int, before: int, after: int) -> str:
    return "\n".join(lines[max(0, i - before): min(len(lines), i + after + 1)])


# Attribute builders return a dict of attributes, or None to drop the match.
AttrFn = Callable[[List[str], int, re.Match, "FileContext"], Optional[Dict[str, str]]]


class FileContext:
    def __init__(self, text: str):
        self.text = text
        self.has_context_deadline = bool(re.search(r"context\.With(Timeout|Deadline)", text))
        self.has_max_bytes = bool(re.search(r"MaxBytesReader|LimitReader|maxContentLength|limit\s*:", text))
        self.has_session_store = bool(re.search(r"(?i)store\s*:|RedisStore|MongoStore|connect-redis", text))
        self.has_scheduler_lock = bool(re.search(r"@SchedulerLock|ShedLock|redlock|advisory_lock|LeaderElect", text))


def timeout_state(text: str) -> str:
    if TIMEOUT_RE.search(text):
        return "present"
    if CALLER_SIGNAL_RE.search(text):
        return "unknown"
    return "none"


def timeout_of_statement(lines, i, _m, _ctx):
    if DECLARATION_RE.match(lines[i]):
        return None
    return {"timeout": timeout_state(statement_extent(lines, i))}


def timeout_of_builder(lines, i, _m, _ctx):
    text = statement_extent(lines, i) + "\n" + window(lines, i, 2, 12)
    return {"timeout": timeout_state(text)}


def go_http_client_literal(lines, i, _m, _ctx):
    text = statement_extent(lines, i, 30)
    return {"timeout": "present" if re.search(r"\bTimeout\s*:", text) else "none"}


def go_default_client(_lines, _i, _m, ctx):
    return {"timeout": "none", "note": "http.DefaultClient has no timeout",
            "context_deadline_in_file": str(ctx.has_context_deadline).lower()}


def unknown_timeout(_lines, _i, _m, _ctx):
    return {"timeout": "unknown"}


def retry_loop(lines, i, m, _ctx):
    body = window(lines, i, 0, 20)
    if BACKOFF_RE.search(body):
        backoff = "exponential"
    elif SLEEP_RE.search(body):
        backoff = "constant"
    else:
        backoff = "none"
    header = lines[i]
    bounded = bool(re.search(r"<|<=|range\(|\bin\s+\w|\.times|until", header))
    return {"backoff": backoff, "attempt_cap": "bounded" if bounded else "unbounded"}


def health_endpoint(lines, i, m, _ctx):
    if not ROUTE_CONTEXT_RE.search(lines[i]):
        return None
    path = m.group(1)
    registration = "constant" if re.match(r"^\s*\w+\s*(=|:=)\s*[\"'`]", lines[i]) else "route"
    body = window(lines, i, 0, 10)
    if DEPENDENCY_CALL_RE.search(body):
        behaviour = "calls_dependency"
    elif STATIC_OK_RE.search(body):
        behaviour = "static_ok"
    else:
        behaviour = "unknown"
    lower = path.lower()
    if "live" in lower:
        probe = "liveness"
    elif "ready" in lower:
        probe = "readiness"
    else:
        probe = "ambiguous"
    if registration == "constant":
        behaviour = "unknown"
    return {"path": path, "registration": registration, "behaviour": behaviour, "probe": probe}


def read_all_body(_lines, _i, _m, ctx):
    if ctx.has_max_bytes:
        return None
    return {"bound": "none", "what": "request body read fully without a size limit"}


def unbounded(what: str) -> AttrFn:
    def fn(_lines, _i, _m, _ctx):
        return {"bound": "none", "what": what}
    return fn


def cache_builder(lines, i, _m, _ctx):
    text = statement_extent(lines, i) + "\n" + window(lines, i, 0, 8)
    if re.search(r"maximumSize|maximumWeight|expireAfter|maxsize=\d|max_size|ttl", text):
        return None
    return {"bound": "none", "what": "cache without size limit or expiry"}


def local_file_write(lines, i, _m, _ctx):
    text = window(lines, i, 1, 1)
    if re.search(r"(?i)(tmp|temp|tempfile|mkstemp|TempDir|os\.TempDir|/dev/)", text):
        return None
    return {"state": "local_disk_write"}


def memory_session(lines, i, _m, ctx):
    if ctx.has_session_store:
        return None
    return {"state": "in_memory_session"}


def in_process_scheduler(_lines, _i, _m, ctx):
    if ctx.has_scheduler_lock:
        return None
    return {"state": "in_process_scheduler"}


def plain(**attrs) -> AttrFn:
    def fn(_lines, _i, _m, _ctx):
        return dict(attrs)
    return fn


# (kind, languages, pattern, attribute builder)
PATTERNS: List[Tuple[str, Tuple[str, ...], re.Pattern, AttrFn]] = [
    # Outbound clients
    ("outbound_client", ("go",), re.compile(r"\bhttp\.DefaultClient\b"), go_default_client),
    ("outbound_client", ("go",), re.compile(r"\bhttp\.(Get|Post|Head|PostForm)\("), go_default_client),
    ("outbound_client", ("go",), re.compile(r"(?<![\w*.])&?http\.Client\s*\{"), go_http_client_literal),
    ("outbound_client", ("go",), re.compile(r"\bgrpc\.(Dial|DialContext|NewClient)\("), unknown_timeout),
    ("outbound_client", ("java",), re.compile(r"new\s+RestTemplate\s*\(|RestTemplateBuilder\(\)"), timeout_of_builder),
    ("outbound_client", ("java",), re.compile(r"WebClient\.(create|builder)\("), timeout_of_builder),
    ("outbound_client", ("java",), re.compile(r"new\s+OkHttpClient\s*(\.Builder)?\s*\("), timeout_of_builder),
    ("outbound_client", ("java",), re.compile(r"HttpClients\.(createDefault|custom|createSystem)\("), timeout_of_builder),
    ("outbound_client", ("java",), re.compile(r"HttpClient\.(newBuilder|newHttpClient)\("), timeout_of_builder),
    ("outbound_client", ("java",), re.compile(r"@FeignClient\b"), unknown_timeout),
    ("outbound_client", ("python",), re.compile(r"\b(requests|httpx)\.(get|post|put|delete|patch|head|request)\("), timeout_of_statement),
    ("outbound_client", ("python",), re.compile(r"\bhttpx\.(Client|AsyncClient)\("), timeout_of_statement),
    ("outbound_client", ("python",), re.compile(r"\baiohttp\.ClientSession\("), timeout_of_statement),
    ("outbound_client", ("python",), re.compile(r"\burllib\.request\.urlopen\("), timeout_of_statement),
    ("outbound_client", ("python",), re.compile(r"\brequests\.Session\(\)"), unknown_timeout),
    ("outbound_client", ("node",), re.compile(r"(?<![\w.])fetch\(\s*[^)]"), timeout_of_statement),
    ("outbound_client", ("node",), re.compile(r"\baxios\.(get|post|put|delete|patch|request)\("), timeout_of_statement),
    ("outbound_client", ("node",), re.compile(r"\baxios\.create\("), timeout_of_statement),
    ("outbound_client", ("node",), re.compile(r"\bgot(\.(get|post|put|delete|patch))?\(\s*[^)]"), timeout_of_statement),
    ("outbound_client", ("node",), re.compile(r"\bhttps?\.(request|get)\("), timeout_of_statement),
    # Retry constructs
    ("retry_construct", ("go", "java", "python", "node"),
     re.compile(r"^\s*(for|while)\b.*\b(retr(y|ies)|attempts?|tries)\b", re.I), retry_loop),
    ("retry_construct", ("java",), re.compile(r"@Retryable\b|RetryTemplate"), plain(library="spring-retry")),
    ("retry_construct", ("python",), re.compile(r"@retry\b|@backoff\.on_exception"), plain(library="decorator")),
    # Resilience libraries (mitigations)
    ("resilience_library", ("go",), re.compile(r"\"(github\.com/(cenkalti/backoff|sony/gobreaker|afex/hystrix-go|avast/retry-go|failsafe-go)[^\"]*)\""), plain()),
    ("resilience_library", ("java",), re.compile(r"\bimport\s+(io\.github\.resilience4j|com\.netflix\.hystrix|dev\.failsafe|net\.jodah\.failsafe|org\.springframework\.retry)"), plain()),
    ("resilience_library", ("java",), re.compile(r"@(CircuitBreaker|Bulkhead|RateLimiter|TimeLimiter)\b"), plain()),
    ("resilience_library", ("python",), re.compile(r"^\s*(from|import)\s+(tenacity|backoff|pybreaker|circuitbreaker|stamina)\b"), plain()),
    ("resilience_library", ("node",), re.compile(r"(require\(|from\s+)['\"](opossum|cockatiel|p-retry|async-retry|axios-retry|got)['\"]"), plain()),
    # Serving entrypoints and shutdown
    ("serving_entrypoint", ("go",), re.compile(r"\.ListenAndServe(TLS)?\(|\bgrpc\.NewServer\("), plain()),
    ("serving_entrypoint", ("java",), re.compile(r"SpringApplication\.run\(|HttpServer\.create\("), plain()),
    ("serving_entrypoint", ("python",), re.compile(r"\buvicorn\.run\(|\bapp\.run\(|serve_forever\(|\bFastAPI\(|\bFlask\("), plain()),
    ("serving_entrypoint", ("node",), re.compile(r"\.listen\(\s*[\w.]+|NestFactory\.create\("), plain()),
    ("signal_handler", ("go",), re.compile(r"signal\.Notify(Context)?\(|\.Shutdown\(|\.GracefulStop\("), plain()),
    ("signal_handler", ("java",), re.compile(r"addShutdownHook\(|@PreDestroy\b"), plain()),
    ("signal_handler", ("python",), re.compile(r"signal\.signal\(\s*signal\.SIGTERM|add_signal_handler\(|on_event\(\s*[\"']shutdown|lifespan\s*="), plain()),
    ("signal_handler", ("node",), re.compile(r"process\.on\(\s*[\"']SIGTERM|enableShutdownHooks\(|http-terminator|stoppable|@godaddy/terminus"), plain()),
    # Health endpoints
    ("health_endpoint", ("go", "java", "python", "node"), HEALTH_PATH_RE, health_endpoint),
    # Unbounded pools, queues and reads
    ("pool_or_queue", ("go",), re.compile(r"\b(io|ioutil)\.ReadAll\(\s*(r|req|request|c\.Request|ctx\.Request)\.Body\)"), read_all_body),
    ("pool_or_queue", ("java",), re.compile(r"Executors\.newCachedThreadPool\("), unbounded("thread pool that grows without limit")),
    ("pool_or_queue", ("java",), re.compile(r"new\s+LinkedBlockingQueue<[^>]*>\(\s*\)"), unbounded("queue without capacity")),
    ("pool_or_queue", ("java",), re.compile(r"CacheBuilder\.newBuilder\(|Caffeine\.newBuilder\("), cache_builder),
    ("pool_or_queue", ("python",), re.compile(r"\b(queue\.Queue|asyncio\.Queue)\(\s*\)"), unbounded("queue without maxsize")),
    ("pool_or_queue", ("python",), re.compile(r"@(functools\.)?lru_cache\(\s*maxsize\s*=\s*None|@(functools\.)?cache\b"), unbounded("cache without size limit")),
    # Local state
    ("local_state", ("go",), re.compile(r"\bos\.(Create|WriteFile|OpenFile)\(|ioutil\.WriteFile\("), local_file_write),
    ("local_state", ("java",), re.compile(r"new\s+FileOutputStream\(|Files\.write\(|new\s+FileWriter\("), local_file_write),
    ("local_state", ("java",), re.compile(r"@Scheduled\b"), in_process_scheduler),
    ("local_state", ("python",), re.compile(r"\bopen\([^)]*[\"'][wa]b?\+?[\"']"), local_file_write),
    ("local_state", ("python",), re.compile(r"BackgroundScheduler\(|\bschedule\.every\("), in_process_scheduler),
    ("local_state", ("node",), re.compile(r"\bfs\.(writeFile|writeFileSync|appendFile|appendFileSync|createWriteStream)\("), local_file_write),
    ("local_state", ("node",), re.compile(r"(require\(|from\s+)['\"]express-session['\"]"), memory_session),
    ("local_state", ("node",), re.compile(r"(require\(|from\s+)['\"]node-cron['\"]|cron\.schedule\("), in_process_scheduler),
    ("local_state", ("go",), re.compile(r"\"github\.com/robfig/cron"), in_process_scheduler),
]

CONFIG_PATTERNS = [
    ("signal_handler", re.compile(r"server\.shutdown\s*[:=]\s*graceful"), {"source": "spring config"}),
    ("dns_cache", re.compile(r"networkaddress\.cache\.ttl\s*=\s*-1"), {"ttl": "forever"}),
    ("health_endpoint", re.compile(r"management\.endpoint\.health|management\.endpoints\.web"), {"source": "spring actuator"}),
]


def list_files(repo: str) -> List[str]:
    out = git(repo, "ls-files", "-z")
    return [p for p in out.split("\0") if p]


def diff_paths(repo: str, since: str, head: str) -> Optional[List[str]]:
    """Paths changed since an ancestor commit.

    None means the baseline cannot bound a diff, so the caller scans every
    file. An empty list means HEAD is that commit and nothing changed.
    """
    since = (since or "").strip()
    if not since:
        return None
    old = git_or_none(repo, "rev-parse", "--verify", "{}^{{commit}}".format(since))
    if not old:
        return None
    if old == head:
        return []
    if git_or_none(repo, "merge-base", "--is-ancestor", old, head) is None:
        return None
    out = git(repo, "diff", "--name-only", "--diff-filter=ACMR", "-z", old, head)
    return [p for p in out.split("\0") if p]


def detect_modules(files: List[str], repo: str) -> Dict[str, dict]:
    modules: Dict[str, dict] = {}
    for path in files:
        name = os.path.basename(path)
        if name not in MODULE_MARKERS or is_excluded(path):
            continue
        mod = os.path.dirname(path) or "."
        entry = modules.setdefault(mod, {"path": mod, "languages": set(), "markers": [], "frontend": False})
        entry["languages"].add(MODULE_MARKERS[name])
        entry["markers"].append(name)
        if name == "package.json":
            entry["frontend"] = is_frontend_package(os.path.join(repo, path))
    if "." not in modules:
        modules["."] = {"path": ".", "languages": set(), "markers": [], "frontend": False}
    return modules


def is_frontend_package(path: str) -> bool:
    try:
        with open(path, encoding="utf-8") as f:
            pkg = json.load(f)
    except (OSError, ValueError):
        return False
    deps = {}
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        deps.update(pkg.get(key) or {})
    has_frontend = any(d in deps for d in FRONTEND_DEPS)
    has_server = any(d in deps for d in NODE_SERVER_DEPS)
    return has_frontend and not has_server


def module_for(path: str, module_paths: List[str]) -> str:
    best = "."
    for mod in module_paths:
        if mod == ".":
            continue
        if path == mod or path.startswith(mod + "/"):
            if len(mod) > len(best) or best == ".":
                best = mod
    return best


def snippet_at(lines: List[str], i: int) -> Tuple[int, int, str]:
    end = i
    while end + 1 < len(lines) and end - i + 1 < SNIPPET_MAX_LINES and lines[end].rstrip().endswith((",", "(", "{", "\\", "+", "&&", "||")):
        end += 1
    return i + 1, end + 1, "\n".join(lines[i:end + 1]).strip()


def scan_file(path: str, text: str, language: Optional[str], module: str) -> List[dict]:
    lines = text.splitlines()
    facts = []

    for i, line in enumerate(lines):
        m = SUPPRESSION_RE.search(line)
        if m:
            facts.append(fact("suppression", language or "any", module, path, i + 1, i + 1, line.strip(), {"rule": m.group(1)}))

    if language is None:
        for kind, pattern, attrs in CONFIG_PATTERNS:
            for i, line in enumerate(lines):
                if pattern.search(line):
                    facts.append(fact(kind, "config", module, path, i + 1, i + 1, line.strip(), dict(attrs)))
        return facts

    ctx = FileContext(text)
    for kind, langs, pattern, attr_fn in PATTERNS:
        if language not in langs:
            continue
        for i, line in enumerate(lines):
            if COMMENT_RE.match(line):
                continue
            m = pattern.search(line)
            if not m:
                continue
            attrs = attr_fn(lines, i, m, ctx)
            if attrs is None:
                continue
            start, end, snippet = snippet_at(lines, i)
            facts.append(fact(kind, language, module, path, start, end, snippet, attrs))
    return facts


def fact(kind, language, module, path, start, end, snippet, attrs) -> dict:
    return {
        "kind": kind, "language": language, "module": module,
        "file": path, "startLine": start, "endLine": end,
        "snippet": snippet[:2000], "attrs": attrs,
    }


def build_inventory(repo: str, max_per_kind: int, since: str = "") -> dict:
    repo = os.path.abspath(repo)
    if git_or_none(repo, "rev-parse", "--is-inside-work-tree") != "true":
        raise SystemExit("error: {} is not a git work tree".format(repo))

    commit = git(repo, "rev-parse", "HEAD").strip()
    branch = git_or_none(repo, "rev-parse", "--abbrev-ref", "HEAD")
    remote = git_or_none(repo, "remote", "get-url", "origin")
    dirty = bool(git_or_none(repo, "status", "--porcelain"))

    files = list_files(repo)
    changed = diff_paths(repo, since, commit)
    if changed is None:
        scan_mode = "full"
        scan_paths = files
        base_commit = None
    elif not changed:
        scan_mode = "unchanged"
        scan_paths = []
        base_commit = commit
    else:
        scan_mode = "diff"
        scan_paths = changed
        base_commit = git_or_none(repo, "rev-parse", "--verify", "{}^{{commit}}".format(since))
    modules = detect_modules(files, repo)
    module_paths = sorted(modules)

    facts: List[dict] = []
    scanned = 0
    for path in scan_paths:
        if is_excluded(path):
            continue
        ext = os.path.splitext(path)[1]
        language = LANG_BY_EXT.get(ext)
        is_config = bool(CONFIG_NAMES.search(path))
        if language is None and not is_config:
            continue
        module = module_for(path, module_paths)
        if language == "node" and modules.get(module, {}).get("frontend"):
            continue
        full = os.path.join(repo, path)
        try:
            if os.path.getsize(full) > MAX_FILE_BYTES:
                continue
            with open(full, encoding="utf-8", errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        scanned += 1
        facts.extend(scan_file(path, text, language if not is_config else None, module))

    grouped: Dict[Tuple[str, str], List[dict]] = defaultdict(list)
    for f in facts:
        grouped[(f["module"], f["kind"])].append(f)
    kept: List[dict] = []
    counts: Dict[str, Dict[str, int]] = defaultdict(dict)
    for (module, kind), items in sorted(grouped.items()):
        counts[module][kind] = len(items)
        kept.extend(items[:max_per_kind] if kind != "suppression" else items)

    return {
        "repo": {
            "root": repo,
            "repoURL": normalize_repo_url(remote),
            "branch": branch if branch != "HEAD" else None,
            "commitSHA": commit,
            "dirty": dirty,
            "scanMode": scan_mode,
            "baseCommit": base_commit,
        },
        "modules": [
            {"path": m["path"], "languages": sorted(m["languages"]), "markers": sorted(m["markers"]), "frontend": m["frontend"]}
            for m in (modules[p] for p in module_paths)
        ],
        "facts": kept,
        "counts": counts,
        "stats": {
            "filesTracked": len(files),
            "filesChanged": None if changed is None else len(changed),
            "filesScanned": scanned,
            "facts": len(facts),
            "factsKept": len(kept),
            "scanMode": scan_mode,
        },
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", required=True, help="path to the git repository")
    parser.add_argument("--out", default="-", help="output JSON file (default stdout)")
    parser.add_argument("--max-per-kind", type=int, default=40, help="facts kept per module and kind")
    parser.add_argument("--since", default="", help="ancestor commit; only files changed since then are scanned")
    args = parser.parse_args(argv)

    inventory = build_inventory(args.repo, args.max_per_kind, args.since)
    write_json(args.out, inventory)
    mode = inventory["repo"]["scanMode"]
    if args.since and mode == "full":
        print("warning: {} is not an ancestor of HEAD; scanning the whole tree".format(args.since), file=sys.stderr)
    if inventory["repo"]["dirty"]:
        print("warning: uncommitted changes; evidence is validated against HEAD {}".format(
            inventory["repo"]["commitSHA"][:12]), file=sys.stderr)
    stats = inventory["stats"]
    print("scanned {} files, {} facts ({} kept) across {} modules".format(
        stats["filesScanned"], stats["facts"], stats["factsKept"], len(inventory["modules"])), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
