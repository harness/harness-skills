"""Validate manual scenario fixtures, not model behavior or live APIs.

CI checks fixture shape, real skill names and coverage only. Follow the
scenario evaluation guide to exercise an agent; no model runs in this test.
"""
import json
import unittest

from tests._mdutil import REPO_ROOT

EXPECTED_SCENARIOS = {
    "killed-old-100-ramp-5", "preserve-source-destination-targets",
    "beta-existing-targets", "killed-default-config-change",
    "missing-primary-metric", "empty-duplicate-results", "duplicate-metric-results",
    "same-treatment-different-configs", "no-critical-envs", "idle-event",
    "unsupported-cli-segment-keys", "ai-config-scope-refusal", "all-segment-types",
    "pipeline-deferred-archive", "pagination-partial", "changed-app-not-running",
}


class ScenarioFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(
            (REPO_ROOT / "tests/fixtures/scenarios.json").read_text()
        )

    def test_required_scenarios_are_present_without_duplicate_ids(self):
        self.assertIsInstance(self.fixtures, list)
        ids = [item["id"] for item in self.fixtures]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(EXPECTED_SCENARIOS.issubset(ids))

    def test_each_scenario_has_inputs_expectations_and_a_real_skill(self):
        for item in self.fixtures:
            with self.subTest(scenario=item.get("id")):
                for key in ("id", "skill", "description"):
                    self.assertIsInstance(item[key], str)
                    self.assertTrue(item[key].strip())
                self.assertTrue((REPO_ROOT / "skills" / item["skill"] / "SKILL.md").is_file())
                self.assertIsInstance(item["inputs"], dict)
                self.assertTrue(item["inputs"])
                for key in ("required_behavior", "forbidden_behavior"):
                    self.assertIsInstance(item[key], list)
                    self.assertTrue(item[key])
                    self.assertTrue(all(isinstance(value, str) and value.strip()
                                        for value in item[key]))


if __name__ == "__main__":
    unittest.main()
