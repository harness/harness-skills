#!/usr/bin/env python3
"""Tests for scripts/catalog_lib.py: frontmatter parsing and catalog loading.

Usage: python3 -m unittest tests/test_catalog_lib.py [-v]
Run from the repo root.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import catalog_lib as cl  # noqa: E402  (path set up above)

DEFAULT_CATEGORY = {
    "dir": "cat",
    "plugin": "harness-cat",
    "title": "Category",
    "description": "A test category",
    "category": "testing",
    "keywords": ["test"],
}

MINIMAL_SKILL = """---
name: a
description: A minimal skill used for catalog_lib tests.
metadata:
  author: Harness
  version: 1.0.0
  mcp-server: harness-mcp
  summary: A minimal skill for tests
license: Apache-2.0
compatibility: None
---

# A

Body.
"""


def categories_json(categories: list[dict], version: str = "1.0.0") -> str:
    return json.dumps({"version": version, "categories": categories})


class CatalogTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)

    def write(self, files: dict[str, str]) -> None:
        for rel, content in files.items():
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

    def minimal_tree(
        self,
        categories: list[dict] | None = None,
        version: str = "1.0.0",
        skill_md: str | None = None,
        skill_dir: str = "a",
        category_dir: str = "cat",
    ) -> None:
        cats = categories if categories is not None else [dict(DEFAULT_CATEGORY)]
        self.write({"skills/categories.json": categories_json(cats, version)})
        self.write({f"skills/{category_dir}/{skill_dir}/SKILL.md": skill_md if skill_md is not None else MINIMAL_SKILL})

    def load(self) -> cl.Catalog:
        return cl.load_catalog(self.root)


class TestCategoriesJsonValidation(CatalogTestCase):
    def test_version_too_short_is_rejected(self):
        self.minimal_tree(version="1.0")
        with self.assertRaisesRegex(cl.CatalogError, "semver"):
            self.load()

    def test_version_with_prefix_is_rejected(self):
        self.minimal_tree(version="v1.1")
        with self.assertRaisesRegex(cl.CatalogError, "semver"):
            self.load()

    def test_extra_key_in_category_entry_is_rejected(self):
        cat = dict(DEFAULT_CATEGORY)
        cat["extra"] = "nope"
        self.minimal_tree(categories=[cat])
        with self.assertRaisesRegex(cl.CatalogError, "unexpected"):
            self.load()

    def test_category_dir_duplicated_in_json_is_rejected(self):
        cat1 = dict(DEFAULT_CATEGORY)
        cat2 = dict(DEFAULT_CATEGORY)
        cat2["plugin"] = "harness-cat2"
        self.minimal_tree(categories=[cat1, cat2])
        with self.assertRaisesRegex(cl.CatalogError, "duplicate category dir"):
            self.load()

    def test_plugin_not_prefixed_harness_is_rejected(self):
        cat = dict(DEFAULT_CATEGORY)
        cat["plugin"] = "my-plugin"
        self.minimal_tree(categories=[cat])
        with self.assertRaisesRegex(cl.CatalogError, "must start with 'harness-'"):
            self.load()

    def test_unlisted_skills_dir_is_rejected(self):
        self.minimal_tree()
        self.write({"skills/extra/dummy.txt": "x"})
        with self.assertRaisesRegex(cl.CatalogError, "is not listed"):
            self.load()

    def test_listed_dir_that_does_not_exist_is_rejected(self):
        cat = dict(DEFAULT_CATEGORY)
        cat["dir"] = "ghost"
        self.write({"skills/categories.json": categories_json([cat])})
        with self.assertRaisesRegex(cl.CatalogError, "does not exist"):
            self.load()

    def test_empty_category_is_rejected(self):
        self.write({"skills/categories.json": categories_json([dict(DEFAULT_CATEGORY)])})
        self.write({"skills/cat/.keep": ""})
        with self.assertRaisesRegex(cl.CatalogError, "has no skills"):
            self.load()


class TestSkillFrontmatterValidation(CatalogTestCase):
    def test_name_mismatch_with_directory_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace("name: a", "name: b")
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "does not match directory name"):
            self.load()

    def test_summary_over_120_chars_is_rejected(self):
        long_summary = ("word " * 30).strip()
        self.assertGreater(len(long_summary), 120)
        skill_md = MINIMAL_SKILL.replace("summary: A minimal skill for tests", f"summary: {long_summary}")
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "exceeds 120 characters"):
            self.load()

    def test_summary_with_pipe_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace(
            "summary: A minimal skill for tests",
            "summary: A minimal skill | not allowed",
        )
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "must not contain '\\|'"):
            self.load()

    def test_blank_compatibility_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace("compatibility: None", "compatibility:")
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "'compatibility' is missing"):
            self.load()

    def test_blank_license_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace("license: Apache-2.0", "license:")
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "'license' is missing"):
            self.load()

    def test_duplicate_frontmatter_key_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace(
            "license: Apache-2.0\n",
            "license: Apache-2.0\nlicense: MIT\n",
        )
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "duplicate key"):
            self.load()

    def test_plain_scalar_with_colon_space_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace(
            "summary: A minimal skill for tests",
            "summary: A minimal: skill for tests",
        )
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "plain scalar contains"):
            self.load()

    def test_plain_scalar_with_space_hash_is_rejected(self):
        skill_md = MINIMAL_SKILL.replace(
            "summary: A minimal skill for tests",
            "summary: A minimal skill #not-a-comment",
        )
        self.minimal_tree(skill_md=skill_md)
        with self.assertRaisesRegex(cl.CatalogError, "plain scalar contains"):
            self.load()


class TestMinimalValidTree(CatalogTestCase):
    def test_minimal_valid_tree_loads(self):
        self.minimal_tree()
        catalog = self.load()
        self.assertEqual(catalog.version, "1.0.0")
        self.assertEqual(len(catalog.skills), 1)
        skill = catalog.skills[0]
        self.assertEqual(skill.name, "a")
        self.assertEqual(skill.category, "cat")
        self.assertEqual(skill.license, "Apache-2.0")
        self.assertEqual(skill.compatibility, "None")


class TestParseFrontmatterScalarForms(unittest.TestCase):
    def test_double_quoted_value_with_colon_space_parses(self):
        text = '---\nname: a\ndescription: "a: b"\n---\n'
        fm = cl.parse_frontmatter(text)
        self.assertEqual(fm["description"], "a: b")

    def test_folded_block_scalar_with_colon_space_parses(self):
        text = "---\nname: a\ndescription: >-\n  a: b\n---\n"
        fm = cl.parse_frontmatter(text)
        self.assertEqual(fm["description"], "a: b")


class TestRealRepoCategoriesJsonVersion(unittest.TestCase):
    def test_version_is_semver(self):
        path = REPO_ROOT / "skills" / "categories.json"
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.assertRegex(data["version"], r"^\d+\.\d+\.\d+$")


if __name__ == "__main__":
    unittest.main()
