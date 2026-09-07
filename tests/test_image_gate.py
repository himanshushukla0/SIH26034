#!/usr/bin/env python3
"""
 Unit tests for LMPC Compliance Engine Image Gate & Barcode Decoder.
"""

import os
import tempfile
import unittest
import cv2
import numpy as np

import image_gate


class TestImageGate(unittest.TestCase):
    """Test suite for image gating, blur analysis, face refusal, and barcode status."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def _create_image(self, width: int, height: int, fill: int = 0) -> str:
        img = np.full((height, width, 3), fill, dtype=np.uint8)
        path = os.path.join(self.temp_dir.name, f"test_{width}x{height}.jpg")
        cv2.imwrite(path, img)
        return path

    def test_unreadable_file(self):
        """Non-existent file should be refused as UNREADABLE_FILE."""
        res = image_gate.prepare_audit_input("non_existent_file_path.jpg")
        self.assertFalse(res["proceed"])
        self.assertEqual(res["audit_status"], "REFUSED")
        self.assertEqual(res["image"]["status"], image_gate.UNREADABLE_FILE)

    def test_too_small_image(self):
        """Image with short edge < 400px must be refused as TOO_SMALL."""
        path = self._create_image(width=300, height=300)
        res = image_gate.prepare_audit_input(path)
        self.assertFalse(res["proceed"])
        self.assertEqual(res["audit_status"], "REFUSED")
        self.assertEqual(res["image"]["status"], image_gate.TOO_SMALL)
        self.assertIn("300x300", res["user_message"])

    def test_featureless_blank_image(self):
        """Blank image with zero edge density must be refused as NOT_A_LABEL."""
        path = self._create_image(width=600, height=600, fill=128)
        res = image_gate.prepare_audit_input(path)
        self.assertFalse(res["proceed"])
        self.assertEqual(res["audit_status"], "REFUSED")
        self.assertEqual(res["image"]["status"], image_gate.NOT_A_LABEL)

    def test_gtin_checksum_validation(self):
        """Valid and invalid GTIN check digits."""
        # 8901030383472 is valid EAN-13
        self.assertTrue(image_gate._gtin_checksum_ok("8901030383472"))
        # Tampered check digit
        self.assertFalse(image_gate._gtin_checksum_ok("8901030383479"))
        # Invalid length
        self.assertIsNone(image_gate._gtin_checksum_ok("12345"))

    def test_valid_packaging_label_passes_gate(self):
        """A well-rendered label with horizontal text rows and edges passes the gate."""
        img = np.full((800, 800, 3), 255, dtype=np.uint8)
        lines = [
            "TATA TEA GOLD PREMIUM 500g",
            "Mfd by: Tata Consumer Products Ltd",
            "Net Quantity: 500 g",
            "MRP: Rs 320.00 (Incl. of all taxes)",
            "USP: Rs 0.64 / g",
            "Best Before: 12 months from packing",
            "Consumer Care: care@tataconsumer.com",
        ]
        for i, line in enumerate(lines):
            y = 120 + i * 85
            cv2.putText(img, line, (50, y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        path = os.path.join(self.temp_dir.name, "valid_label.png")
        cv2.imwrite(path, img)

        res = image_gate.prepare_audit_input(path)
        self.assertTrue(res["proceed"])
        self.assertEqual(res["audit_status"], "READY")
        self.assertEqual(res["image"]["status"], image_gate.OK)


if __name__ == "__main__":
    unittest.main()
