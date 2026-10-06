"""Regression coverage: relative-link integrity across the FME skill/reference
dependency graph (PR27 / FME-18539).

Scope: this validates that links between checked-in markdown docs actually
resolve (file exists, anchor exists). It does NOT execute any skill, call
any MCP tool/CLI, or evaluate LLM behavior.
"""
import unittest
from pathlib import Path

from tests._mdutil import REPO_ROOT, iter_markdown_links, get_heading_slugs

FME_SKILL_NAMES = [
    "discover-feature-flags", "explain-flag", "create-feature-flag",
    "update-flag-targeting", "manage-flag-lifecycle", "manage-segments",
    "cleanup-feature-flags", "fme-pipeline", "manage-experiments",
    "create-experiment", "review-experiment-results", "choose-metric",
    "create-metric", "instrument-metric",
]


def _is_external_or_special(target: str) -> bool:
    target = target.split("#", 1)[0]
    return bool(
        target.startswith("http://")
        or target.startswith("https://")
        or target.startswith("mailto:")
    )


def _discover_fme_markdown_files() -> set[Path]:
    """BFS over the FME skills' markdown files and whatever they link to
    locally, so the test covers the dependency graph as it actually exists
    on disk rather than a hardcoded file list."""
    seeds = []
    for name in FME_SKILL_NAMES:
        skill_md = REPO_ROOT / "skills" / name / "SKILL.md"
        if skill_md.exists():
            seeds.append(skill_md)

    seen: set[Path] = set()
    queue = list(seeds)
    while queue:
        current = queue.pop()
        if current in seen or not current.exists():
            continue
        seen.add(current)
        if current.suffix != ".md":
            continue
        for _, _, target in iter_markdown_links(current):
            if _is_external_or_special(target):
                continue
            target_path = target.split("#", 1)[0]
            resolved = (current.parent / target_path).resolve()
            if resolved.suffix == ".md" and REPO_ROOT in resolved.parents:
                queue.append(resolved)
    return seen


class FmeDocLinkGraphTests(unittest.TestCase):
    """Walks the FME skill/reference dependency graph starting from each
    FME skill's SKILL.md and checks every relative link it finds."""

    @classmethod
    def setUpClass(cls):
        cls.files = sorted(_discover_fme_markdown_files())

    def test_all_fme_skill_docs_found(self):
        for name in FME_SKILL_NAMES:
            with self.subTest(skill=name):
                self.assertIn(REPO_ROOT / "skills" / name / "SKILL.md", self.files)

    def test_relative_links_resolve_to_existing_files(self):
        failures = []
        for md_file in self.files:
            for line_no, text, target in iter_markdown_links(md_file):
                if _is_external_or_special(target):
                    continue
                target_path, _, anchor = target.partition("#")
                resolved = (md_file.parent / target_path).resolve()
                if not resolved.exists():
                    rel = md_file.relative_to(REPO_ROOT)
                    failures.append(
                        f"{rel}:{line_no} link [{text}]({target}) -> "
                        f"missing file {resolved}"
                    )
        self.assertEqual(
            [], failures, "Broken relative links:\n" + "\n".join(failures)
        )

    def test_anchors_resolve_to_existing_headings(self):
        failures = []
        for md_file in self.files:
            for line_no, text, target in iter_markdown_links(md_file):
                if _is_external_or_special(target):
                    continue
                target_path, sep, anchor = target.partition("#")
                if not sep or not anchor:
                    continue
                resolved = (md_file.parent / target_path).resolve() if target_path else md_file
                if not resolved.exists() or resolved.suffix != ".md":
                    continue  # covered by the file-existence test
                slugs = get_heading_slugs(resolved)
                if anchor.lower() not in slugs:
                    rel = md_file.relative_to(REPO_ROOT)
                    failures.append(
                        f"{rel}:{line_no} link [{text}]({target}) -> "
                        f"no heading matching '#{anchor}' in {resolved.name}"
                    )
        self.assertEqual(
            [], failures, "Broken anchors:\n" + "\n".join(failures)
        )


class CreateExperimentEntrypointTests(unittest.TestCase):
    """The compatibility entrypoint delegates creation to manage-experiments;
    it must not duplicate its orchestration or depend on removed skills."""

    def setUp(self):
        self.entry = REPO_ROOT / "skills" / "create-experiment" / "SKILL.md"
        self.assertTrue(self.entry.exists(), "create-experiment entrypoint is missing")
        self.text = self.entry.read_text(encoding="utf-8")

    def test_delegates_are_named_and_exist(self):
        delegates = ["manage-experiments", "review-experiment-results"]
        missing_mentions = [d for d in delegates if d not in self.text]
        missing_dirs = [
            d for d in delegates
            if not (REPO_ROOT / "skills" / d / "SKILL.md").exists()
        ]
        self.assertEqual(
            [], missing_mentions,
            f"create-experiment no longer mentions delegate skill(s): {missing_mentions}",
        )
        self.assertEqual(
            [], missing_dirs,
            f"Delegate skill(s) referenced by create-experiment are missing: {missing_dirs}",
        )

    def test_readme_links_to_existing_entrypoint(self):
        readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(
            "skills/create-experiment/SKILL.md", readme,
            "README.md index no longer links to the create-experiment entrypoint",
        )


if __name__ == "__main__":
    unittest.main()
