"""
SIH26034 — LMPC Compliance Engine Unit Tests

Tests:
1. Unit Sale Price (USP) calculations per 2021 LMPC Amendment.
2. Rule 6 Mandatory Declarations validation.
3. Cross-modal e-commerce discrepancy detection (Price Overcharge, Origin mismatch).
4. Severity classification & scoring logic.
"""

import unittest
from backend.agents.lmpc_evaluator import lmpc_evaluator, AuditVerdict
from backend.agents.report_generator import report_generator


class TestLMPCEvaluator(unittest.TestCase):
    """Test suite for Legal Metrology compliance checks."""

    def test_usp_weight_under_1kg(self):
        """Rule 6(1)(e): Packages <= 1kg must declare USP per gram."""
        usp = lmpc_evaluator._compute_usp(
            mrp_str="100.0",
            net_value="500",
            net_unit="g",
        )
        self.assertEqual(usp, "₹0.20 per g")

    def test_usp_weight_over_1kg(self):
        """Rule 6(1)(e): Packages > 1kg must declare USP per kg."""
        usp = lmpc_evaluator._compute_usp(
            mrp_str="250.0",
            net_value="5",
            net_unit="kg",
        )
        self.assertEqual(usp, "₹50.00 per kg")

    def test_usp_volume_under_1l(self):
        """Rule 6(1)(e): Liquids <= 1L must declare USP per ml."""
        usp = lmpc_evaluator._compute_usp(
            mrp_str="150.0",
            net_value="750",
            net_unit="ml",
        )
        self.assertEqual(usp, "₹0.20 per ml")

    def test_usp_volume_over_1l(self):
        """Rule 6(1)(e): Liquids > 1L must declare USP per litre."""
        usp = lmpc_evaluator._compute_usp(
            mrp_str="300.0",
            net_value="2",
            net_unit="l",
        )
        self.assertEqual(usp, "₹150.00 per l")

    def test_usp_count_based(self):
        """Rule 6(1)(e): Count-based items must declare USP per piece/unit."""
        usp = lmpc_evaluator._compute_usp(
            mrp_str="120.0",
            net_value="10",
            net_unit="units",
        )
        self.assertEqual(usp, "₹12.00 per unit")

    def test_full_compliant_package(self):
        """A package with all 10 declarations should score 100% and be COMPLIANT."""
        mock_extractions = {
            "product_name": {"value": "Organic Green Tea", "confidence": 0.98},
            "manufacturer_name": {"value": "Tata Consumer Products Ltd", "confidence": 0.95},
            "manufacturer_address": {"value": "1, Bishop Lefroy Road, Kolkata 700020", "confidence": 0.95},
            "country_of_origin": {"value": "India", "confidence": 0.99},
            "generic_name": {"value": "Green Tea", "confidence": 0.95},
            "net_quantity": {"value": "250 g", "confidence": 0.97},
            "net_quantity_value": {"value": "250", "confidence": 0.97},
            "net_quantity_unit": {"value": "g", "confidence": 0.97},
            "manufacture_date": {"value": "01/2025", "confidence": 0.94},
            "expiry_date": {"value": "01/2026", "confidence": 0.94},
            "mrp": {"value": "₹240.00", "confidence": 0.99},
            "unit_sale_price": {"value": "₹0.96 per g", "confidence": 0.90},
            "consumer_care_name": {"value": "Consumer Care Cell", "confidence": 0.92},
            "consumer_care_phone": {"value": "1800-345-1720", "confidence": 0.95},
            "consumer_care_email": {"value": "care@tataconsumer.com", "confidence": 0.95},
        }

        verdict: AuditVerdict = lmpc_evaluator.evaluate(extractions=mock_extractions)

        self.assertEqual(verdict.overall_status, "COMPLIANT")
        self.assertGreaterEqual(verdict.compliance_score, 90.0)
        self.assertEqual(verdict.failed_checks, 0)
        self.assertEqual(len(verdict.violations), 0)

    def test_missing_mandatory_declarations(self):
        """Missing MRP and Net Quantity must trigger critical/major violations."""
        mock_extractions = {
            "product_name": {"value": "Unknown Snack", "confidence": 0.7},
            "country_of_origin": {"value": None, "confidence": 0.0},
            "mrp": {"value": None, "confidence": 0.0},
            "net_quantity": {"value": None, "confidence": 0.0},
        }

        verdict: AuditVerdict = lmpc_evaluator.evaluate(extractions=mock_extractions)

        self.assertEqual(verdict.overall_status, "NON_COMPLIANT")
        self.assertLess(verdict.compliance_score, 60.0)
        self.assertGreater(len(verdict.violations), 0)

        # Verify critical MRP violation
        mrp_violation = next(
            (v for v in verdict.violations if "MRP" in v.field_name or "mrp" in v.field_name.lower()),
            None
        )
        self.assertIsNotNone(mrp_violation)
        self.assertEqual(mrp_violation.severity, "critical")

    def test_cross_modal_price_overcharge(self):
        """E-commerce listed price exceeding physical packaging MRP is a critical Section 18 violation."""
        mock_extractions = {
            "product_name": {"value": "Basmati Rice 5kg", "confidence": 0.95},
            "mrp": {"value": "₹450.00", "confidence": 0.98},
            "net_quantity": {"value": "5 kg", "confidence": 0.98},
            "country_of_origin": {"value": "India", "confidence": 0.98},
        }

        # Listing attempts to charge ₹520 (₹70 over printed MRP!)
        mock_listing = {
            "product_name": "Basmati Rice 5kg",
            "listed_price": 520.0,
            "net_quantity": "5 kg",
            "country_of_origin": "India",
        }

        verdict: AuditVerdict = lmpc_evaluator.evaluate(
            extractions=mock_extractions,
            listing_data=mock_listing,
        )

        overcharge_violation = next(
            (v for v in verdict.violations if v.is_discrepancy and "Overcharge" in v.field_name),
            None
        )
        self.assertIsNotNone(overcharge_violation)
        self.assertEqual(overcharge_violation.severity, "critical")
        self.assertIn("Section 18", overcharge_violation.rule_reference)

    def test_report_generation(self):
        """Verifies that the HTML inspection report is generated correctly."""
        verdict_dict = {
            "compliance_score": 85.0,
            "total_checks": 10,
            "passed_checks": 8,
            "failed_checks": 2,
            "overall_status": "PARTIAL_VIOLATION",
            "computed_usp": "₹0.50 per g",
            "declaration_status": {
                "mrp": {"status": "FOUND", "value": "₹150.00"},
                "country_of_origin": {"status": "MISSING", "value": None},
            },
            "violations": [
                {
                    "rule_reference": "Rule 6(1)(aa)",
                    "field_name": "Country of Origin",
                    "severity": "critical",
                    "description": "Country of Origin is missing.",
                    "expected_value": "Mandatory declaration",
                    "found_value": "Missing",
                    "is_discrepancy": False,
                }
            ],
        }
        extractions = {
            "product_name": {"value": "Test Premium Coffee"},
            "mrp": {"value": "₹150.00"},
            "net_quantity": {"value": "300 g"},
        }

        html_path = report_generator.generate_html_report(
            audit_id="test-audit-123456",
            verdict_data=verdict_dict,
            extractions=extractions,
        )
        self.assertTrue(html_path.endswith(".html"))
        with open(html_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("STATUTORY COMPLIANCE INSPECTION", content)
        self.assertIn("Test Premium Coffee", content)
        self.assertIn("Section 36", content)
        self.assertIn("Section 49", content)
        self.assertIn("Ministry of Consumer Affairs", content)

    def test_statutory_act_and_penalty_citations(self):
        """Verifies that every violation carries explicit Act Section, Penalty, and Statutory Proof."""
        mock_extractions = {
            "product_name": {"value": "Biscuits", "confidence": 0.9},
            "mrp": {"value": None, "confidence": 0.0},
        }
        verdict: AuditVerdict = lmpc_evaluator.evaluate(extractions=mock_extractions)
        self.assertGreater(len(verdict.violations), 0)
        for v in verdict.violations:
            self.assertTrue(v.act_section.startswith("Section"))
            self.assertTrue(v.punishment_section.startswith("Section"))
            self.assertIn("₹", v.statutory_penalty)
            self.assertTrue(len(v.legal_proof_summary) > 0)

        # Check Ministry authority and corporate liability metadata
        self.assertIn("Ministry of Consumer Affairs", verdict.statutory_authority)
        self.assertIn("Section 49", verdict.corporate_liability_clause)

    def test_illegal_unit_statutory_violation(self):
        """Rule 6(1)(c) & Section 11(1)(d): Non-standard unit 'gms' must cite Section 11(1)(d) and Section 29."""
        mock_extractions = {
            "product_name": {"value": "Wheat Flour", "confidence": 0.95},
            "net_quantity": {"value": "500 gms", "confidence": 0.95},
            "net_quantity_unit": {"value": "gms", "confidence": 0.95},
            "net_quantity_value": {"value": "500", "confidence": 0.95},
        }
        verdict: AuditVerdict = lmpc_evaluator.evaluate(extractions=mock_extractions)
        unit_violation = next((v for v in verdict.violations if "Unit Format" in v.field_name), None)
        self.assertIsNotNone(unit_violation)
        self.assertIn("Section 11(1)(d)", unit_violation.act_section)
        self.assertIn("Section 29", unit_violation.punishment_section)
        self.assertIn("₹10,000", unit_violation.statutory_penalty)

    def test_needs_manual_review_on_blurry_label(self):
        """When label readability is blurry or damaged, status must be NEEDS_MANUAL_REVIEW under Section 15."""
        mock_extractions = {
            "product_name": {"value": "Packaged Tea", "confidence": 0.95},
            "label_readability": "blurry",
        }
        verdict: AuditVerdict = lmpc_evaluator.evaluate(extractions=mock_extractions)
        self.assertEqual(verdict.overall_status, "NEEDS_MANUAL_REVIEW")
        self.assertGreater(len(verdict.manual_review_reasons), 0)
        self.assertIn("Section 15", verdict.manual_review_reasons[0])


if __name__ == "__main__":
    unittest.main()
