#!/usr/bin/env python3
"""Render Cursor's umbrella plugin manifests (.cursor-plugin/).

Usage: `render(catalog)` returns {relative_path: text}; consumed by
scripts/generate_catalog.py, which writes the result to disk. Run this
file directly to print the rendered files to stdout for inspection:

    scripts/gen_cursor.py

Cursor reads `.cursor-plugin/marketplace.json` before
`.claude-plugin/marketplace.json`, ignores entry-level `strict`/`skills`,
and takes skills only from the plugin's own `.cursor-plugin/plugin.json`,
scanning each listed dir one level deep (`<dir>/<skill>/SKILL.md`). So all
71 skills ship as one umbrella plugin rooted at the repo, with the nine
category dirs listed explicitly.
"""
from __future__ import annotations

from catalog_lib import (
    AUTHOR,
    Catalog,
    LICENSE,
    MARKETPLACE_NAME,
    REPOSITORY,
    UMBRELLA_DISPLAY_NAME,
    UMBRELLA_NAME,
    all_keywords,
    render_json,
    umbrella_description,
)


def render(catalog: Catalog) -> dict[str, str]:
    description = umbrella_description(catalog)

    marketplace = {
        "name": MARKETPLACE_NAME,
        "owner": {"name": AUTHOR},
        "metadata": {"description": description},
        "plugins": [
            {"name": UMBRELLA_NAME, "source": ".", "description": description},
        ],
    }

    plugin = {
        "name": UMBRELLA_NAME,
        "displayName": UMBRELLA_DISPLAY_NAME,
        "version": catalog.version,
        "description": description,
        "author": {"name": AUTHOR},
        "repository": REPOSITORY,
        "license": LICENSE,
        "keywords": all_keywords(catalog),
        "skills": [f"./skills/{cat.dir}" for cat in catalog.categories],
    }

    return {
        ".cursor-plugin/marketplace.json": render_json(marketplace),
        ".cursor-plugin/plugin.json": render_json(plugin),
    }


if __name__ == "__main__":
    from catalog_lib import load_catalog

    for path, text in render(load_catalog()).items():
        print(f"--- {path} ---")
        print(text, end="")
