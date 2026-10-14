#!/usr/bin/env python3
"""Render Codex's umbrella plugin manifests (.agents/plugins/ + .codex-plugin/).

Usage: `render(catalog)` returns {relative_path: text}; consumed by
scripts/generate_catalog.py, which writes the result to disk. Run this
file directly to print the rendered files to stdout for inspection:

    scripts/gen_codex.py

Codex looks for a marketplace manifest in order: `.agents/plugins/marketplace.json`,
`.agents/plugins/api_marketplace.json`, `.claude-plugin/marketplace.json`,
`.cursor-plugin/marketplace.json` (first match wins). For a plugin's own
manifest it checks `.codex-plugin/`, `.claude-plugin/`, `.cursor-plugin/`
(a manifest on disk always wins over marketplace entry fields), and the
marketplace entry name must equal the on-disk manifest name. Skills are
discovered by recursively scanning the manifest's `skills` path to depth 6.
So, like Cursor, all 71 skills ship as one umbrella plugin rooted at the
repo, pointed at `./skills/`.
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

_CATEGORY = "Developer tools"


def render(catalog: Catalog) -> dict[str, str]:
    description = umbrella_description(catalog)

    marketplace = {
        "name": MARKETPLACE_NAME,
        "interface": {"displayName": UMBRELLA_DISPLAY_NAME},
        "plugins": [
            {
                "name": UMBRELLA_NAME,
                "source": {"source": "local", "path": "./"},
                "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                "category": _CATEGORY,
            },
        ],
    }

    plugin = {
        "name": UMBRELLA_NAME,
        "version": catalog.version,
        "description": description,
        "author": {"name": AUTHOR},
        "repository": REPOSITORY,
        "license": LICENSE,
        "keywords": all_keywords(catalog),
        "skills": "./skills/",
        "interface": {
            "displayName": UMBRELLA_DISPLAY_NAME,
            "shortDescription": "Harness pipelines, deployments, feature flags, security and more",
            "developerName": AUTHOR,
            "category": _CATEGORY,
            "websiteUrl": "https://www.harness.io",
        },
    }

    return {
        ".agents/plugins/marketplace.json": render_json(marketplace),
        ".codex-plugin/plugin.json": render_json(plugin),
    }


if __name__ == "__main__":
    from catalog_lib import load_catalog

    for path, text in render(load_catalog()).items():
        print(f"--- {path} ---")
        print(text, end="")
