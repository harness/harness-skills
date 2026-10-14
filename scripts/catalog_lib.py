"""Load and validate the skill catalog (skills/categories.json + SKILL.md frontmatter).

Importable library only -- no CLI. Consumed by the Claude/Cursor/Codex plugin
manifest generators so they agree on skill and category data.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

MARKETPLACE_NAME = "harness-skills"
REPOSITORY = "https://github.com/harness/harness-skills"
AUTHOR = "Harness"
LICENSE = "Apache-2.0"
SUMMARY_MAX = 120

UMBRELLA_NAME = "harness-skills"
UMBRELLA_DISPLAY_NAME = "Harness Skills"

SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")
CATEGORY_KEYS = ("dir", "plugin", "title", "description", "category", "keywords")


class CatalogError(Exception):
    """A problem with skills/categories.json or a SKILL.md tree."""


@dataclass(frozen=True)
class Skill:
    name: str  # frontmatter name == directory name
    category: str  # category dir, e.g. "fme"
    path: str  # posix, relative to repo root, e.g. "skills/fme/explain-flag"
    description: str  # frontmatter description folded to one line (single spaces, stripped)
    summary: str  # metadata.summary
    version: str  # metadata.version
    mcp_server: str  # metadata.mcp-server
    compatibility: str  # top-level compatibility
    license: str  # top-level license


@dataclass(frozen=True)
class Category:
    dir: str
    plugin: str
    title: str
    description: str
    category: str
    keywords: tuple[str, ...]
    skills: tuple[Skill, ...]  # sorted by skill name


@dataclass(frozen=True)
class Catalog:
    root: Path  # absolute repo root
    version: str  # categories.json top-level "version" (semver)
    categories: tuple[Category, ...]  # categories.json order

    @property
    def skills(self) -> tuple[Skill, ...]:
        return tuple(skill for cat in self.categories for skill in cat.skills)

    def category(self, dir: str) -> Category:
        for cat in self.categories:
            if cat.dir == dir:
                return cat
        raise KeyError(dir)

    def plugin(self, name: str) -> Category:
        for cat in self.categories:
            if cat.plugin == name:
                return cat
        raise KeyError(name)


def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent


def render_json(obj: object) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False) + "\n"


def count_label(n: int) -> str:
    return f"{n} skill" if n == 1 else f"{n} skills"


def umbrella_description(catalog: Catalog) -> str:
    n = len(catalog.skills)
    return (
        f"All {n} Harness skills in one plugin: pipelines, deployments, access control, "
        "feature flags and experimentation, database, platform, security, observability "
        "and AI agents."
    )


def marketplace_description(catalog: Catalog) -> str:
    n = len(catalog.skills)
    c = len(catalog.categories)
    return f"{n} Harness skills for AI coding agents, as {c} domain plugins."


def all_keywords(catalog: Catalog) -> list[str]:
    seen: list[str] = []
    for cat in catalog.categories:
        for kw in cat.keywords:
            if kw not in seen:
                seen.append(kw)
    return seen


# --------------------------------------------------------------------------
# Frontmatter parsing: a small YAML subset.
#
# Supports plain scalars, single-/double-quoted scalars, folded (">", ">-")
# and literal ("|", "|-") block scalars, and one level of nested mapping
# (a key with no inline value, followed by more-indented "key: value" lines).
# Anything else (lists, flow collections, deeper nesting) raises CatalogError.
# --------------------------------------------------------------------------

_KEY_RE = re.compile(r"^([A-Za-z0-9_.-]+):(?:[ \t](.*))?$")
_BLOCK_HEADER_RE = re.compile(r"^([>|])([+-]?)$")


def _line_indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def _parse_double_quoted(raw: str) -> str:
    escapes = {"n": "\n", "t": "\t", '"': '"', "\\": "\\", "/": "/", "r": "\r", "0": "\0"}
    out: list[str] = []
    i = 1
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == "\\":
            if i + 1 >= n:
                raise CatalogError(f"unterminated escape in double-quoted scalar: {raw!r}")
            nxt = raw[i + 1]
            if nxt not in escapes:
                raise CatalogError(f"unsupported escape '\\{nxt}' in double-quoted scalar: {raw!r}")
            out.append(escapes[nxt])
            i += 2
            continue
        if ch == '"':
            if raw[i + 1 :].strip() != "":
                raise CatalogError(f"content after closing quote: {raw!r}")
            return "".join(out)
        out.append(ch)
        i += 1
    raise CatalogError(f"unterminated double-quoted scalar: {raw!r}")


def _parse_single_quoted(raw: str) -> str:
    out: list[str] = []
    i = 1
    n = len(raw)
    while i < n:
        ch = raw[i]
        if ch == "'":
            if i + 1 < n and raw[i + 1] == "'":
                out.append("'")
                i += 2
                continue
            if raw[i + 1 :].strip() != "":
                raise CatalogError(f"content after closing quote: {raw!r}")
            return "".join(out)
        out.append(ch)
        i += 1
    raise CatalogError(f"unterminated single-quoted scalar: {raw!r}")


def _block_scalar_lines(lines: list[str], start: int, base_indent: int) -> tuple[list[str], int]:
    """Collect the raw lines (blank or indented more than base_indent) belonging
    to a block scalar starting at `start`. Returns (raw_lines, next_index)."""
    raw: list[str] = []
    i = start
    n = len(lines)
    while i < n:
        line = lines[i]
        if line.strip() == "":
            raw.append(line)
            i += 1
            continue
        if _line_indent(line) <= base_indent:
            break
        raw.append(line)
        i += 1
    return raw, i


def _parse_block_scalar(lines: list[str], start: int, base_indent: int, header: str) -> tuple[str, int]:
    m = _BLOCK_HEADER_RE.match(header)
    if not m:
        raise CatalogError(f"unsupported block scalar header: {header!r}")
    style, chomp = m.group(1), m.group(2)

    raw, next_i = _block_scalar_lines(lines, start, base_indent)
    non_blank_indents = [_line_indent(l) for l in raw if l.strip() != ""]
    if not non_blank_indents:
        return "", next_i
    content_indent = min(non_blank_indents)
    dedented = [l[content_indent:] if l.strip() != "" else "" for l in raw]

    trailing_blanks = 0
    core = list(dedented)
    while core and core[-1] == "":
        core.pop()
        trailing_blanks += 1

    if style == "|":
        body = "\n".join(core)
    else:
        paragraphs: list[str] = []
        buf: list[str] = []
        for line in core:
            if line == "":
                paragraphs.append(" ".join(buf))
                buf = []
            else:
                buf.append(line)
        paragraphs.append(" ".join(buf))
        body = "\n".join(paragraphs)

    if chomp == "-":
        return body, next_i
    if chomp == "+":
        return body + ("\n" * (trailing_blanks + 1)), next_i
    return body + "\n", next_i  # clip (default)


_PLAIN_SCALAR_BAD_START = "@`&*!%#|>"


def _reject_unquotable_plain_scalar(rest: str) -> None:
    """A plain (unquoted) scalar that a real YAML parser would not read the
    way this value implies -- it would end the mapping value early (": "),
    start a comment (" #" or trailing ":"), or begin with a character YAML
    reserves and cannot start a plain scalar with."""
    hint = "quote the value or use a block scalar"
    if ": " in rest:
        raise CatalogError(f"plain scalar contains ': ', {hint}: {rest!r}")
    if rest.endswith(":"):
        raise CatalogError(f"plain scalar ends with ':', {hint}: {rest!r}")
    if " #" in rest:
        raise CatalogError(f"plain scalar contains ' #', {hint}: {rest!r}")
    if rest and rest[0] in _PLAIN_SCALAR_BAD_START:
        raise CatalogError(f"plain scalar starts with reserved character {rest[0]!r}, {hint}: {rest!r}")
    if rest.startswith("? ") or rest.startswith(": "):
        raise CatalogError(f"plain scalar starts with {rest[:2]!r}, {hint}: {rest!r}")


def _parse_scalar(rest: str) -> str:
    if rest.startswith('"'):
        return _parse_double_quoted(rest)
    if rest.startswith("'"):
        return _parse_single_quoted(rest)
    if rest.startswith("[") or rest.startswith("{"):
        raise CatalogError(f"flow collections are not supported: {rest!r}")
    if rest.startswith("- ") or rest == "-":
        raise CatalogError(f"list values are not supported: {rest!r}")
    _reject_unquotable_plain_scalar(rest)
    return rest


def _parse_level(
    lines: list[str], start: int, base_indent: int, depth: int
) -> tuple[dict[str, object], int]:
    mapping: dict[str, object] = {}
    i = start
    n = len(lines)
    while i < n:
        raw_line = lines[i]
        if raw_line.strip() == "":
            i += 1
            continue
        indent = _line_indent(raw_line)
        if indent < base_indent:
            break
        if indent > base_indent:
            raise CatalogError(f"unexpected indentation: {raw_line!r}")

        m = _KEY_RE.match(raw_line[base_indent:])
        if not m:
            raise CatalogError(f"cannot parse frontmatter line: {raw_line!r}")
        key, rest = m.group(1), (m.group(2) or "").strip()
        i += 1

        if key in mapping:
            raise CatalogError(f"duplicate key {key!r} in frontmatter")

        if rest == "":
            j = i
            while j < n and lines[j].strip() == "":
                j += 1
            next_indent = _line_indent(lines[j]) if j < n else -1
            if next_indent > base_indent:
                if lines[j].lstrip().startswith("- "):
                    raise CatalogError(f"list values are not supported for key {key!r}")
                if depth >= 1:
                    raise CatalogError(f"nested mapping deeper than one level at key {key!r}")
                nested, i = _parse_level(lines, j, next_indent, depth + 1)
                mapping[key] = nested
            else:
                mapping[key] = ""
        elif rest[0] in ">|":
            mapping[key], i = _parse_block_scalar(lines, i, base_indent, rest)
        else:
            mapping[key] = _parse_scalar(rest)
    return mapping, i


def parse_frontmatter(text: str) -> dict[str, object]:
    lines = text.split("\n")
    if not lines or lines[0].rstrip("\r") != "---":
        raise CatalogError("missing frontmatter: file must start with '---'")
    end = None
    for idx in range(1, len(lines)):
        if lines[idx].rstrip("\r") == "---":
            end = idx
            break
    if end is None:
        raise CatalogError("missing closing '---' for frontmatter")

    body = [l.rstrip("\r") for l in lines[1:end]]
    mapping, _ = _parse_level(body, 0, 0, 0)
    return mapping


# --------------------------------------------------------------------------
# Catalog loading / validation
# --------------------------------------------------------------------------


def _fold_description(value: object) -> str:
    if not isinstance(value, str):
        return ""
    return re.sub(r"\s+", " ", value).strip()


def load_catalog(root: Path | None = None) -> Catalog:
    root = Path(root).resolve() if root is not None else repo_root()
    errors: list[str] = []

    categories_path = root / "skills" / "categories.json"
    if not categories_path.is_file():
        raise CatalogError("skills/categories.json: file not found")

    raw_text = categories_path.read_text(encoding="utf-8")
    try:
        config = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CatalogError(f"skills/categories.json: invalid JSON: {exc}")

    if not isinstance(config, dict) or set(config.keys()) != {"version", "categories"}:
        found = sorted(config.keys()) if isinstance(config, dict) else type(config).__name__
        raise CatalogError(
            f"skills/categories.json: top-level keys must be exactly 'version' and 'categories', found {found}"
        )

    version = config["version"]
    if not isinstance(version, str) or not SEMVER_RE.match(version):
        errors.append(f"skills/categories.json: top-level 'version' must be semver X.Y.Z, found {version!r}")

    cats_raw = config["categories"]
    if not isinstance(cats_raw, list):
        raise CatalogError("skills/categories.json: 'categories' must be a list")

    # Pass 1: every dict entry with a string "dir", regardless of whether the
    # rest of the entry validates -- used so an unrelated field error on one
    # category doesn't also spuriously flag its directory as "unknown".
    listed_dirs = {e["dir"] for e in cats_raw if isinstance(e, dict) and isinstance(e.get("dir"), str)}

    seen_dirs: dict[str, int] = {}
    seen_plugins: dict[str, int] = {}
    cat_entries: list[dict] = []
    for idx, entry in enumerate(cats_raw):
        ctx = f"skills/categories.json: categories[{idx}]"
        if not isinstance(entry, dict):
            errors.append(f"{ctx}: must be an object")
            continue
        keys = set(entry.keys())
        if keys != set(CATEGORY_KEYS):
            missing = sorted(set(CATEGORY_KEYS) - keys)
            extra = sorted(keys - set(CATEGORY_KEYS))
            detail = []
            if missing:
                detail.append(f"missing {missing}")
            if extra:
                detail.append(f"unexpected {extra}")
            errors.append(f"{ctx}: must have exactly keys {sorted(CATEGORY_KEYS)}, {'; '.join(detail)}")
            continue

        ok = True
        for k in ("dir", "plugin", "title", "description", "category"):
            if not isinstance(entry[k], str):
                errors.append(f"{ctx}.{k}: must be a string")
                ok = False
        if not isinstance(entry["keywords"], list) or not all(isinstance(x, str) for x in entry["keywords"]):
            errors.append(f"{ctx}.keywords: must be a list of strings")
            ok = False
        if not ok:
            continue

        d, p = entry["dir"], entry["plugin"]
        seen_dirs[d] = seen_dirs.get(d, 0) + 1
        seen_plugins[p] = seen_plugins.get(p, 0) + 1
        if not p.startswith("harness-"):
            errors.append(f"{ctx}: plugin name {p!r} must start with 'harness-'")
        cat_entries.append(entry)

    for d, cnt in seen_dirs.items():
        if cnt > 1:
            errors.append(f"skills/categories.json: duplicate category dir {d!r}")
    for p, cnt in seen_plugins.items():
        if cnt > 1:
            errors.append(f"skills/categories.json: duplicate plugin name {p!r}")

    skills_dir = root / "skills"
    if not skills_dir.is_dir():
        raise CatalogError("skills: directory not found")

    actual_dirs = {p.name for p in skills_dir.iterdir() if p.is_dir()}
    for d in sorted(actual_dirs - listed_dirs):
        errors.append(f"skills/{d}: directory is not listed in skills/categories.json")

    all_skill_names: dict[str, str] = {}
    categories: list[Category] = []

    for entry in cat_entries:
        d = entry["dir"]
        cat_dir = skills_dir / d
        if not cat_dir.is_dir():
            errors.append(f"skills/categories.json: category dir 'skills/{d}' does not exist")
            continue

        skill_names = sorted(p.name for p in cat_dir.iterdir() if p.is_dir())
        if not skill_names:
            errors.append(f"skills/{d}: category has no skills")

        skills_list: list[Skill] = []
        for sname in skill_names:
            rel_path = f"skills/{d}/{sname}"
            skill_md = cat_dir / sname / "SKILL.md"
            if not skill_md.is_file():
                errors.append(f"{rel_path}: missing SKILL.md")
                continue

            try:
                fm = parse_frontmatter(skill_md.read_text(encoding="utf-8"))
            except CatalogError as exc:
                errors.append(f"{rel_path}/SKILL.md: {exc}")
                continue

            fname = fm.get("name")
            if fname != sname:
                errors.append(
                    f"{rel_path}/SKILL.md: frontmatter name {fname!r} does not match directory name {sname!r}"
                )

            if sname in all_skill_names:
                errors.append(
                    f"{rel_path}/SKILL.md: duplicate skill name {sname!r} also used in "
                    f"skills/{all_skill_names[sname]}"
                )
            else:
                all_skill_names[sname] = d

            description_raw = fm.get("description")
            if not isinstance(description_raw, str) or description_raw.strip() == "":
                errors.append(f"{rel_path}/SKILL.md: 'description' is missing")
                description_raw = ""

            metadata = fm.get("metadata")
            if not isinstance(metadata, dict):
                errors.append(f"{rel_path}/SKILL.md: 'metadata' mapping is missing")
                metadata = {}

            summary = metadata.get("summary")
            if not isinstance(summary, str) or summary == "":
                errors.append(f"{rel_path}/SKILL.md: metadata.summary is missing")
                summary = ""
            elif len(summary) > SUMMARY_MAX:
                errors.append(
                    f"{rel_path}/SKILL.md: metadata.summary exceeds {SUMMARY_MAX} characters ({len(summary)})"
                )
            if isinstance(summary, str) and "|" in summary:
                errors.append(f"{rel_path}/SKILL.md: metadata.summary must not contain '|'")

            version_field = metadata.get("version")
            if not isinstance(version_field, str) or version_field == "":
                errors.append(f"{rel_path}/SKILL.md: metadata.version is missing")
                version_field = ""

            mcp_server = metadata.get("mcp-server")
            if not isinstance(mcp_server, str) or mcp_server == "":
                errors.append(f"{rel_path}/SKILL.md: metadata.mcp-server is missing")
                mcp_server = ""

            compatibility = fm.get("compatibility")
            if not isinstance(compatibility, str) or compatibility.strip() == "":
                errors.append(f"{rel_path}/SKILL.md: 'compatibility' is missing")
                compatibility = ""

            license_ = fm.get("license")
            if not isinstance(license_, str) or license_.strip() == "":
                errors.append(f"{rel_path}/SKILL.md: 'license' is missing")
                license_ = ""

            skills_list.append(
                Skill(
                    name=sname,
                    category=d,
                    path=rel_path,
                    description=_fold_description(description_raw),
                    summary=summary,
                    version=version_field,
                    mcp_server=mcp_server,
                    compatibility=compatibility,
                    license=license_,
                )
            )

        categories.append(
            Category(
                dir=d,
                plugin=entry["plugin"],
                title=entry["title"],
                description=entry["description"],
                category=entry["category"],
                keywords=tuple(entry["keywords"]),
                skills=tuple(skills_list),
            )
        )

    if errors:
        raise CatalogError("\n".join(sorted(set(errors))))

    return Catalog(root=root, version=version, categories=tuple(categories))
