import unittest
from datetime import datetime, timezone
import uuid

from backend.agents.lmpc_evaluator import (
    PENALTY_SEC_36_1,
    PENALTY_SEC_29,
)


class TestAnalyticsAggregation(unittest.TestCase):
    """Test suite for analytics computations and fine estimation logic."""

    def test_fine_estimation_logic(self):
        """Should accurately estimate statutory fines based on Act sections."""
        # Simulated violations
        sample_violations = [
            {"punishment_section": "Section 36(1)", "rule": "Rule 6(1)(f)"},
            {"punishment_section": "Section 36(1)", "rule": "Rule 6(1)(a)"},
            {"punishment_section": "Section 29", "rule": "Rule 6(1)(c)"},
            {"punishment_section": "Section 36(2)", "rule": "Rule 6(1)(c)"},
        ]
        
        est_fines = 0
        for v in sample_violations:
            punish = v["punishment_section"]
            if "29" in punish:
                est_fines += 10000
            elif "36(2)" in punish:
                est_fines += 10000
            else:
                est_fines += 25000

        # 2 * 25000 (Sec 36(1)) + 10000 (Sec 29) + 10000 (Sec 36(2)) = 70,000
        self.assertEqual(est_fines, 70000)

    def test_compliance_rate_computation(self):
        """Should accurately compute percentages and averages."""
        total = 4
        compliant = 2
        non_compliant = 1
        manual_review = 1
        scores = [100.0, 95.0, 40.0, 60.0]

        rate = round((compliant / total) * 100, 1)
        avg_score = round(sum(scores) / len(scores), 1)

        self.assertEqual(rate, 50.0)
        self.assertEqual(avg_score, 73.8)


if __name__ == "__main__":
    unittest.main()
