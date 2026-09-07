"""
Unit tests for LMPC Notice Drafting Module (Jan Vishwas 2026 Statutory Regime).
Verifies:
1. s.15(6) Improvement Notice selection for 1st contraventions.
2. Show Cause Notice selection for repeat offences (offence_number >= 2).
3. Criminal offences (s.36(2) short measure) defaulting to Show Cause.
4. Correct inclusion of statutory remedies, escalation ladders, and appeal rights.
"""

import unittest
from lmpc_notice import (
    select_instrument,
    draft_notice,
    evidence_fingerprint,
    DEFAULT_COMPLIANCE_DAYS,
    DEFAULT_SHOW_CAUSE_DAYS,
)
import lmpc_rules as rules


class TestLMPCNoticeDrafting(unittest.TestCase):
    def setUp(self):
        self.sample_item = {
            "name": "Royal Shahi Garam Masala Pouch",
            "manufacturer": "Local Spice Mills, New Delhi",
            "barcode": "8909999999999",
            "data_source": "Physical Packaging OCR Inspection",
            "checks": [("Rule 6(1)(a)", "Manufacturer Address", "No PIN Code", "FAIL")],
        }

    def test_first_offence_drafts_improvement_notice(self):
        """First contravention of Section 36(1) must select Improvement Notice under s.15(6)."""
        failures = [
            {"rule_id": "MANUFACTURER", "found": "Missing PIN Code"},
            {"rule_id": "UNIT_SALE_PRICE", "found": "No USP declared"},
            {"rule_id": "DATE_OF_MANUFACTURE", "found": "Missing on PDP"},
        ]
        res = draft_notice(
            item=self.sample_item,
            failures=failures,
            officer_name="Inspector R. K. Singh",
            ref="LMPC/2026/001",
            offence_number=1,
        )

        self.assertEqual(res["instrument"], rules.IMPROVEMENT_NOTICE)
        self.assertIn("section 15(6)", res["reason"].lower())

        text = res["text"]
        # Must fulfill the 4 requirements of s.15(6):
        # (a) & (b) Grounds and matters
        self.assertIn("GROUNDS AND (b) MATTERS CONSTITUTING THE FAILURE", text)
        # (c) Specified measures to secure compliance
        normalized_text = " ".join(text.split())
        self.assertIn(rules.rule("MANUFACTURER").remedy, normalized_text)
        self.assertIn(rules.rule("UNIT_SALE_PRICE").remedy, normalized_text)
        # (d) Specified compliance period (30 days)
        self.assertIn("PERIOD FOR COMPLIANCE: you are required to take the measures specified", text)
        self.assertIn(f"{DEFAULT_COMPLIANCE_DAYS} days", text)
        # Consequence under s.15(7) & Appeal under s.50
        self.assertIn("section 15(7)", text)
        self.assertIn("section 50", text)
        self.assertIn("60 days", text)
        # Escalation ladder
        self.assertIn("Second contravention", text)

    def test_repeat_offence_drafts_show_cause_notice(self):
        """Second offence must select Show Cause Notice with civil penalty / fine liabilities."""
        failures = [
            {"rule_id": "UNIT_SALE_PRICE", "found": "No USP declared"},
        ]
        res = draft_notice(
            item=self.sample_item,
            failures=failures,
            officer_name="Inspector R. K. Singh",
            ref="LMPC/2026/002",
            offence_number=2,
        )

        self.assertEqual(res["instrument"], "SHOW_CAUSE")
        self.assertIn("contravention number 2", res["reason"])
        self.assertIn("SHOW CAUSE NOTICE", res["text"])
        self.assertIn(f"{DEFAULT_SHOW_CAUSE_DAYS} days", res["text"])
        self.assertIn("section 48", res["text"])  # Compounding

    def test_criminal_shortfall_drafts_show_cause_notice(self):
        """Short measure under Section 36(2) remains criminal and selects Show Cause."""
        failures = [
            {"rule_id": "NET_QUANTITY_SHORTFALL", "found": "Actual 420g vs Declared 500g (MPE exceeded)"},
        ]
        res = draft_notice(
            item=self.sample_item,
            failures=failures,
            officer_name="Inspector R. K. Singh",
            ref="LMPC/2026/003",
            offence_number=1,
        )

        self.assertEqual(res["instrument"], "SHOW_CAUSE")
        self.assertIn("remained criminal", res["reason"])
        self.assertIn("NET_QUANTITY_SHORTFALL", res["reason"])
        self.assertIn("SHOW CAUSE NOTICE", res["text"])

    def test_evidence_fingerprint_generation(self):
        """Produces unique, verifiable SHA-256 fingerprint."""
        fp1 = evidence_fingerprint("Payload A")
        fp2 = evidence_fingerprint("Payload A")
        fp3 = evidence_fingerprint("Payload B")

        self.assertEqual(fp1, fp2)
        self.assertNotEqual(fp1, fp3)
        self.assertEqual(len(fp1), 64)


if __name__ == "__main__":
    unittest.main()
