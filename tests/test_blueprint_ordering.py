"""Documentation contracts: prepare initial allocation before restoring a
killed flag, then perform later ramp increases. Scan step markers per flag
and environment, not just the first step anywhere in a multi-env file.
This is deliberately not a YAML/schema validator or a pipeline execution.
"""
import re
import unittest

from tests._mdutil import REPO_ROOT

BLUEPRINTS_DIR = (
    REPO_ROOT / "skills" / "fme-pipeline" / "references" / "blueprints"
)

RAMP_BLUEPRINTS = (
    "r1-progressive-ramp.yaml", "r2-multi-env-promotion.yaml",
    "r3-beta-cohort.yaml",
)


def rollout_steps(text):
    """Yield relevant (type, flag, env, body) from the fixed step layout."""
    matches = list(re.finditer(r"(?m)^\s*type:\s*(\w+)\s*$", text))
    for i, match in enumerate(matches):
        kind = match.group(1)
        if kind not in {"FmeFlagDefaultAllocation", "FmeFlagRestore",
                        "FmeFlagAddRemoveIndividualTargets", "HarnessApproval"}:
            continue
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[match.end():end]
        if kind == "HarnessApproval":
            yield kind, None, None, block
            continue
        flag = re.search(r"(?m)^\s*flagName:\s*(.+)$", block)
        env = re.search(r"(?m)^\s*environment:\s*(.+)$", block)
        if not flag or not env:
            raise AssertionError(f"Cannot resolve flag/environment for {kind}")
        yield kind, flag.group(1).strip(), env.group(1).strip(), block


class BlueprintRestoreOrderingTests(unittest.TestCase):
    def test_initial_allocation_precedes_each_environment_restore(self):
        for filename in RAMP_BLUEPRINTS:
            with self.subTest(blueprint=filename):
                steps = list(rollout_steps((BLUEPRINTS_DIR / filename).read_text()))
                restored = set()
                allocations = {}
                for index, (kind, flag, env, _) in enumerate(steps):
                    key = (flag, env)
                    if kind == "FmeFlagDefaultAllocation":
                        allocations.setdefault(key, []).append(index)
                    elif kind == "FmeFlagRestore":
                        self.assertIn(key, allocations, f"{env}: restore before allocation")
                        self.assertEqual(1, len(allocations[key]),
                                         f"{env}: later ramp increases ran while killed")
                        restored.add(key)
                self.assertTrue(restored, "Blueprint must contain a restore")
                self.assertTrue(restored.issubset(allocations))

    def test_manual_readback_approval_follows_writes_before_each_restore(self):
        for filename in RAMP_BLUEPRINTS:
            with self.subTest(blueprint=filename):
                steps = rollout_steps((BLUEPRINTS_DIR / filename).read_text())
                last_write = {}
                last_readback = -1
                for index, (kind, flag, env, body) in enumerate(steps):
                    key = (flag, env)
                    if kind == "HarnessApproval":
                        if re.search(r"read[ -]?back", body, re.IGNORECASE):
                            for field in ("isKilled", "defaultTreatment", "trafficAllocation", "defaultRule"):
                                self.assertIn(field, body)
                            self.assertNotRegex(body, r"defaultRule\s+trafficAllocation")
                            last_readback = index
                    elif kind == "FmeFlagRestore":
                        self.assertIn(key, last_write)
                        self.assertGreater(last_readback, last_write[key],
                                           f"{env}: restore lacks readback approval after all writes")
                        last_readback = -1  # A prior environment's gate cannot be reused.
                    else:
                        last_write[key] = index

    def test_retirement_is_preparatory_not_an_archive(self):
        text = (BLUEPRINTS_DIR / "l2-flag-retirement.yaml").read_text()
        self.assertNotRegex(text, r"(?m)^\s*type:\s*FmeFlagArchive\b")
        self.assertIn("manage-flag-lifecycle", text)


if __name__ == "__main__":
    unittest.main()
