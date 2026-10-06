"""Shared stdlib-only markdown helpers for FME docs-contract tests.

These are narrow, purpose-built parsers (regex/line-based) — NOT general
markdown or YAML engines. They exist only to support structural checks of
checked-in documentation (links, headings, fenced code). They do not
execute any skill, call any MCP tool, or invoke a live CLI/backend.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

_FENCE_RE = re.compile(r"^\s*```")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_INLINE_CODE_RE = re.compile(r"`[^`]*`")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


def lines_outside_fences(path: Path):
    """Yield (line_no, line_text) for lines not inside ``` code fences."""
    in_fence = False
    for i, line in enumerate(read_lines(path), start=1):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        yield i, line


def iter_markdown_links(path: Path):
    """Yield (line_no, text, target) for links outside code fences/spans."""
    for line_no, line in lines_outside_fences(path):
        # Drop inline code spans so `[fake](link)` examples aren't treated
        # as real navigable links.
        stripped = _INLINE_CODE_RE.sub("", line)
        for match in _LINK_RE.finditer(stripped):
            yield line_no, match.group(1), match.group(2)


def slugify(heading: str) -> str:
    """Approximate GitHub's heading-to-anchor slug algorithm."""
    text = heading.strip().lower()
    text = re.sub(r"[`*]", "", text)  # GitHub preserves identifier underscores.
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    return text


def get_heading_slugs(path: Path) -> set[str]:
    slugs = set()
    for _, line in lines_outside_fences(path):
        match = _HEADING_RE.match(line)
        if match:
            slugs.add(slugify(match.group(2)))
    return slugs


def iter_fenced_code_blocks(path: Path):
    """Yield (start_line, lang, code_text) for each ``` fenced block."""
    lines = read_lines(path)
    i = 0
    while i < len(lines):
        m = re.match(r"^\s*```(\S*)", lines[i])
        if m:
            lang = m.group(1)
            start = i + 1
            body = []
            i += 1
            while i < len(lines) and not _FENCE_RE.match(lines[i]):
                body.append(lines[i])
                i += 1
            yield start, lang, "\n".join(body)
        i += 1
