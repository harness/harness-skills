#!/usr/bin/env python3
"""Tests for scripts/check_links.py: links, anchors and backticked path mentions.

Usage: python3 -m unittest tests/test_check_links.py [-v]
Run from the repo root.
"""
from __future__ import annotations

import contextlib
import io
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import check_links  # noqa: E402  (path set up above)

REF = "# Ref\n\n## Intro\n\nText.\n"


def run_main(root: Path, discover: bool = False) -> tuple[int, str]:
    """Run main() against root; return (exit code, stdout).

    By default checks every Markdown file under root (fixture trees are not git
    repos); discover=True uses main()'s own file discovery.
    """
    argv = ["--root", str(root)] if discover else ["--root", str(root), str(root)]
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = check_links.main(argv)
    return code, out.getvalue()


class TreeCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write(self, files: dict[str, str]) -> None:
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def skill(self, body: str, extra: dict[str, str] | None = None) -> None:
        """skills/cat/a/SKILL.md with the given body, plus extra files."""
        self.write({"skills/cat/a/SKILL.md": body, **(extra or {})})


class TestMentions(TreeCase):
    def test_resolving_mention_passes(self):
        self.skill("See `references/ref.md` first.\n", {"skills/cat/a/references/ref.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=1", out)
        self.assertIn("broken=0", out)

    def test_missing_mention_fails(self):
        self.skill("See `references/nope.md` first.\n")
        code, out = run_main(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("skills/cat/a/SKILL.md:1 -> references/nope.md (missing file)", out)

    def test_bad_anchor_fails_and_good_anchor_passes(self):
        self.skill(
            "Good `references/ref.md#intro`.\nBad `references/ref.md#nope`.\n",
            {"skills/cat/a/references/ref.md": REF},
        )
        code, out = run_main(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("skills/cat/a/SKILL.md:2 -> references/ref.md#nope (missing anchor)", out)
        self.assertNotIn("SKILL.md:1 ", out)
        self.assertIn("broken=1", out)

    def test_mention_in_fenced_block_is_ignored(self):
        self.skill("```\n`references/nope.md`\n```\n\n~~~\n`references/nope2.md`\n~~~\n")
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=0", out)

    def test_mention_in_frontmatter_is_ignored(self):
        self.skill("---\ndescription: see `references/nope.md`\n---\n\n# A\n")
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=0", out)

    def test_placeholder_span_is_ignored(self):
        self.skill(
            "`skills/<category>/<skill>/references/x.md`\n"
            "`references/*.md`\n"
            "`references/{a,b}.md`\n"
            "`references/ref.md` and `src/main.py`\n",
            {"skills/cat/a/references/ref.md": REF},
        )
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=1", out)

    def test_span_with_extra_text_is_not_a_mention(self):
        self.skill("Read `see references/nope.md` and `references/nope.md first`.\n")
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=0", out)

    def test_shared_references_resolve_from_repo_root(self):
        self.skill("Load `references/shared/tool-map.md`.\n", {"references/shared/tool-map.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=1", out)

    def test_references_file_mentioning_sibling_resolves_from_skill_folder(self):
        self.skill(
            "# A\n",
            {
                "skills/cat/a/references/one.md": "See `references/two.md`.\n",
                "skills/cat/a/references/two.md": REF,
            },
        )
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)

    def test_skill_references_form_resolves_from_category_folder(self):
        self.skill("Mirror `b/references/x.md`.\n", {"skills/cat/b/references/x.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("mentions-checked=1", out)

    def test_dotdot_mention_resolves_from_file(self):
        self.skill("Read `../b/references/x.md`.\n", {"skills/cat/b/references/x.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)


class TestCrossSkillWarnings(TreeCase):
    def test_cross_skill_mention_warns_but_exits_zero(self):
        self.skill("Reuse `skills/cat/b/references/x.md`.\n", {"skills/cat/b/references/x.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn(
            "warning: skills/cat/a/SKILL.md:1: path into another skill: skills/cat/b/references/x.md", out
        )
        self.assertIn("broken=0", out)
        self.assertIn("warnings=1", out)

    def test_cross_skill_link_warns_but_exits_zero(self):
        self.skill("Hand off to [b](../b/SKILL.md).\n", {"skills/cat/b/SKILL.md": "# B\n"})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("warning: skills/cat/a/SKILL.md:1: path into another skill: skills/cat/b/SKILL.md", out)
        self.assertIn("warnings=1", out)

    def test_cross_category_mention_warns(self):
        self.skill("Reuse `skills/other/c/references/x.md`.\n", {"skills/other/c/references/x.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("path into another skill: skills/other/c/references/x.md", out)

    def test_same_skill_and_shared_paths_do_not_warn(self):
        self.skill(
            "Own `references/ref.md`, shared `references/shared/s.md`, [link](references/ref.md).\n",
            {"skills/cat/a/references/ref.md": REF, "references/shared/s.md": REF},
        )
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("warnings=0", out)
        self.assertNotIn("warning:", out)

    def test_file_outside_a_skill_does_not_warn(self):
        self.write({"README.md": "See `skills/cat/a/references/x.md` and [a](skills/cat/a/SKILL.md).\n",
                    "skills/cat/a/SKILL.md": "# A\n", "skills/cat/a/references/x.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 0, out)
        self.assertIn("warnings=0", out)

    def test_broken_cross_skill_mention_is_an_error_not_a_warning(self):
        self.skill("Reuse `skills/cat/b/references/gone.md`.\n")
        code, out = run_main(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("(missing file)", out)
        self.assertNotIn("warning:", out)


class TestLinks(TreeCase):
    def test_markdown_links_still_checked(self):
        self.skill("[ok](references/ref.md#intro) [bad](references/gone.md) [anchor](#nope)\n",
                   {"skills/cat/a/references/ref.md": REF})
        code, out = run_main(self.root)
        self.assertEqual(code, 1, out)
        self.assertIn("references/gone.md (missing file)", out)
        self.assertIn("#nope (missing anchor)", out)
        self.assertIn("links-checked=2", out)
        self.assertIn("broken=2", out)


class TestUsageErrors(TreeCase):
    def test_nonexistent_path_argument_is_an_error(self):
        self.write({"README.md": "# A\n"})
        missing = self.root / "nope.md"
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = check_links.main(["--root", str(self.root), str(missing)])
        self.assertEqual(code, 2)
        self.assertIn(f"error: no such file or directory: {missing}", err.getvalue())

    def test_empty_file_set_is_an_error(self):
        # No files written: an empty root dir has nothing to check.
        with contextlib.redirect_stderr(io.StringIO()):
            code, out = run_main(self.root)
        self.assertEqual(code, 2, out)

    @unittest.skipIf(hasattr(os, "geteuid") and os.geteuid() == 0, "root ignores file permissions")
    def test_unreadable_file_is_reported_as_broken(self):
        self.skill("See [broken](nope.md).\n")
        path = self.root / "skills/cat/a/SKILL.md"
        path.chmod(0o000)
        try:
            code, out = run_main(self.root)
        finally:
            path.chmod(0o644)
        self.assertEqual(code, 1, out)
        self.assertIn("skills/cat/a/SKILL.md:0 ->  (unreadable:", out)
        self.assertIn("broken=1", out)


class TestGitDiscovery(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        subprocess.run(["git", "init", "-q"], cwd=self.root, check=True)

    def test_non_ascii_filename_is_discovered_via_git(self):
        (self.root / "café.md").write_text("# X\n\n[broken](nope.md)\n", encoding="utf-8")
        code, out = run_main(self.root, discover=True)
        self.assertEqual(code, 1, out)
        self.assertIn("café.md:3 -> nope.md (missing file)", out)


class TestRealRepo(unittest.TestCase):
    def test_real_repo_checks_clean(self):
        code, out = run_main(REPO_ROOT, discover=True)
        self.assertEqual(code, 0, out)
        self.assertIn("broken=0", out)
        self.assertRegex(out, r"mentions-checked=[1-9]")


if __name__ == "__main__":
    unittest.main()
