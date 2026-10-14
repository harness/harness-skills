#!/usr/bin/env python3
"""Move skills/<name>/ into skills/<category>/<name>/ and rewrite Markdown
links/paths that depend on skill depth.

Usage: scripts/migrate_to_categories.py [--dry-run | --apply | --check | --repair]
                                         [--base REV] [--map NAME=CATEGORY ...]

  --dry-run   (default) print the planned moves and text rewrites, change nothing.
  --apply     perform the move on a flat tree: rewrite text, then git mv each
              skill directory into its category.
  --check     read-only: verify a categorized tree is correct (for CI).
  --repair    fix a categorized tree after a branch rebased across the move
              introduced new flat skill dirs or depth-stale links.
  --map NAME=CATEGORY   place a skill that is not in MOVE_MAP (repeatable).
                         Used by --repair for skills added on other branches.
  --base REV  base revision for --check's "no skill added/deleted" diff.

Run from anywhere; it always operates on the repo that contains this
scripts/ directory, never on the current working directory.

This script is temporary scaffolding for the skills/<category>/<name>/
migration. Delete it once the merge window has closed and every in-flight
branch has been rebased past the move.
"""
from __future__ import annotations

import argparse
import posixpath
import re
import subprocess
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))
import check_links  # noqa: E402

# Category directories, in display order.
CATEGORIES = (
    "pipelines",
    "infrastructure",
    "access-control",
    "fme",
    "database",
    "platform",
    "security",
    "observability-governance",
    "agents",
)

# skill -> category. Ordered to match the category list above.
MOVE_MAP: dict[str, str] = {
    # pipelines
    "create-pipeline": "pipelines",
    "create-pipeline-v1": "pipelines",
    "create-trigger": "pipelines",
    "create-template": "pipelines",
    "run-pipeline": "pipelines",
    "debug-pipeline": "pipelines",
    "migrate-pipeline": "pipelines",
    "manage-freeze-windows": "pipelines",
    # infrastructure
    "create-service": "infrastructure",
    "create-environment": "infrastructure",
    "create-infrastructure": "infrastructure",
    "create-connector": "infrastructure",
    "create-secret": "infrastructure",
    # access-control
    "manage-users": "access-control",
    "manage-roles": "access-control",
    # fme
    "discover-feature-flags": "fme",
    "explain-flag": "fme",
    "create-feature-flag": "fme",
    "instrument-feature-flag": "fme",
    "feature-flag-onboarding": "fme",
    "update-flag-targeting": "fme",
    "manage-flag-lifecycle": "fme",
    "manage-segments": "fme",
    "cleanup-feature-flags": "fme",
    "fme-pipeline": "fme",
    "create-experiment": "fme",
    "manage-experiments": "fme",
    "review-experiment-results": "fme",
    "choose-metric": "fme",
    "create-metric": "fme",
    "instrument-metric": "fme",
    # database
    "dbops-changeset": "database",
    # platform
    "manage-delegates": "platform",
    "manage-iacm": "platform",
    "manage-cde": "platform",
    "manage-artifacts": "platform",
    "create-sbom": "platform",
    "enforce-sbom": "platform",
    "manage-supply-chain": "platform",
    "manage-pull-requests": "platform",
    # security
    "configure-repo-scan": "security",
    "configure-secret-scan": "security",
    "configure-container-scan": "security",
    "generate-slsa": "security",
    "enforce-slsa": "security",
    "sign-artifact": "security",
    "verify-sign": "security",
    "configure-dast-scan": "security",
    "exempt-vuln": "security",
    "approve-exempt": "security",
    "configure-agent-pr-attestation": "security",
    # observability-governance
    "analyze-costs": "observability-governance",
    "security-report": "observability-governance",
    "dora-metrics": "observability-governance",
    "gitops-status": "observability-governance",
    "chaos-experiment": "observability-governance",
    "chaos-dr-test": "observability-governance",
    "scorecard-review": "observability-governance",
    "audit-report": "observability-governance",
    "template-usage": "observability-governance",
    "create-policy": "observability-governance",
    "manage-idp": "observability-governance",
    "manage-slos": "observability-governance",
    "sei-analytics": "observability-governance",
    "ai-operations": "observability-governance",
    "optimize-pipeline": "observability-governance",
    "deployment-readiness": "observability-governance",
    "incident-response": "observability-governance",
    "pr-analysis": "observability-governance",
    # agents
    "create-agent-template": "agents",
    "create-agent": "agents",
}

EXPECTED_SKILL_COUNT = 71

# Two links live inside fenced code blocks (copy-paste templates), so the
# generic link rewriter -- which skips fences, like check_links.iter_links --
# never sees them. Rewrite them by exact text match instead.
FIXED_REWRITES: dict[str, tuple[str, str]] = {
    "references/fme/tool-map.md": (
        "[tool-map.md](../../references/fme/tool-map.md)",
        "[tool-map.md](../../../references/fme/tool-map.md)",
    ),
    "skills/choose-metric/SKILL.md": (
        "](../../references/fme/metric-design.md#suggest-metrics-from-code)",
        "](../../../references/fme/metric-design.md#suggest-metrics-from-code)",
    ),
}


def abort(message: str, code: int = 2) -> None:
    print(f"error: {message}", file=sys.stderr)
    sys.exit(code)


def run_git(args: list[str], root: Path = REPO_ROOT, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=check)


# --------------------------------------------------------------------------
# Discovery
# --------------------------------------------------------------------------

def flat_skill_dirs(root: Path) -> list[str]:
    """Names of directories directly under skills/ that contain SKILL.md."""
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return []
    return sorted(
        p.name for p in skills_dir.iterdir() if p.is_dir() and (p / "SKILL.md").is_file()
    )


def categorized_skill_dirs(root: Path) -> list[tuple[str, str]]:
    """(category, name) pairs for skills already at skills/<cat>/<name>/."""
    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        return []
    out = []
    for cat_dir in sorted(p for p in skills_dir.iterdir() if p.is_dir()):
        if (cat_dir / "SKILL.md").is_file():
            continue  # flat skill dir, not a category
        for sub in sorted(p for p in cat_dir.iterdir() if p.is_dir()):
            if (sub / "SKILL.md").is_file():
                out.append((cat_dir.name, sub.name))
    return out


def iter_markdown_files(root: Path) -> list[str]:
    """Repo-relative posix paths of every tracked *.md / *.mdc file."""
    out = run_git(["ls-files", "-z", "--", "*.md", "*.mdc"], root=root).stdout
    return [name for name in out.split("\0") if name]


def depth_counts(root: Path) -> tuple[int, int]:
    """(count at skills/<name>/SKILL.md, count at skills/<cat>/<name>/SKILL.md)."""
    skills_dir = root / "skills"
    depth2 = depth3 = 0
    if not skills_dir.is_dir():
        return 0, 0
    for p in skills_dir.rglob("SKILL.md"):
        depth = len(p.relative_to(skills_dir).parts)
        if depth == 2:
            depth2 += 1
        elif depth == 3:
            depth3 += 1
    return depth2, depth3


# --------------------------------------------------------------------------
# Move map / --map handling
# --------------------------------------------------------------------------

def parse_map_args(pairs: list[str]) -> dict[str, str]:
    extra: dict[str, str] = {}
    for item in pairs:
        if "=" not in item:
            abort(f"invalid --map value (expected NAME=CATEGORY): {item}")
        name, _, cat = item.partition("=")
        if cat not in CATEGORIES:
            abort(f"--map {item}: category '{cat}' is not one of {', '.join(CATEGORIES)}")
        extra[name] = cat
    return extra


def build_full_map(map_args: list[str]) -> dict[str, str]:
    full_map = dict(MOVE_MAP)
    full_map.update(parse_map_args(map_args))
    return full_map


# --------------------------------------------------------------------------
# Path mapping
# --------------------------------------------------------------------------

def map_path(path: str, full_map: dict[str, str]) -> str:
    """Rewrite a repo-relative posix path's skills/<name> prefix, if any."""
    parts = path.split("/")
    if len(parts) >= 2 and parts[0] == "skills" and parts[1] in full_map:
        return "/".join(["skills", full_map[parts[1]], parts[1], *parts[2:]])
    return path


def split_dest(dest: str) -> tuple[str, str]:
    """Split a link destination into (path part, '#frag'/'?query' suffix)."""
    m = re.search(r"[#?]", dest)
    if m:
        return dest[: m.start()], dest[m.start() :]
    return dest, ""


def plain_path_regex(full_map: dict[str, str]) -> re.Pattern:
    """Match a plain-text "skills/<name>" mention for any name in full_map.

    Names are tried longest-first and the match is rejected if followed by
    another name character, so "create-pipeline" cannot match a prefix of
    "create-pipeline-v1". An already-categorized "skills/<cat>/<name>" is
    never matched: the segment right after "skills/" would be the category,
    and no category is also a skill name (enforced separately), so the
    alternation simply does not fire there.
    """
    names = sorted(full_map, key=len, reverse=True)
    alternation = "|".join(re.escape(n) for n in names)
    return re.compile(r"skills/(" + alternation + r")(?![A-Za-z0-9-])")


def apply_edits(line: str, edits: list[tuple[int, int, str]]) -> str:
    out = []
    pos = 0
    for start, end, text in sorted(edits, key=lambda e: e[0]):
        if start < pos:
            abort(f"overlapping edits on line {line!r}: edit at {start} overlaps previous edit ending at {pos}")
        out.append(line[pos:start])
        out.append(text)
        pos = end
    out.append(line[pos:])
    return "".join(out)


def is_angle_bracketed(line: str, start: int, end: int) -> bool:
    return line[start - 1 : start] == "<" and line[end : end + 1] == ">"


def apply_fixed_rewrites(old_path: str, text: str) -> tuple[str, bool]:
    pair = FIXED_REWRITES.get(old_path)
    if pair is None:
        return text, False
    old, new = pair
    count = text.count(old)
    if count == 1:
        return text.replace(old, new), True
    if count == 0 and text.count(new) == 1:
        return text, False  # already applied -- idempotent re-run (e.g. a dry run after the move)
    abort(f"{old_path}: expected exactly one occurrence of fixed rewrite target, found {count}")


# --------------------------------------------------------------------------
# Per-file rewrite (used by --apply, and by --repair for new flat dirs)
# --------------------------------------------------------------------------

def compute_file_rewrite(
    root: Path,
    old_path: str,
    full_map: dict[str, str],
    abort_angle_percent: list[tuple[str, int, str]],
    abort_missing: list[tuple[str, int, str]],
) -> tuple[str, str, list[tuple[str, int, str, str]], list[tuple[str, int, str, str]], bool]:
    """Rewrite one file assuming it currently lives at its OLD (pre-move) path.

    Returns (new_path, new_text, link_rewrites, plain_rewrites, fixed_applied).
    """
    text = (root / old_path).read_text(encoding="utf-8")
    text, fixed_applied = apply_fixed_rewrites(old_path, text)

    old_file_dir = posixpath.dirname(old_path)
    new_path = map_path(old_path, full_map)
    new_file_dir = posixpath.dirname(new_path)

    links_by_line: dict[int, list] = {}
    for link in check_links.iter_links(text):
        links_by_line.setdefault(link.line, []).append(link)

    regex = plain_path_regex(full_map)
    lines = text.split("\n")
    new_lines = []
    link_rewrites: list[tuple[str, int, str, str]] = []
    plain_rewrites: list[tuple[str, int, str, str]] = []

    for lineno, line in enumerate(lines, start=1):
        links = links_by_line.get(lineno, [])
        excluded = [(l.start, l.end) for l in links]
        edits: list[tuple[int, int, str]] = []

        for link in links:
            dest = link.dest
            if not dest or check_links.is_external(dest):
                continue
            path_part, suffix = split_dest(dest)
            if path_part == "":
                continue  # pure "#anchor" link
            trailing_slash = path_part.endswith("/")

            old_target = posixpath.normpath(posixpath.join(old_file_dir, path_part))
            mapped_target = map_path(old_target, full_map)
            new_path_part = posixpath.relpath(mapped_target, new_file_dir)
            if trailing_slash and not new_path_part.endswith("/"):
                new_path_part += "/"
            new_dest = new_path_part + suffix

            if new_dest == dest:
                continue  # byte-identical after normalisation: skip

            if "%" in dest or is_angle_bracketed(line, link.start, link.end):
                abort_angle_percent.append((old_path, link.line, dest))
                continue
            # Resolvable either in the pre-move tree, or (for files already
            # moved, e.g. during --repair) in the post-move tree.
            if not (root / old_target).exists() and not (root / mapped_target).exists():
                abort_missing.append((old_path, link.line, dest))
                continue

            edits.append((link.start, link.end, new_dest))
            link_rewrites.append((old_path, link.line, dest, new_dest))

        for m in regex.finditer(line):
            if any(s <= m.start() < e for s, e in excluded):
                continue
            name = m.group(1)
            new_text_ = f"skills/{full_map[name]}/{name}"
            if new_text_ != m.group(0):
                edits.append((m.start(), m.end(), new_text_))
                plain_rewrites.append((old_path, lineno, m.group(0), new_text_))

        new_lines.append(apply_edits(line, edits))

    return new_path, "\n".join(new_lines), link_rewrites, plain_rewrites, fixed_applied


def remaining_plain_paths(root: Path, full_map: dict[str, str]) -> list[tuple[str, int, str]]:
    """Any leftover "skills/<name>" (old-style) mention still in the tree."""
    regex = plain_path_regex(full_map)
    hits = []
    for rel_path in iter_markdown_files(root):
        text = (root / rel_path).read_text(encoding="utf-8")
        for lineno, line in enumerate(text.split("\n"), start=1):
            for m in regex.finditer(line):
                hits.append((rel_path, lineno, m.group(0)))
    return hits


# --------------------------------------------------------------------------
# Guards
# --------------------------------------------------------------------------

def guard_unmapped(flat_names: list[str], full_map: dict[str, str]) -> None:
    unmapped = sorted(n for n in flat_names if n not in full_map)
    if unmapped:
        abort(
            "unmapped flat skill dir(s), add to MOVE_MAP or pass --map NAME=CATEGORY: "
            + ", ".join(unmapped)
        )


def guard_existing_target(root: Path, names: list[str], full_map: dict[str, str]) -> None:
    collisions = [
        f"skills/{full_map[n]}/{n}" for n in names if (root / "skills" / full_map[n] / n).exists()
    ]
    if collisions:
        abort("target already exists for dir(s) that still need moving: " + ", ".join(collisions))


def guard_dirty_tree(root: Path) -> None:
    status = run_git(["status", "--porcelain", "--untracked-files=no"], root=root).stdout
    if status.strip():
        abort("working tree has uncommitted tracked changes:\n" + status)
    untracked = run_git(
        ["ls-files", "--others", "--exclude-standard", "--", "skills", "references", "templates"],
        root=root,
    ).stdout
    if untracked.strip():
        abort("untracked file(s) under skills/, references/, or templates/:\n" + untracked)


def guard_category_collision(full_map: dict[str, str]) -> None:
    bad = sorted(set(full_map) & set(CATEGORIES))
    if bad:
        abort("skill name(s) collide with a category dir name: " + ", ".join(bad))


# --------------------------------------------------------------------------
# Post-checks (shared by --apply and --check)
# --------------------------------------------------------------------------

def run_post_checks(root: Path, full_map: dict[str, str], context: str) -> None:
    problems, _stats = check_links.check(root, check_links.markdown_files(root))
    if problems:
        details = "\n".join(f"  {p.path}:{p.line} -> {p.dest} ({p.reason})" for p in problems)
        abort(f"{context}: post-check found {len(problems)} broken link(s)/anchor(s):\n{details}", code=1)

    depth2, depth3 = depth_counts(root)
    if depth2 != 0 or depth3 != EXPECTED_SKILL_COUNT:
        abort(
            f"{context}: post-check expected 0 SKILL.md at depth 2 and "
            f"{EXPECTED_SKILL_COUNT} at depth 3, found {depth2} and {depth3}",
            code=1,
        )

    diff = run_git(["diff", "--cached", "-M", "--diff-filter=AD", "HEAD", "--", "skills"], root=root).stdout
    if diff.strip():
        abort(f"{context}: post-check found add/delete (not pure rename) under skills/:\n{diff}", code=1)

    leftovers = remaining_plain_paths(root, full_map)
    if leftovers:
        details = "\n".join(f"  {p}:{l}: {t}" for p, l, t in leftovers)
        abort(f"{context}: post-check found leftover old-style skills/<name> path(s):\n{details}", code=1)

    print(
        f"{context}: post-checks passed (0 broken links/anchors, "
        f"{EXPECTED_SKILL_COUNT} SKILL.md at depth 3, 0 at depth 2, "
        "skills/ diff is a pure rename, no leftover plain paths)"
    )


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------

def cmd_dry_run(root: Path, full_map: dict[str, str]) -> int:
    flat_names = flat_skill_dirs(root)
    if not flat_names:
        print("No flat skill dirs found; tree is already categorized, nothing to move.")
        return 0

    moves = [(n, full_map[n]) for n in flat_names if n in full_map]
    unmapped = [n for n in flat_names if n not in full_map]

    abort_angle_percent: list[tuple[str, int, str]] = []
    abort_missing: list[tuple[str, int, str]] = []
    all_link_rewrites: list[tuple[str, int, str, str]] = []
    all_plain_rewrites: list[tuple[str, int, str, str]] = []
    fixed_count = 0

    for old_path in iter_markdown_files(root):
        _new_path, _new_text, link_rewrites, plain_rewrites, fixed_applied = compute_file_rewrite(
            root, old_path, full_map, abort_angle_percent, abort_missing
        )
        all_link_rewrites.extend(link_rewrites)
        all_plain_rewrites.extend(plain_rewrites)
        fixed_count += 1 if fixed_applied else 0

    print("Planned moves:")
    for name, cat in moves:
        print(f"  git mv skills/{name} skills/{cat}/{name}")
    if unmapped:
        print("Unmapped flat skill dir(s) (would abort --apply/--repair): " + ", ".join(unmapped))

    print("\nPlanned link rewrites:")
    for path, line, old, new in all_link_rewrites:
        print(f"{path}:{line}: {old} -> {new}")

    print("\nPlanned plain-path rewrites:")
    for path, line, old, new in all_plain_rewrites:
        print(f"{path}:{line}: {old} -> {new}")

    if abort_angle_percent or abort_missing:
        print("\nUnresolvable link(s) (would abort --apply/--repair):")
        for path, line, dest in abort_angle_percent:
            print(f"  {path}:{line} -> {dest} (angle-bracketed or percent-encoded)")
        for path, line, dest in abort_missing:
            print(f"  {path}:{line} -> {dest} (target missing)")

    print(
        f"\nSUMMARY moves={len(moves)} link-rewrites={len(all_link_rewrites)} "
        f"plain-rewrites={len(all_plain_rewrites)} fixed-rewrites={fixed_count} "
        f"unresolvable={len(abort_angle_percent) + len(abort_missing)}"
    )
    return 0


def cmd_apply(root: Path, full_map: dict[str, str]) -> int:
    flat_names = flat_skill_dirs(root)
    if not flat_names:
        print("No flat skill dirs found; nothing to apply.")
        return 0

    guard_unmapped(flat_names, full_map)
    moves = [(n, full_map[n]) for n in flat_names]
    guard_existing_target(root, [n for n, _ in moves], full_map)
    guard_dirty_tree(root)
    guard_category_collision(full_map)

    abort_angle_percent: list[tuple[str, int, str]] = []
    abort_missing: list[tuple[str, int, str]] = []
    rewrites: dict[str, tuple[str, str]] = {}
    link_count = plain_count = fixed_count = 0

    for old_path in iter_markdown_files(root):
        new_path, new_text, link_rewrites, plain_rewrites, fixed_applied = compute_file_rewrite(
            root, old_path, full_map, abort_angle_percent, abort_missing
        )
        rewrites[old_path] = (new_path, new_text)
        link_count += len(link_rewrites)
        plain_count += len(plain_rewrites)
        fixed_count += 1 if fixed_applied else 0

    if abort_angle_percent or abort_missing:
        lines = ["cannot rewrite the following link(s) automatically:"]
        for path, line, dest in abort_angle_percent:
            lines.append(f"  {path}:{line} -> {dest} (angle-bracketed or percent-encoded)")
        for path, line, dest in abort_missing:
            lines.append(f"  {path}:{line} -> {dest} (target missing in old tree)")
        abort("\n".join(lines))

    # Move directories first, while every file's content is still untouched
    # (a plain structural rename). Write rewritten content afterwards, at
    # each file's final path, and `git add` it there. `git mv` on a
    # directory stages the rename by reusing the source's existing index
    # blob rather than re-hashing the working tree, so writing to the old
    # path before moving would leave the index pointing at pre-rewrite
    # content even though the physical move itself succeeded.
    moved_cats: set[str] = set()
    for name, cat in moves:
        if cat not in moved_cats:
            (root / "skills" / cat).mkdir(parents=True, exist_ok=True)
            moved_cats.add(cat)
        run_git(["mv", f"skills/{name}", f"skills/{cat}/{name}"], root=root)

    changed = []
    for old_path, (new_path, new_text) in rewrites.items():
        original = (root / new_path).read_text(encoding="utf-8")
        if new_text != original:
            (root / new_path).write_text(new_text, encoding="utf-8")
            changed.append(new_path)

    if changed:
        run_git(["add", "--", *sorted(changed)], root=root)

    run_post_checks(root, full_map, context="apply")
    print(
        f"Applied: moves={len(moves)} link-rewrites={link_count} "
        f"plain-rewrites={plain_count} fixed-rewrites={fixed_count}"
    )
    return 0


def resolve_base(root: Path, base_arg: str | None) -> str | None:
    if base_arg:
        try:
            run_git(["rev-parse", "--verify", base_arg], root=root)
        except subprocess.CalledProcessError:
            return None
        return base_arg
    try:
        run_git(["rev-parse", "--verify", "origin/main"], root=root)
    except subprocess.CalledProcessError:
        return None
    try:
        merge_base = run_git(["merge-base", "HEAD", "origin/main"], root=root).stdout.strip()
    except subprocess.CalledProcessError:
        return None
    try:
        listing = run_git(["ls-tree", "-r", "--name-only", merge_base, "--", "skills"], root=root).stdout
    except subprocess.CalledProcessError:
        return None
    flat_pattern = re.compile(r"^skills/[^/]+/SKILL\.md$")
    if any(flat_pattern.match(line) for line in listing.splitlines()):
        return merge_base
    return None


def cmd_check(root: Path, full_map: dict[str, str], base_arg: str | None) -> int:
    ok = True

    missing = sorted(
        n for n, cat in full_map.items() if not (root / "skills" / cat / n / "SKILL.md").is_file()
    )
    if missing:
        ok = False
        print(f"FAIL: missing categorized skill(s): {', '.join(missing)}")
    else:
        print(f"OK: all {len(full_map)} mapped skill(s) found at skills/<category>/<name>/SKILL.md")

    depth2, depth3 = depth_counts(root)
    if depth2 != 0 or depth3 != EXPECTED_SKILL_COUNT:
        ok = False
        print(
            f"FAIL: expected 0 SKILL.md at depth 2 and {EXPECTED_SKILL_COUNT} at depth 3; "
            f"found {depth2} and {depth3}"
        )
    else:
        print(f"OK: {EXPECTED_SKILL_COUNT} SKILL.md at depth 3, 0 at depth 2")

    flat = flat_skill_dirs(root)
    if flat:
        ok = False
        print(f"FAIL: flat skill dir(s) remain: {', '.join(flat)}")
    else:
        print("OK: no flat skill dir remains")

    problems, stats = check_links.check(root, check_links.markdown_files(root))
    if problems:
        ok = False
        print(f"FAIL: {len(problems)} broken link(s)/anchor(s)")
        for p in problems:
            print(f"  {p.path}:{p.line} -> {p.dest} ({p.reason})")
    else:
        print(
            f"OK: 0 broken links/anchors ({stats['links-checked']} links, "
            f"{stats['anchors-checked']} anchors checked)"
        )

    leftovers = remaining_plain_paths(root, full_map)
    if leftovers:
        ok = False
        print(f"FAIL: {len(leftovers)} leftover old-style skills/<name> path(s)")
        for p, l, t in leftovers:
            print(f"  {p}:{l}: {t}")
    else:
        print("OK: no leftover old-style skills/<name> path remains")

    base = resolve_base(root, base_arg)
    if base:
        diff = run_git(
            ["diff", "-M", "--diff-filter=AD", base, "HEAD", "--", "skills/*/SKILL.md", "skills/*/*/SKILL.md"],
            root=root,
        ).stdout
        if diff.strip():
            ok = False
            print(f"FAIL: {base}..HEAD shows an added/deleted skill file (expected pure rename):\n{diff}")
        else:
            print(f"OK: {base}..HEAD shows no skill file add/delete")
    elif base_arg:
        ok = False
        print(f"FAIL: cannot resolve --base {base_arg}")
    else:
        print("SKIP: no usable base (no --base given, and origin/main merge-base unavailable or already categorized)")

    return 0 if ok else 1


def repair_broken_links(
    root: Path, full_map: dict[str, str]
) -> tuple[list[tuple[str, int, str, str]], list, set[str]]:
    """Fix links broken by a rebase, assuming the file's old flat location."""
    problems, _stats = check_links.check(root, check_links.markdown_files(root))
    broken_by_file: dict[str, list] = {}
    for p in problems:
        broken_by_file.setdefault(p.path, []).append(p)

    fixed: list[tuple[str, int, str, str]] = []
    unfixable: list = []
    touched: set[str] = set()

    for rel_path, probs in broken_by_file.items():
        parts = rel_path.split("/")
        if len(parts) >= 3 and parts[0] == "skills":
            name = parts[2]
            sim_old_dir = posixpath.dirname("/".join(["skills", name, *parts[3:]]))
        else:
            # File outside skills/ (or not deep enough to have moved): it kept
            # its own path, but any "skills/<name>/..." target it points at
            # still needs remapping to the new category path.
            sim_old_dir = posixpath.dirname(rel_path)
        actual_dir = posixpath.dirname(rel_path)

        file_path = root / rel_path
        text = file_path.read_text(encoding="utf-8")
        lines = text.split("\n")

        links_by_line: dict[int, list] = {}
        for link in check_links.iter_links(text):
            links_by_line.setdefault(link.line, []).append(link)

        edits_by_line: dict[int, list[tuple[int, int, str]]] = {}
        used_links: set[tuple[int, int]] = set()

        for p in probs:
            candidates = [
                l
                for l in links_by_line.get(p.line, [])
                if l.dest == p.dest and (l.line, l.start) not in used_links
            ]
            if not candidates:
                unfixable.append(p)
                continue
            link = candidates[0]
            used_links.add((link.line, link.start))
            dest = link.dest
            path_part, suffix = split_dest(dest)
            if path_part == "":
                unfixable.append(p)
                continue
            trailing_slash = path_part.endswith("/")

            old_target = posixpath.normpath(posixpath.join(sim_old_dir, path_part))
            mapped_target = map_path(old_target, full_map)
            if not (root / mapped_target).exists():
                unfixable.append(p)
                continue

            new_path_part = posixpath.relpath(mapped_target, actual_dir)
            if trailing_slash and not new_path_part.endswith("/"):
                new_path_part += "/"
            new_dest = new_path_part + suffix
            if new_dest == dest:
                unfixable.append(p)
                continue

            edits_by_line.setdefault(p.line, []).append((link.start, link.end, new_dest))
            fixed.append((rel_path, p.line, dest, new_dest))

        if edits_by_line:
            new_lines = [
                apply_edits(line, edits_by_line[i]) if i in edits_by_line else line
                for i, line in enumerate(lines, start=1)
            ]
            file_path.write_text("\n".join(new_lines), encoding="utf-8")
            touched.add(rel_path)

    return fixed, unfixable, touched


def repair_plain_paths(root: Path, full_map: dict[str, str]) -> tuple[list[tuple[str, int, str, str]], set[str]]:
    regex = plain_path_regex(full_map)
    fixed: list[tuple[str, int, str, str]] = []
    touched: set[str] = set()

    for rel_path in iter_markdown_files(root):
        file_path = root / rel_path
        text = file_path.read_text(encoding="utf-8")

        links_by_line: dict[int, list] = {}
        for link in check_links.iter_links(text):
            links_by_line.setdefault(link.line, []).append(link)

        lines = text.split("\n")
        changed = False
        new_lines = []
        for lineno, line in enumerate(lines, start=1):
            excluded = [(l.start, l.end) for l in links_by_line.get(lineno, [])]
            edits = []
            for m in regex.finditer(line):
                if any(s <= m.start() < e for s, e in excluded):
                    continue
                name = m.group(1)
                new_text_ = f"skills/{full_map[name]}/{name}"
                if new_text_ != m.group(0):
                    edits.append((m.start(), m.end(), new_text_))
                    fixed.append((rel_path, lineno, m.group(0), new_text_))
            if edits:
                changed = True
                new_lines.append(apply_edits(line, edits))
            else:
                new_lines.append(line)

        if changed:
            file_path.write_text("\n".join(new_lines), encoding="utf-8")
            touched.add(rel_path)

    return fixed, touched


def cmd_repair(root: Path, full_map: dict[str, str]) -> int:
    guard_dirty_tree(root)
    flat_names = flat_skill_dirs(root)
    guard_unmapped(flat_names, full_map)
    guard_existing_target(root, flat_names, full_map)
    guard_category_collision(full_map)

    moves = [(n, full_map[n]) for n in flat_names]
    link_count = plain_count = fixed_count = 0

    if moves:
        abort_angle_percent: list[tuple[str, int, str]] = []
        abort_missing: list[tuple[str, int, str]] = []
        own_files = [
            p
            for p in iter_markdown_files(root)
            if any(p == f"skills/{n}" or p.startswith(f"skills/{n}/") for n in flat_names)
        ]
        rewrites: dict[str, tuple[str, str]] = {}
        for old_path in own_files:
            new_path, new_text, link_rewrites, plain_rewrites, fixed_applied = compute_file_rewrite(
                root, old_path, full_map, abort_angle_percent, abort_missing
            )
            rewrites[old_path] = (new_path, new_text)
            link_count += len(link_rewrites)
            plain_count += len(plain_rewrites)
            fixed_count += 1 if fixed_applied else 0

        if abort_angle_percent or abort_missing:
            lines = ["cannot rewrite the following link(s) automatically:"]
            for path, line, dest in abort_angle_percent:
                lines.append(f"  {path}:{line} -> {dest} (angle-bracketed or percent-encoded)")
            for path, line, dest in abort_missing:
                lines.append(f"  {path}:{line} -> {dest} (target missing)")
            abort("\n".join(lines))

        # Move first (plain rename, content untouched), then write final
        # content at the new path and `git add` it there -- see cmd_apply
        # for why this order matters (git mv reuses the source's index
        # blob instead of re-hashing the working tree).
        moved_cats: set[str] = set()
        for name, cat in moves:
            if cat not in moved_cats:
                (root / "skills" / cat).mkdir(parents=True, exist_ok=True)
                moved_cats.add(cat)
            run_git(["mv", f"skills/{name}", f"skills/{cat}/{name}"], root=root)

        own_changed = []
        for old_path, (new_path, new_text) in rewrites.items():
            original = (root / new_path).read_text(encoding="utf-8")
            if new_text != original:
                (root / new_path).write_text(new_text, encoding="utf-8")
                own_changed.append(new_path)

        if own_changed:
            run_git(["add", "--", *sorted(own_changed)], root=root)

    link_fixed, link_unfixable, link_touched = repair_broken_links(root, full_map)
    plain_fixed, plain_touched = repair_plain_paths(root, full_map)

    moved_prefixes = tuple(f"skills/{n}" for n in flat_names)
    touched_unmoved = sorted(
        p
        for p in (link_touched | plain_touched)
        if not any(p == pre or p.startswith(pre + "/") for pre in moved_prefixes)
    )
    if touched_unmoved:
        run_git(["add", "--", *touched_unmoved], root=root)

    print(
        f"repair: moved={len(moves)} link-rewrites={link_count} plain-rewrites={plain_count} "
        f"fixed-rewrites={fixed_count} broken-link-fixes={len(link_fixed)} "
        f"plain-path-fixes={len(plain_fixed)}"
    )
    if link_unfixable:
        print(f"repair: {len(link_unfixable)} broken link(s) could not be auto-fixed:")
        for p in link_unfixable:
            print(f"  {p.path}:{p.line} -> {p.dest} ({p.reason})")

    problems, _stats = check_links.check(root, check_links.markdown_files(root))
    depth2, depth3 = depth_counts(root)
    remaining_flat = flat_skill_dirs(root)
    leftovers = remaining_plain_paths(root, full_map)

    print(
        f"repair tree-check: broken-links={len(problems)} depth2={depth2} depth3={depth3} "
        f"flat-remaining={len(remaining_flat)} leftover-plain-paths={len(leftovers)}"
    )
    if problems:
        print(f"repair: {len(problems)} broken link(s)/anchor(s) remain unfixable:")
        for p in problems:
            print(f"  {p.path}:{p.line} -> {p.dest} ({p.reason})")
    if leftovers:
        print(f"repair: {len(leftovers)} leftover old-style skills/<name> path(s):")
        for path, line, text in leftovers:
            print(f"  {path}:{line} {text}")

    # Unlike --apply/--check, --repair's job is to let branches add new
    # skills across the move boundary, so depth3 legitimately grows beyond
    # EXPECTED_SKILL_COUNT. Only depth2 == 0 (nothing left at the old
    # flat depth) and no remaining flat dir are required.
    ok = not problems and depth2 == 0 and not remaining_flat and not leftovers
    if ok:
        print("repair: tree is clean. Suggested commit:")
        print('  git commit -m "chore: repair skill-category layout after rebase"')
        return 0
    print("repair: tree still has issues after repair; see FAIL/leftover details above.", file=sys.stderr)
    return 1


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", dest="mode", action="store_const", const="dry-run")
    mode_group.add_argument("--apply", dest="mode", action="store_const", const="apply")
    mode_group.add_argument("--check", dest="mode", action="store_const", const="check")
    mode_group.add_argument("--repair", dest="mode", action="store_const", const="repair")
    parser.add_argument("--base", default=None, help="base revision for --check's rename-only diff")
    parser.add_argument(
        "--map",
        dest="map_args",
        action="append",
        default=[],
        metavar="NAME=CATEGORY",
        help="place a skill not in MOVE_MAP (repeatable)",
    )
    parser.set_defaults(mode="dry-run")
    args = parser.parse_args(argv)

    if not (REPO_ROOT / "skills").is_dir():
        abort(f"no skills/ directory found under repo root {REPO_ROOT}")

    full_map = build_full_map(args.map_args)

    if args.mode == "dry-run":
        return cmd_dry_run(REPO_ROOT, full_map)
    if args.mode == "apply":
        return cmd_apply(REPO_ROOT, full_map)
    if args.mode == "check":
        return cmd_check(REPO_ROOT, full_map, args.base)
    if args.mode == "repair":
        return cmd_repair(REPO_ROOT, full_map)
    return 2


if __name__ == "__main__":
    sys.exit(main())
