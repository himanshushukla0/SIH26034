import json
import os
import unittest
import uuid
from pathlib import Path

from backend.agents.report_generator import ReportGenerator, report_generator
from backend.agents.lmpc_evaluator import ViolationRecord


class TestReportGenerator(unittest.TestCase):
    """Test suite for ReportGenerator robustness and edge-case handling."""

    def setUp(self):
        self.generator = ReportGenerator()

    def test_generate_html_with_none_audit_id(self):
        """Should generate a valid report even if audit_id is None."""
        path = self.generator.generate_html_report(None)
        self.assertTrue(Path(path).exists())
        self.assertTrue(path.endswith(".html"))

    def test_generate_html_with_uuid_audit_id(self):
        """Should handle UUID objects without raising TypeError on slicing."""
        uid = uuid.uuid4()
        path = self.generator.generate_html_report(uid)
        self.assertTrue(Path(path).exists())

    def test_generate_html_with_unsafe_characters_in_audit_id(self):
        """Should sanitize URLs and invalid Windows path characters."""
        unsafe_id = "https://amazon.in/dp/B0123:foo*bar?test=1"
        path = self.generator.generate_html_report(unsafe_id)
        self.assertTrue(Path(path).exists())

    def test_empty_declarations_extractions_fallback(self):
        """Should derive declaration status from extractions when reloaded from DB."""
        extractions = {
            "manufacturer_name": {"value": "Tata Consumer Products Ltd"},
            "mrp": {"value": "99.00"},
            "country_of_origin": {"value": "India"},
        }
        verdict = {
            "compliance_score": 100.0,
            "overall_status": "COMPLIANT",
            "declaration_status": {},  # empty like in DB reload
            "violations": [],
        }
        path = self.generator.generate_html_report(
            audit_id="tata-tea-test",
            verdict_data=verdict,
            extractions=extractions,
        )
        content = Path(path).read_text(encoding="utf-8")
        self.assertIn("Tata Consumer Products Ltd", content)
        self.assertIn("India", content)
        self.assertIn("FOUND", content)

    def test_mixed_violation_types(self):
        """Should handle dataclass, dict, and string violations without crashing."""
        v_record = ViolationRecord(
            rule_reference="Rule 6(1)(f)",
            act_section="Section 18(1)",
            punishment_section="Section 36(1)",
            statutory_penalty="Improvement notice under Section 15(6)",
            field_name="mrp",
            severity="critical",
            description="MRP omitted from PDP",
            expected_value="Valid MRP",
            found_value="Missing",
            legal_proof_summary="Violates Section 18(1)",
        )
        v_dict = {
            "rule_reference": "Rule 6(1)(aa)",
            "act_section": "Section 18(1)",
            "punishment_section": "Section 36(1)",
            "field_name": "country_of_origin",
            "severity": "major",
            "description": "Origin missing",
        }
        v_str = "Raw string violation notice"
        
        verdict = {
            "compliance_score": 40.0,
            "overall_status": "NON_COMPLIANT",
            "violations": [v_record, v_dict, v_str, None],
        }
        path = self.generator.generate_html_report("mixed-viol-test", verdict)
        content = Path(path).read_text(encoding="utf-8")
        self.assertIn("MRP omitted from PDP", content)
        self.assertIn("Origin missing", content)
        self.assertIn("Raw string violation notice", content)

    def test_json_summary_generation(self):
        """Should generate valid JSON summary."""
        path = self.generator.generate_json_summary(
            "summary-test",
            verdict_data={"compliance_score": 85.0, "overall_status": "COMPLIANT"},
            extractions={"mrp": "100"},
        )
        self.assertTrue(Path(path).exists())
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(data["verdict"]["compliance_score"], 85.0)

    def test_pdf_graceful_fallback(self):
        """Should gracefully return HTML path when WeasyPrint is not installed."""
        path = self.generator.generate_pdf_report("pdf-fallback-test")
        self.assertTrue(Path(path).exists())
        # Since weasyprint is not installed in standard env, it returns html
        self.assertTrue(path.endswith(".html") or path.endswith(".pdf"))


if __name__ == "__main__":
    unittest.main()
