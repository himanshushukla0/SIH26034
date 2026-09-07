#!/usr/bin/env python3
"""
 Unit tests for LMPC Compliance Engine Vision Extraction Contract.
"""

import unittest
import lmpc_extraction as ext
import lmpc_core as core


class TestVisionExtractionContract(unittest.TestCase):
    """Test suite for extraction response coercion, validation, and contract enforcement."""

    def test_escape_hatch_rejects_non_label(self):
        """When model uses escape hatch (is_product_label: false), audit is refused."""
        raw_response = {
            "is_product_label": False,
            "what_it_shows": "a selfie of a person in a room",
            "fields": {},
        }
        res = ext.validate_extraction(raw_response)
        self.assertFalse(res.accepted)
        self.assertEqual(res.status, ext.REJECTED_NOT_LABEL)
        self.assertIn("selfie of a person", res.message)
        self.assertEqual(res.audit_status(), core.INSUFFICIENT_DATA)

    def test_malformed_json_rejected(self):
        """Malformed response without JSON or without fields object is rejected."""
        res_text = ext.validate_extraction("Just a random conversation text with no JSON.")
        self.assertFalse(res_text.accepted)
        self.assertEqual(res_text.status, ext.REJECTED_MALFORMED)

        res_no_fields = ext.validate_extraction({"is_product_label": True})
        self.assertFalse(res_no_fields.accepted)
        self.assertEqual(res_no_fields.status, ext.REJECTED_MALFORMED)

    def test_quoted_text_enforcement(self):
        """A reported value without verbatim quoted_text is downgraded to UNVERIFIED."""
        raw = {
            "is_product_label": True,
            "what_it_shows": "tea packet back panel",
            "fields": {
                "MANUFACTURER": {
                    "value": "Tata Consumer Products Ltd",
                    "quoted_text": None,  # Hallucinated/Recalled without quoting!
                    "confidence": 0.95,
                    "bbox": [10, 10, 200, 30],
                },
                "NET_QUANTITY": {
                    "value": "500 g",
                    "quoted_text": "Net Wt. 500 g",
                    "confidence": 0.95,
                    "bbox": [10, 50, 100, 20],
                },
            },
        }
        res = ext.validate_extraction(raw, min_mean_confidence=0.10)
        mfg_check = next(c for c in res.checks if c["rule_id"] == "MANUFACTURER")
        self.assertEqual(mfg_check["status"], core.UNVERIFIED)
        self.assertIn("could not quote it", mfg_check["val"])
        self.assertIn("MANUFACTURER", res.downgraded[0])

    def test_low_confidence_downgrade(self):
        """Field with confidence below threshold (< 0.70) is downgraded to UNVERIFIED."""
        raw = {
            "is_product_label": True,
            "what_it_shows": "food label",
            "fields": {
                "MRP": {
                    "value": "Rs 150.00",
                    "quoted_text": "MRP Rs 150.00",
                    "confidence": 0.50,  # Below MIN_FIELD_CONFIDENCE (0.70)
                    "bbox": [10, 10, 80, 20],
                },
                "NET_QUANTITY": {
                    "value": "200 g",
                    "quoted_text": "Net Qty: 200 g",
                    "confidence": 0.90,
                    "bbox": [10, 40, 80, 20],
                },
            },
        }
        res = ext.validate_extraction(raw, min_mean_confidence=0.10)
        mrp_check = next(c for c in res.checks if c["rule_id"] == "MRP")
        self.assertEqual(mrp_check["status"], core.UNVERIFIED)
        self.assertIn("low confidence (50%)", mrp_check["val"])

    def test_low_mean_confidence_rejects_whole_label(self):
        """When mean confidence across read fields < 0.55, whole label is rejected."""
        raw = {
            "is_product_label": True,
            "what_it_shows": "blurry label",
            "fields": {
                "MRP": {
                    "value": "Rs 150",
                    "quoted_text": "MRP Rs 150",
                    "confidence": 0.35,
                    "bbox": [10, 10, 50, 20],
                }
            },
        }
        res = ext.validate_extraction(raw)
        self.assertFalse(res.accepted)
        self.assertEqual(res.status, ext.REJECTED_LOW_CONFIDENCE)

    def test_valid_label_accepted_with_high_confidence(self):
        """When declarations are quoted and confident, response is ACCEPTED."""
        fields_data = {
            k: {
                "value": f"Sample {k}",
                "quoted_text": f"Quoted {k}",
                "confidence": 0.92,
                "bbox": [10, 20, 100, 30],
            }
            for k in ext.FIELD_KEYS
        }
        raw = {
            "is_product_label": True,
            "what_it_shows": "Tea packaging declaration panel",
            "fields": fields_data,
        }
        res = ext.validate_extraction(raw)
        self.assertTrue(res.accepted)
        self.assertEqual(res.status, ext.ACCEPTED)
        self.assertEqual(len(res.downgraded), 0)
        self.assertEqual(res.audit_status(), core.COMPLIANT)

        summary = ext.compliance_summary(res.checks)
        self.assertEqual(summary["verdict"], core.COMPLIANT)
        self.assertEqual(summary["score_percent"], 100.0)

    def test_build_audit_with_image_gate(self):
        """build_audit correctly gates unaccepted extractions and refused image gates."""
        gate_refused = {"proceed": False, "user_message": "Refused selfie"}
        res_gated = ext.build_audit(gate_refused, ext.ExtractionResult(ext.ACCEPTED, "OK"))
        self.assertFalse(res_gated["audit_recorded"])
        self.assertEqual(res_gated["reason"], "Refused selfie")


if __name__ == "__main__":
    unittest.main()
