import unittest
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from audit_engine import analyze_contract


class AuditEngineTests(unittest.TestCase):
    def test_random_text_is_invalid_contract_input(self):
        result = analyze_contract("hh.py", "sujdxkkzsososo")

        self.assertEqual(result["verdict"]["status"], "invalid")
        self.assertEqual(result["metrics"]["consensus"]["value"], "N/A")
        self.assertEqual(result["metrics"]["deterministic"]["value"], "INVALID")
        self.assertTrue(any(finding["pillar"] == "input" for finding in result["findings"]))
        self.assertIn("severityModel", result)

    def test_minimal_genlayer_contract_can_be_scored(self):
        source = """
class Market:
    @gl.public.write
    def resolve(self):
        if gl.message.sender_address:
            return True
"""

        result = analyze_contract("market.py", source)

        self.assertNotEqual(result["verdict"]["status"], "invalid")
        self.assertNotEqual(result["metrics"]["consensus"]["value"], "N/A")

    def test_findings_include_code_context_and_fix_guidance(self):
        source = """
class Market:
    @gl.public.write
    def submit_target(self, target):
        self.targets.append(target)
"""

        result = analyze_contract("market.py", source)
        explanation = result["summary"]["findingExplanations"][0]

        self.assertEqual(explanation["line"], 3)
        self.assertIn("@gl.public.write", explanation["snippet"])
        self.assertIn("guard", explanation["suggestedFix"].lower())
        self.assertTrue(explanation["suggestedFix"])
        self.assertTrue(explanation["whySeverity"])

    def test_summary_merges_duplicate_access_control_findings(self):
        source = """
class Market:
    @gl.public.write
    def submit_target(self, target):
        self.targets.append(target)

    @gl.public.write
    def set_winner(self, winner):
        self.winner = winner
"""

        result = analyze_contract("market.py", source)
        access_details = [
            finding for finding in result["summary"]["findingExplanations"]
            if finding["title"] == "Public write may be callable by the wrong user"
        ]
        access_groups = [
            finding for finding in result["summary"]["narrativeFindings"]
            if finding["title"] == "Public write may be callable by the wrong user"
        ]

        self.assertEqual(len(access_details), 2)
        self.assertEqual(len(access_groups), 1)
        self.assertEqual(access_groups[0]["count"], 2)
        self.assertEqual(result["summary"]["nextSteps"].count(access_groups[0]["recommendation"]), 1)


if __name__ == "__main__":
    unittest.main()
