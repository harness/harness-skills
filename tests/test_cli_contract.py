"""Regression coverage: Harness unified CLI field/command contract as it may
appear in checked-in docs (PR27 / FME-18539).

This test does NOT check out, parse, or depend on
harness-unified-cli/pkg/spec/fme.spec.yaml at runtime. It encodes a small,
hand-reviewed snapshot of the fields/commands relevant to this repo's docs,
sourced from that spec at revision 8768ee9, as plain Python literals. If the
CLI contract changes, update MUTATION_FIELD_MAP / UNSUPPORTED_CLI_SNIPPETS
by hand after reviewing the new spec — this file intentionally avoids
copying the spec itself or re-implementing its validation logic.

Scope: scans inline and fenced CLI examples in FME skill/reference markdown
and checks two things:
  1. `--set <field>` mutation examples use the correct snake_case CLI field
     name, not a stale camelCase/API-body field name.
  2. Known-unsupported CLI syntax (e.g. `--set tags`, segment `key` actions)
     is not presented as a bare, positive, runnable example without an
     adjacent "unsupported" annotation.

A coverage assertion prevents an empty scan from passing unnoticed.
These checks do not prove compatibility with an installed or live CLI.
"""
import re
import unittest

from tests._mdutil import REPO_ROOT, iter_fenced_code_blocks, lines_outside_fences

# Source: harness-unified-cli/pkg/spec/fme.spec.yaml @ 8768ee9 (snapshot,
# hand-reviewed — not re-derived at test time).
MUTATION_FIELD_MAP = {
    "rolloutStatus.id": "rollout_status",
    "trafficAllocation": "traffic_allocation",
    "significanceThreshold": "significance_threshold",
    "isEnabled": "is_enabled",
}

# Patterns that are explicitly NOT supported by the CLI per the same
# reviewed spec snapshot.
UNSUPPORTED_CLI_SNIPPET_PATTERNS = [
    re.compile(r"--set\s+tags\b"),
    re.compile(r"segment:(?:list_keys|add_keys|remove_keys)\b"),
    # `segment:list_keys` is not a real noun:action — the generic
    # `harness execute` command's `--help` exits 0 for nonexistent
    # noun:action pairs too (it just prints generic execute flags), so a
    # successful --help is not evidence this command exists.
    re.compile(r"list\s+feature_flag\b[^\n]*(?:--tags\b|--rollout-status-id\b)"),
    re.compile(r"list\s+metric\b[^\n]*--id\s+\S+,\S+"),
    # `fme_experiment` update gates its file-body path to None server-side,
    # so `-f`/`--file` is unsupported there even though the CLI's global
    # help text advertises --file.
    re.compile(r"update\s+experiment\b[^\n]*(?:\s-f\b|--file\b)"),
    # File input does not merge a separate audit-comment body flag.
    re.compile(r"update\s+feature_flag:definition\b(?=[^\n]*(?:\s-f\b|--file\b))(?=[^\n]*--comment\b)"),
]

UNSUPPORTED_ANNOTATION_RE = re.compile(
    r"unsupported|not supported|rejected|no cli|not available|isn't valid|doesn't match",
    re.IGNORECASE,
)

CLI_LINE_RE = re.compile(r"\bharness\s+(?:list|get|create|update|delete|execute)\b")


def _all_markdown_files():
    files = set((REPO_ROOT / "references" / "fme").glob("*.md"))
    for path in (REPO_ROOT / "skills").glob("*/SKILL.md"):
        if "references/fme/tool-map.md" in path.read_text():
            files.update(path.parent.rglob("*.md"))
    return sorted(files)


def _cli_blocks_with_context():
    """Yield runnable-looking inline/fenced examples and local context."""
    for path in _all_markdown_files():
        lines = path.read_text(encoding="utf-8").splitlines()
        for line_no, line in lines_outside_fences(path):
            for code in re.findall(r"`([^`]+)`", line):
                if CLI_LINE_RE.search(code):
                    yield path, line_no, code, line
        for start_line, lang, code in iter_fenced_code_blocks(path):
            if not CLI_LINE_RE.search(code):
                continue
            window_start = max(0, start_line - 6)
            window_end = min(len(lines), start_line + code.count("\n") + 6)
            context = "\n".join(lines[window_start:window_end])
            yield path, start_line, code, context


class CliMutationFieldTests(unittest.TestCase):
    def test_scans_real_examples_including_tool_tables(self):
        examples = list(_cli_blocks_with_context())
        self.assertGreater(len(examples), 30)
        self.assertTrue(any(path.name == "tool-map.md" for path, *_ in examples))

    def test_set_examples_use_snake_case_cli_fields(self):
        failures = []
        for path, start_line, code, _ in _cli_blocks_with_context():
            for camel, snake in MUTATION_FIELD_MAP.items():
                if re.search(rf"--set\s+{re.escape(camel)}\b", code):
                    rel = path.relative_to(REPO_ROOT)
                    failures.append(
                        f"{rel}:{start_line} uses '--set {camel}' — CLI "
                        f"expects '--set {snake}'"
                    )
        self.assertEqual(
            [], failures,
            "Stale camelCase field(s) in CLI --set examples:\n"
            + "\n".join(failures),
        )


class CliUnsupportedSyntaxTests(unittest.TestCase):
    def test_unsupported_syntax_not_shown_as_bare_positive_example(self):
        failures = []
        for path, start_line, code, context in _cli_blocks_with_context():
            for pattern in UNSUPPORTED_CLI_SNIPPET_PATTERNS:
                if pattern.search(code) and not UNSUPPORTED_ANNOTATION_RE.search(context):
                    rel = path.relative_to(REPO_ROOT)
                    failures.append(
                        f"{rel}:{start_line} shows unsupported CLI syntax "
                        f"'{pattern.pattern}' without an adjacent "
                        "unsupported/not-supported annotation"
                    )
        self.assertEqual(
            [], failures,
            "Unsupported CLI syntax shown as a positive example:\n"
            + "\n".join(failures),
        )


if __name__ == "__main__":
    unittest.main()
