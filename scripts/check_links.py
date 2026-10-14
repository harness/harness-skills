#!/usr/bin/env python3
"""Check Markdown links and anchors.

Usage: scripts/check_links.py [path ...] [--root DIR]

With no positional arguments, checks every Markdown file (*.md, *.mdc) git
knows about or would add, starting from the repo root. Positional arguments
(files or directories, relative to the current directory) restrict the set
of files checked. --root overrides the repo root used for file discovery
and for resolving "outside root" links.

Prints one line per broken link or anchor, then a SUMMARY line. Exit 1 if
anything is broken, 0 if clean, 2 on usage or tree errors.
"""
from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Sequence
from urllib.parse import unquote

SKIP_DIRS = {".git", ".claude", "node_modules"}

# A URL with a scheme (http:, mailto:, ...) or a protocol-relative "//" URL.
URL_RE = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*:|//)")

FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
# Inline code span: N backticks, non-greedy content, the same N backticks.
CODE_SPAN_RE = re.compile(r"(`+)(?!`)([\s\S]*?[^`])\1(?!`)")
LINK_DEST_RE = re.compile(r"\]\(\s*(<[^>]*>|[^\s)]+)")
REF_DEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*(<[^>]*>|\S+)")
ATX_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
TRAILING_HASHES_RE = re.compile(r"\s+#+\s*$")
LINK_TEXT_RE = re.compile(r"!?\[([^\]]*)\]\([^)]*\)")
STAR_EMPHASIS_RE = re.compile(r"(\*{1,3})(.+?)\1")
UNDERSCORE_EMPHASIS_RE = re.compile(r"(_{1,3})(.+?)\1")
HTML_TAG_RE = re.compile(r"<[^>]+>")
HTML_A_NAME_RE = re.compile(r'<a\b[^>]*\bname\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.IGNORECASE)
HTML_ID_ATTR_RE = re.compile(r'\bid\s*=\s*(?:"([^"]*)"|\'([^\']*)\')', re.IGNORECASE)
LINE_FRAGMENT_RE = re.compile(r"^L\d+(-L\d+)?$")


@dataclass(frozen=True)
class Link:
    line: int  # 1-based line number
    dest: str  # destination as written (no angle brackets)
    start: int  # 0-based column of dest's first char in the raw line
    end: int  # column one past dest's last char


@dataclass(frozen=True)
class Problem:
    path: str  # relative to root, posix separators
    line: int
    dest: str
    reason: str  # "missing file" | "missing anchor"


def _frontmatter_end(lines: list[str]) -> int:
    """Return the index of the first line after YAML frontmatter, or 0 if none."""
    if not lines or lines[0].rstrip("\r\n") != "---":
        return 0
    for i in range(1, len(lines)):
        if lines[i].rstrip("\r\n") == "---":
            return i + 1
    return 0


def _mask_code_spans(line: str) -> str:
    """Replace inline code spans with spaces of the same length, preserving columns."""
    return CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)


def iter_links(text: str) -> Iterator[Link]:
    """Yield every inline link/image destination and reference definition.

    Skips fenced code blocks, inline code spans, and YAML frontmatter. Does
    not filter external or anchor-only destinations -- see is_external().
    """
    lines = text.split("\n")
    skip_until = _frontmatter_end(lines)
    fence: tuple[str, int] | None = None
    for i, raw in enumerate(lines):
        if i < skip_until:
            continue
        f = FENCE_RE.match(raw)
        if f:
            token = f.group(1)
            ch, length = token[0], len(token)
            if fence is None:
                fence = (ch, length)
            elif ch == fence[0] and length >= fence[1]:
                fence = None
            continue
        if fence is not None:
            continue
        masked = _mask_code_spans(raw)
        for m in LINK_DEST_RE.finditer(masked):
            yield _link_from_match(i + 1, m, 1)
        d = REF_DEF_RE.match(masked)
        if d:
            yield _link_from_match(i + 1, d, 1)


def _link_from_match(line: int, m: re.Match, group: int) -> Link:
    dest_raw = m.group(group)
    start, end = m.start(group), m.end(group)
    if dest_raw.startswith("<"):
        dest = dest_raw[1:-1]
        start += 1
        end -= 1
    else:
        dest = dest_raw
    return Link(line=line, dest=dest, start=start, end=end)


def is_external(dest: str) -> bool:
    """True for URLs with a scheme or protocol-relative "//" URLs."""
    return bool(URL_RE.match(dest))


def _strip_one_emphasis(text: str) -> str | None:
    """Strip the first emphasis span found, or None if there is none.

    "*"/"**"/"***" may appear intraword (CommonMark allows this), but a
    lone "_" delimiter run may not -- so an underscore span only counts as
    emphasis when the characters just outside it are not alphanumeric.
    """
    m = STAR_EMPHASIS_RE.search(text)
    if m:
        return text[: m.start()] + m.group(2) + text[m.end() :]
    for m in UNDERSCORE_EMPHASIS_RE.finditer(text):
        start, end = m.start(), m.end()
        before = text[start - 1] if start > 0 else ""
        after = text[end] if end < len(text) else ""
        if not before.isalnum() and not after.isalnum():
            return text[:start] + m.group(2) + text[end:]
    return None


def _render_inline(text: str) -> str:
    """Reduce inline Markdown markup to its plain-text content."""
    text = CODE_SPAN_RE.sub(lambda m: m.group(2), text)
    text = LINK_TEXT_RE.sub(lambda m: m.group(1), text)
    while True:
        stripped = _strip_one_emphasis(text)
        if stripped is None:
            break
        text = stripped
    text = HTML_TAG_RE.sub("", text)
    return text


def _slugify_heading(raw_text: str) -> str:
    """GitHub-style anchor slug for one ATX heading's text."""
    text = TRAILING_HASHES_RE.sub("", raw_text.rstrip())
    text = _render_inline(text)
    text = text.lower()
    kept = [ch for ch in text if ch.isalnum() or ch in ("_", "-", " ")]
    return "".join(kept).replace(" ", "-")


def heading_anchors(text: str) -> set[str]:
    """All valid anchors for a Markdown document.

    Includes GitHub-style slugs of ATX headings (with -1, -2, ... suffixes
    for duplicates) plus explicit <a name="x">, <a id="x">, and any id="x"
    attributes. Headings and anchors inside fenced code blocks or YAML
    frontmatter are ignored.
    """
    lines = text.split("\n")
    skip_until = _frontmatter_end(lines)
    fence: tuple[str, int] | None = None
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for i, raw in enumerate(lines):
        if i < skip_until:
            continue
        f = FENCE_RE.match(raw)
        if f:
            token = f.group(1)
            ch, length = token[0], len(token)
            if fence is None:
                fence = (ch, length)
            elif ch == fence[0] and length >= fence[1]:
                fence = None
            continue
        if fence is not None:
            continue
        h = ATX_HEADING_RE.match(raw)
        if h:
            slug = _slugify_heading(h.group(2))
            if slug in seen:
                seen[slug] += 1
                anchors.add(f"{slug}-{seen[slug]}")
            else:
                seen[slug] = 0
                anchors.add(slug)
        for m in HTML_A_NAME_RE.finditer(raw):
            anchors.add(m.group(1) if m.group(1) is not None else m.group(2))
        for m in HTML_ID_ATTR_RE.finditer(raw):
            anchors.add(m.group(1) if m.group(1) is not None else m.group(2))
    return anchors


def _walk_markdown(base: Path) -> list[Path]:
    out: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            if fn.endswith(".md") or fn.endswith(".mdc"):
                out.append(Path(dirpath) / fn)
    return out


def _git_or_walk_markdown(root: Path) -> list[Path]:
    try:
        proc = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "--", "*.md", "*.mdc"],
            cwd=root,
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, OSError):
        return _walk_markdown(root)
    files = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if line:
            files.append(root / line)
    return files


def markdown_files(root: Path, paths: Sequence[str] = ()) -> list[Path]:
    """Resolve the set of Markdown files to check.

    With no paths, lists files git knows about or would add under root
    (falling back to a directory walk if root is not a git repo). With
    paths given (relative to the current directory), restricts the set to
    those files/directories instead.
    """
    root = Path(root)
    if paths:
        collected: list[Path] = []
        for p in paths:
            fp = Path(p)
            if not fp.is_absolute():
                fp = Path.cwd() / fp
            if fp.is_dir():
                collected.extend(_walk_markdown(fp))
            elif fp.is_file():
                collected.append(fp)
        candidates = collected
    else:
        candidates = _git_or_walk_markdown(root)

    seen: set[Path] = set()
    result: list[Path] = []
    for f in candidates:
        try:
            resolved = f.resolve()
        except OSError:
            continue
        if resolved in seen or not resolved.is_file():
            continue
        seen.add(resolved)
        result.append(resolved)
    result.sort()
    return result


def check(root: Path, files: Iterable[Path]) -> tuple[list[Problem], dict[str, int]]:
    """Check links and anchors in files. Returns (problems, stats).

    stats keys: md-files, links-checked, anchors-checked.
    """
    root = Path(root).resolve()
    problems: list[Problem] = []
    stats = {"md-files": 0, "links-checked": 0, "anchors-checked": 0}
    anchor_cache: dict[Path, set[str] | None] = {}

    def get_anchors(path: Path) -> set[str] | None:
        if path in anchor_cache:
            return anchor_cache[path]
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            anchor_cache[path] = None
            return None
        anchors = heading_anchors(content)
        anchor_cache[path] = anchors
        return anchors

    for file_path in files:
        stats["md-files"] += 1
        try:
            text = file_path.read_text(encoding="utf-8")
        except OSError:
            continue
        resolved_self = file_path.resolve()
        anchor_cache.setdefault(resolved_self, heading_anchors(text))

        try:
            rel_str = resolved_self.relative_to(root).as_posix()
        except ValueError:
            rel_str = resolved_self.as_posix()

        for link in iter_links(text):
            dest = link.dest
            if not dest or is_external(dest):
                continue

            if "#" in dest:
                path_part, frag = dest.split("#", 1)
            else:
                path_part, frag = dest, None
            path_part = path_part.split("?", 1)[0]

            if path_part:
                stats["links-checked"] += 1
                decoded = unquote(path_part)
                resolved = (file_path.parent / decoded).resolve()
                in_root = resolved.is_relative_to(root)
                if not in_root or not resolved.exists():
                    problems.append(Problem(rel_str, link.line, dest, "missing file"))
                    continue
                if frag is None:
                    continue
                decoded_frag = unquote(frag)
                if LINE_FRAGMENT_RE.match(decoded_frag):
                    continue
                if resolved.suffix.lower() not in (".md", ".mdc"):
                    continue
                stats["anchors-checked"] += 1
                anchors = get_anchors(resolved)
                if anchors is None or decoded_frag not in anchors:
                    problems.append(Problem(rel_str, link.line, dest, "missing anchor"))
            else:
                if frag is None:
                    continue
                decoded_frag = unquote(frag)
                if LINE_FRAGMENT_RE.match(decoded_frag):
                    continue
                stats["anchors-checked"] += 1
                anchors = anchor_cache.get(resolved_self)
                if anchors is None or decoded_frag not in anchors:
                    problems.append(Problem(rel_str, link.line, dest, "missing anchor"))

    problems.sort(key=lambda p: (p.path, p.line))
    return problems, stats


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check Markdown links and anchors.")
    parser.add_argument("paths", nargs="*", help="files or directories to check, relative to cwd")
    parser.add_argument("--root", help="repo root (defaults to the parent of scripts/)")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 2

    root = Path(args.root) if args.root else Path(__file__).resolve().parent.parent
    if not root.is_dir():
        print(f"error: root not found: {root}", file=sys.stderr)
        return 2
    root = root.resolve()

    try:
        files = markdown_files(root, args.paths)
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    problems, stats = check(root, files)
    for p in problems:
        print(f"{p.path}:{p.line} -> {p.dest} ({p.reason})")
    broken = len(problems)
    print(
        f"SUMMARY md-files={stats['md-files']} links-checked={stats['links-checked']} "
        f"anchors-checked={stats['anchors-checked']} broken={broken}"
    )
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
