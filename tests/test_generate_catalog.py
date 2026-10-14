#!/usr/bin/env python3
"""Tests for scripts/generate_catalog.py: CLI outputs, exit codes, marker handling.

Usage: python3 -m unittest tests/test_generate_catalog.py [-v]
Run from the repo root.

Two kinds of coverage:

- GenerateCatalogCliTestCase builds a minimal temp tree (one category, one
  skill, the four marker-bearing doc files) and runs generate_catalog.main()
  against it via unittest.mock.patch.object(catalog_lib, "repo_root", ...).
  _discover_generators() globs the real scripts/gen_*.py by the script's own
  location, so those generators run for real against the temp catalog -- this
  exercises the full default/--check/error paths end to end.
- The remaining classes check the real repo: render_all() against the files
  actually on disk, the content of skills.json and the generated doc tables,
  and _replace_marker_block() in isolation.
"""
from __future__ import annotations

import contextlib
import io
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import catalog_lib  # noqa: E402  (path set up above)
import generate_catalog  # noqa: E402

BEGIN = generate_catalog.BEGIN_MARKER
END = generate_catalog.END_MARKER

EXPECTED_GENERATED_RELPATHS = {
    ".claude-plugin/marketplace.json",
    ".cursor-plugin/marketplace.json",
    ".cursor-plugin/plugin.json",
    ".agents/plugins/marketplace.json",
    ".codex-plugin/plugin.json",
    "skills.json",
    "README.md",
    "AGENTS.md",
    ".cursor/rules/harness.mdc",
    ".github/copilot-instructions.md",
}


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _minimal_skill_md() -> str:
    return (
        "---\n"
        "name: demo-skill\n"
        "description: >-\n"
        "  Demo skill for generate_catalog tests. Use when verifying the skill\n"
        "  catalog pipeline end to end.\n"
        "metadata:\n"
        "  author: Harness\n"
        "  version: 1.0.0\n"
        "  mcp-server: harness-mcp-v2\n"
        "  summary: Demo skill used by generate_catalog tests\n"
        "license: Apache-2.0\n"
        "compatibility: No special requirements\n"
        "---\n\n"
        "# Demo Skill\n\n"
        "## Instructions\n\n"
        "1. Do the demo thing.\n"
    )


def _categories_json() -> str:
    data = {
        "version": "1.0.0",
        "categories": [
            {
                "dir": "demo",
                "plugin": "harness-demo",
                "title": "Demo Category",
                "description": "A demo category for generator tests.",
                "category": "ci-cd",
                "keywords": ["demo", "harness"],
            }
        ],
    }
    return json.dumps(data, indent=2) + "\n"


def _doc_with_marker(title: str) -> str:
    return f"# {title}\n\nIntro text.\n\n{BEGIN}\n{END}\n\nTrailing text.\n"


def _build_minimal_tree(root: Path) -> None:
    _write(root / "skills" / "categories.json", _categories_json())
    _write(root / "skills" / "demo" / "demo-skill" / "SKILL.md", _minimal_skill_md())
    _write(root / "README.md", _doc_with_marker("Harness Skills"))
    _write(root / "AGENTS.md", _doc_with_marker("Agents"))
    _write(root / ".cursor" / "rules" / "harness.mdc", _doc_with_marker("Cursor Rules"))
    _write(root / ".github" / "copilot-instructions.md", _doc_with_marker("Copilot Instructions"))


class GenerateCatalogCliTestCase(unittest.TestCase):
    """Runs generate_catalog.main() against a minimal temp tree."""

    def setUp(self):
        self._tmpdir_ctx = tempfile.TemporaryDirectory(prefix="gentests-catalog-")
        self.addCleanup(self._tmpdir_ctx.cleanup)
        self.root = Path(self._tmpdir_ctx.name).resolve()
        _build_minimal_tree(self.root)
        patcher = patch.object(catalog_lib, "repo_root", return_value=self.root)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _run_main(self, argv=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = generate_catalog.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_default_mode_writes_then_second_run_writes_nothing(self):
        code1, out1, err1 = self._run_main([])
        self.assertEqual(code1, 0)
        self.assertEqual(err1, "")
        self.assertIn("wrote 10 of 10 generated files", out1)
        for relpath in EXPECTED_GENERATED_RELPATHS:
            with self.subTest(relpath=relpath):
                self.assertTrue((self.root / relpath).is_file(), f"missing {relpath}")

        code2, out2, err2 = self._run_main([])
        self.assertEqual(code2, 0)
        self.assertEqual(err2, "")
        self.assertIn("wrote 0 of 10 generated files", out2)
        self.assertNotIn("wrote .", out2)
        self.assertNotIn("wrote skills.json", out2)
        self.assertNotIn("wrote README.md", out2)

    def test_check_returns_0_when_fresh(self):
        self._run_main([])
        code, out, err = self._run_main(["--check"])
        self.assertEqual(code, 0)
        self.assertEqual(err, "")
        self.assertIn("0 of 10 generated files stale", out)

    def test_check_returns_1_and_reports_stale_readme_after_edit(self):
        self._run_main([])
        readme_path = self.root / "README.md"
        text = readme_path.read_text(encoding="utf-8")
        mutated = text.replace("demo-skill", "demo-skill-mutated")
        self.assertNotEqual(mutated, text, "fixture README row did not contain the skill name")
        readme_path.write_text(mutated, encoding="utf-8")

        code, out, err = self._run_main(["--check"])
        self.assertEqual(code, 1)
        self.assertIn("stale: README.md", out)

    def test_check_returns_1_when_skills_json_deleted(self):
        self._run_main([])
        (self.root / "skills.json").unlink()

        code, out, err = self._run_main(["--check"])
        self.assertEqual(code, 1)
        self.assertIn("stale: skills.json", out)

    def test_returns_2_when_categories_json_is_invalid_json(self):
        (self.root / "skills" / "categories.json").write_text("{not valid json", encoding="utf-8")

        code, out, err = self._run_main([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("invalid JSON", err)

    def test_returns_2_when_agents_md_has_no_end_marker(self):
        agents_path = self.root / "AGENTS.md"
        text = agents_path.read_text(encoding="utf-8")
        mutated = text.replace(f"{END}\n", "")
        self.assertNotIn(END, mutated)
        agents_path.write_text(mutated, encoding="utf-8")

        code, out, err = self._run_main([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertIn("AGENTS.md", err)


class RealRepoRenderAllTestCase(unittest.TestCase):
    """render_all() against the real repo must equal what's on disk, byte for byte."""

    def test_render_all_matches_disk_and_covers_the_expected_paths(self):
        catalog = catalog_lib.load_catalog(REPO_ROOT)
        files = generate_catalog.render_all(catalog)

        self.assertEqual(set(files), EXPECTED_GENERATED_RELPATHS)

        for relpath, text in files.items():
            disk_path = REPO_ROOT / relpath
            with self.subTest(relpath=relpath):
                self.assertTrue(disk_path.is_file(), f"missing {relpath}")
                self.assertEqual(
                    text,
                    disk_path.read_text(encoding="utf-8"),
                    f"{relpath} on disk is stale relative to render_all()",
                )


class SkillsJsonContentTestCase(unittest.TestCase):
    """skills.json on disk must agree with the real skill tree and the Claude manifest."""

    @classmethod
    def setUpClass(cls):
        cls.skills_json = json.loads((REPO_ROOT / "skills.json").read_text(encoding="utf-8"))
        cls.claude_marketplace = json.loads(
            (REPO_ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )

    def test_plugin_skill_counts_sum_to_skill_md_count_on_disk(self):
        total_on_disk = len(list(REPO_ROOT.glob("skills/*/*/SKILL.md")))
        total_in_plugins = sum(len(p["skills"]) for p in self.skills_json["plugins"])
        self.assertEqual(total_in_plugins, total_on_disk)
        self.assertEqual(len(self.skills_json["skills"]), total_on_disk)

    def test_each_plugin_skills_match_on_disk_skill_dirs(self):
        for plugin in self.skills_json["plugins"]:
            dir_path = REPO_ROOT / plugin["dir"]
            with self.subTest(plugin=plugin["name"]):
                on_disk = sorted(
                    child.name
                    for child in dir_path.iterdir()
                    if child.is_dir() and (child / "SKILL.md").is_file()
                )
                self.assertEqual(sorted(plugin["skills"]), on_disk)

    def test_each_plugin_name_matches_claude_marketplace_entry_for_its_dir(self):
        claude_name_by_dir: dict[str, str] = {}
        for entry in self.claude_marketplace["plugins"]:
            skill_dirs = entry.get("skills", [])
            self.assertEqual(len(skill_dirs), 1, f"{entry.get('name')}: expected exactly one skills dir")
            rel_dir = skill_dirs[0]
            dir_name = rel_dir[len("./skills/") :] if rel_dir.startswith("./skills/") else rel_dir
            claude_name_by_dir[dir_name] = entry["name"]

        for plugin in self.skills_json["plugins"]:
            dir_name = plugin["dir"][len("skills/") :]
            with self.subTest(plugin=plugin["name"]):
                self.assertEqual(plugin["name"], claude_name_by_dir[dir_name])

    def test_every_skill_path_exists(self):
        for skill in self.skills_json["skills"]:
            skill_md = REPO_ROOT / skill["path"] / "SKILL.md"
            with self.subTest(skill=skill["name"]):
                self.assertTrue(skill_md.is_file(), f"missing {skill['path']}/SKILL.md")


def _extract_marker_block(text: str) -> str:
    begin = text.index(BEGIN) + len(BEGIN)
    end = text.index(END)
    return text[begin:end]


class DocTableContentTestCase(unittest.TestCase):
    """The marked skill table in each doc file must have exactly one row per skill."""

    @classmethod
    def setUpClass(cls):
        cls.catalog = catalog_lib.load_catalog(REPO_ROOT)
        cls.all_skill_names = sorted(s.name for s in cls.catalog.skills)

    def test_readme_rows_link_each_skills_skill_md(self):
        text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
        block = _extract_marker_block(text)
        rows = re.findall(r"\[([\w-]+)\]\((skills/[\w-]+/[\w-]+/SKILL\.md)\)", block)
        self.assertEqual(len(rows), len(self.all_skill_names))
        self.assertEqual(sorted(name for name, _ in rows), self.all_skill_names)
        skill_by_name = {s.name: s for s in self.catalog.skills}
        for name, path in rows:
            with self.subTest(skill=name):
                self.assertEqual(path, f"{skill_by_name[name].path}/SKILL.md")

    def test_other_doc_files_have_one_slash_skill_row_per_skill(self):
        for relpath in (
            "AGENTS.md",
            ".cursor/rules/harness.mdc",
            ".github/copilot-instructions.md",
        ):
            with self.subTest(relpath=relpath):
                text = (REPO_ROOT / relpath).read_text(encoding="utf-8")
                block = _extract_marker_block(text)
                rows = re.findall(r"\| `/([\w-]+)` \|", block)
                self.assertEqual(sorted(rows), self.all_skill_names)


class ReplaceMarkerBlockTestCase(unittest.TestCase):
    """Unit tests for generate_catalog._replace_marker_block in isolation."""

    def test_text_before_begin_and_after_end_is_kept_byte_for_byte(self):
        text = f"before\n{BEGIN}\nold body\n{END}\nafter\n"
        result = generate_catalog._replace_marker_block("doc.md", text, ["new", "body"])
        self.assertTrue(result.startswith(f"before\n{BEGIN}\n"))
        self.assertTrue(result.endswith(f"{END}\nafter\n"))

    def test_second_application_is_a_no_op(self):
        text = f"before\n{BEGIN}\nold\n{END}\nafter\n"
        once = generate_catalog._replace_marker_block("doc.md", text, ["x", "y"])
        twice = generate_catalog._replace_marker_block("doc.md", once, ["x", "y"])
        self.assertEqual(once, twice)

    def test_zero_begin_markers_raises(self):
        text = f"no markers here\n{END}\n"
        with self.assertRaises(generate_catalog.TreeError):
            generate_catalog._replace_marker_block("doc.md", text, ["x"])

    def test_two_begin_markers_raises(self):
        text = f"{BEGIN}\nbody\n{BEGIN}\nbody2\n{END}\n"
        with self.assertRaises(generate_catalog.TreeError):
            generate_catalog._replace_marker_block("doc.md", text, ["x"])

    def test_end_before_begin_raises(self):
        text = f"{END}\nbody\n{BEGIN}\n"
        with self.assertRaises(generate_catalog.TreeError):
            generate_catalog._replace_marker_block("doc.md", text, ["x"])

    def test_file_without_trailing_newline_keeps_that(self):
        text = f"before\n{BEGIN}\nold\n{END}\nafter"
        result = generate_catalog._replace_marker_block("doc.md", text, ["new"])
        self.assertFalse(result.endswith("\n"))
        self.assertTrue(result.endswith("after"))


if __name__ == "__main__":
    unittest.main()
