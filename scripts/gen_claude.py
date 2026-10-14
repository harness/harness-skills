#!/usr/bin/env python3
"""Render the Claude Code plugin marketplace manifest from the skill catalog.

Usage: imported by scripts/generate_catalog.py, which calls render(catalog).
Running this file directly prints the rendered marketplace.json to stdout.
"""
from __future__ import annotations

import catalog_lib


def render(catalog: catalog_lib.Catalog) -> dict[str, str]:
    plugins = []
    for cat in catalog.categories:
        plugins.append(
            {
                "name": cat.plugin,
                "displayName": cat.title,
                "description": f"{catalog_lib.count_label(len(cat.skills))}: {cat.description}",
                "source": ".",
                "strict": False,
                "skills": [f"./skills/{cat.dir}"],
                "category": cat.category,
                "keywords": list(cat.keywords),
                "author": {"name": catalog_lib.AUTHOR},
                "repository": catalog_lib.REPOSITORY,
                "license": catalog_lib.LICENSE,
            }
        )

    manifest = {
        "name": catalog_lib.MARKETPLACE_NAME,
        "owner": {"name": catalog_lib.AUTHOR},
        "metadata": {"description": catalog_lib.marketplace_description(catalog)},
        "plugins": plugins,
    }

    return {".claude-plugin/marketplace.json": catalog_lib.render_json(manifest)}


def main() -> None:
    catalog = catalog_lib.load_catalog()
    files = render(catalog)
    for text in files.values():
        print(text, end="")


if __name__ == "__main__":
    main()
