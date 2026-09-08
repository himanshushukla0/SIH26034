"""
Comprehensive Unit Tests for the Refined 5-Step LMPC Architecture:
GATE -> READ -> MAP -> CHECK -> CONFIRM

Verifies:
1. Scoped OCR digit repair: '2SO.OO' -> 250.00, 'lOOO ml' -> 1000 ml, Gupta Oil Mills undamaged
2. Two-pass scanning: Single-line (conf 0.92) and stitched line pairs (conf 0.82)
3. Absence findings: 6-digit PIN code sweep
4. GENERIC_NAME discipline: Deliberately unparsed by regex -> INSUFFICIENT_DATA (never invents)
5. needs_model() decision switch: Clean label (>=75% coverage) never costs an API call
"""

import unittest
from lmpc_labelparse import parse_label, repair_numeric_run, needs_model, ParsedField
from lmpc_checks import run_checks
import lmpc_notice


class Test5StepPipeline(unittest.TestCase):

    def test_scoped_ocr_digit_repair(self):
        # Numeric runs repaired
        self.assertEqual(repair_numeric_run("2SO.OO"), "250.00")
        self.assertEqual(repair_numeric_run("lOOO"), "1000")
        self.assertEqual(repair_numeric_run("IOO"), "100")
        self.assertEqual(repair_numeric_run("S00"), "500")

        # Non-numeric text / brand names MUST survive undamaged
        self.assertEqual(repair_numeric_run("Gupta Oil Mills"), "Gupta Oil Mills")
        self.assertEqual(repair_numeric_run("Patanjali"), "Patanjali")

    def test_full_tea_label_89_percent_coverage(self):
        # A clean label where 8 of 9 fields are parsed, GENERIC_NAME left unparsed
        ocr_text = """
        TATA TEA GOLD
        Manufactured by: Tata Consumer Products Ltd, 1 Bishop Lefroy Road, Kolkata 700020
        Country of Origin: India
        Net Quantity: 500 g
        PKD: 03/2026
        Best Before: 12 months from packaging
        MRP Rs 320.00 (inclusive of all taxes)
        USP Rs 0.64/g
        Consumer Care: care@tataconsumer.com Tel: 1800-345-1720
        """

        parse_res = parse_label(ocr_text)
        fields = parse_res.fields

        # Check coverage: exactly 8 of 9 fields (88.9% -> 88.9%)
        self.assertEqual(parse_res.parsed_count, 8)
        self.assertAlmostEqual(parse_res.coverage_percent, 88.9, places=1)
        self.assertTrue(parse_res.has_pin_code)
        self.assertEqual(parse_res.pin_code, "700020")

        # Clean label (>=75%) does NOT need model escalation (Zero API cost!)
        self.assertFalse(parse_res.needs_model_escalation)

        # GENERIC_NAME is deliberately unparsed (never invents)
        self.assertIsNone(fields["GENERIC_NAME"].value)

        # CHECK reports INSUFFICIENT_DATA rather than hallucinating COMPLIANT
        check_res = run_checks(fields, has_pin_code=parse_res.has_pin_code)
        self.assertEqual(check_res["failed"], 0)
        self.assertEqual(check_res["unverified"], 1)
        self.assertEqual(check_res["overall_status"], "INSUFFICIENT_DATA")

    def test_two_pass_line_pair_stitching(self):
        # Narrow package where keyword and value are on separate adjacent lines
        narrow_pack_text = """
        PARLE-G GLUCOSE BISCUITS
        Net Content:
        250 g
        MRP (incl. of all taxes)
        Rs. 30.00
        Mfg Date
        02/2026
        Best Before
        6 months
        Made in India
        Consumer Helpline 1800220033
        Mfd by Parle Biscuits Pvt Ltd, Mumbai 400057
        """

        parse_res = parse_label(narrow_pack_text)
        fields = parse_res.fields

        # Values stitched across lines have stitched=True and conf=0.82
        self.assertTrue(fields["NET_QUANTITY"].stitched)
        self.assertEqual(fields["NET_QUANTITY"].confidence, 0.82)
        self.assertEqual(fields["NET_QUANTITY"].value, "250 g")

        self.assertTrue(fields["MRP"].stitched)
        self.assertEqual(fields["MRP"].confidence, 0.82)
        self.assertEqual(fields["MRP"].value, "₹ 30.00")

        # 7 of 9 fields parsed = 77.8% coverage >= 75% -> No model escalation needed!
        self.assertGreaterEqual(parse_res.coverage_percent, 75.0)
        self.assertFalse(parse_res.needs_model_escalation)

    def test_ocr_damaged_digits_repair(self):
        # Damaged digits: 'lOOO ml', 'Rs. 2SO.OO'
        damaged_text = """
        FORTUNE MUSTARD OIL
        Mfd by Adani Wilmar, Ahmedabad 380009
        Country of Origin: India
        Net Quantity: lOOO ml
        PKD: 04/2026
        Best Before: 9 months
        MRP Rs. 2SO.OO (inclusive of all taxes)
        Consumer Care Tel: 1800233000
        """

        parse_res = parse_label(damaged_text)
        fields = parse_res.fields

        # Scoped repair correctly fixed the numbers
        self.assertEqual(fields["NET_QUANTITY"].value, "1000 ml")
        self.assertEqual(fields["MRP"].value, "₹ 250.00")

        # Coverage is 77.8% (7/9) -> no model needed
        self.assertGreaterEqual(parse_res.coverage_percent, 75.0)
        self.assertFalse(parse_res.needs_model_escalation)

    def test_absence_finding_no_pin_code(self):
        # Address without any 6-digit PIN code
        no_pin_text = """
        LOCAL SPICE PACK
        Mfd by Shinde Masale, Pune
        Made in India
        Net Qty: 100 g
        MRP Rs 50.00
        """

        parse_res = parse_label(no_pin_text)
        self.assertFalse(parse_res.has_pin_code)

        check_res = run_checks(parse_res.fields, has_pin_code=parse_res.has_pin_code)
        pin_failures = [f for f in check_res["findings"] if f["rule_id"] == "PIN_CODE_ABSENCE"]
        self.assertEqual(len(pin_failures), 1)
        self.assertIn("No 6-digit Indian PIN code", pin_failures[0]["detail"])

    def test_deficient_pack_low_coverage_escalates_to_model(self):
        # Deficient spice pack with only 3 fields (33% coverage)
        deficient_text = """
        GARAM MASALA
        Net Qty: 50 g
        MRP Rs 25.00
        """

        parse_res = parse_label(deficient_text)
        # Coverage is 22.2% or 33.3% (<75%)
        self.assertLess(parse_res.coverage_percent, 75.0)
        self.assertTrue(parse_res.needs_model_escalation)
        self.assertIn("Low coverage", parse_res.escalation_reason)

        # Shop signage / zero coverage
        signage_text = "WELCOME TO SHARMA GENERAL STORE - ALL GROCERIES AVAILABLE"
        sign_res = parse_label(signage_text)
        self.assertEqual(sign_res.coverage_percent, 0.0)
        self.assertTrue(sign_res.needs_model_escalation)


if __name__ == "__main__":
    unittest.main()
