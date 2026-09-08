import unittest

try:
    from fastapi.testclient import TestClient
    from backend.app import app
    HAS_FASTAPI = True
except ImportError:
    HAS_FASTAPI = False
    TestClient = None
    app = None


@unittest.skipUnless(HAS_FASTAPI, "FastAPI or TestClient dependencies not installed in current Python env")
class TestFastAPIEndpoints(unittest.TestCase):
    """Test suite for FastAPI endpoints."""

    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_check(self):
        """GET /api/health should return 200 and healthy status."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "Kraya-Rakshak")

    def test_invalid_image_upload_type(self):
        """POST /api/audit/image should reject non-image file types."""
        response = self.client.post(
            "/api/audit/image",
            files={"file": ("test.txt", b"plain text", "text/plain")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Unsupported file type", response.json()["detail"])

    def test_invalid_url_format(self):
        """POST /api/audit/url should reject malformed URLs."""
        response = self.client.post(
            "/api/audit/url",
            data={"url": "not-a-valid-url"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid URL", response.json()["detail"])

    def test_image_gate_refuses_invalid_image(self):
        """POST /api/audit/image should refuse non-label image (e.g. too small) with audit_recorded=False."""
        import cv2, numpy as np
        small_img = np.zeros((200, 200, 3), dtype=np.uint8)
        _, buf = cv2.imencode(".jpg", small_img)
        response = self.client.post(
            "/api/audit/image",
            files={"file": ("small.jpg", buf.tobytes(), "image/jpeg")},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["audit_recorded"])
        self.assertIsNone(data["verdict"])
        self.assertEqual(data["status"], "REFUSED")
        self.assertEqual(data["image_assessment"]["status"], "TOO_SMALL")
        self.assertIn("at least 400px", data["reason"])

    def test_post_draft_notice_improvement(self):
        """POST /api/notice/draft for 1st contravention returns IMPROVEMENT_NOTICE."""
        payload = {
            "item": {
                "name": "Tata Tea Premium 500g",
                "manufacturer": "Tata Consumer Products Ltd",
                "barcode": "8901030383478",
                "data_source": "Automated OCR Scan",
                "checks": ["Net Quantity Missing"],
            },
            "failures": [
                {"rule_id": "NET_QUANTITY", "found": "No unit specified"}
            ],
            "officer_name": "Inspector Test Officer",
            "ref": "LMPC/TEST/001",
            "offence_number": 1,
        }
        response = self.client.post("/api/notice/draft", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["instrument"], "IMPROVEMENT_NOTICE")
        self.assertIn("SECTION 15(6)", data["text"])
        self.assertIn("Tata Consumer Products Ltd", data["text"])
        self.assertIn("Inspector Test Officer", data["text"])

    def test_post_draft_notice_show_cause(self):
        """POST /api/notice/draft for 2nd contravention returns SHOW_CAUSE."""
        payload = {
            "item": {
                "name": "Sample Commodity",
                "manufacturer": "Sample Manufacturer",
                "barcode": "8900000000000",
                "data_source": "Field Inspection",
                "checks": ["Missing MRP"],
            },
            "failures": [
                {"rule_id": "MRP", "found": "No MRP declared"}
            ],
            "officer_name": "Inspector Test Officer",
            "ref": "LMPC/TEST/002",
            "offence_number": 2,
        }
        response = self.client.post("/api/notice/draft", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["instrument"], "SHOW_CAUSE")
        self.assertIn("SHOW CAUSE NOTICE", data["text"])
        self.assertIn("contravention number 2", data["text"])

    def test_image_audit_stores_real_image_path(self):
        """POST /api/audit/image should persist uploaded file to disk and record image_path in DB."""
        from unittest.mock import patch
        from pathlib import Path
        import json
        import lmpc_extraction as ext

        mock_gate = {
            "proceed": True,
            "image": {"status": "OK", "width": 800, "height": 800},
            "barcode": {"status": "BARCODE_OK", "barcode": "8901234567890"},
            "audit_status": "READY",
            "user_message": "OK",
            "guidance": "",
        }

        mock_gemini_raw = {
            "is_product_label": True,
            "what_it_shows": "Tea packaging declaration panel",
            "fields": {
                k: {
                    "value": f"Valid {k}",
                    "quoted_text": f"Quoted {k}",
                    "confidence": 0.95,
                    "bbox": [10, 10, 100, 20],
                }
                for k in ext.FIELD_KEYS
            },
        }

        with patch("backend.app.vision.prepare_audit_input", return_value=mock_gate), \
             patch("backend.app.call_gemini", return_value=mock_gemini_raw), \
             patch("backend.app.persist_audit_from_extraction", return_value="mock-audit-uuid-1234") as mock_persist:

            dummy_img_bytes = b"\xff\xd8\xff\xe0" + b"\x00" * 500
            response = self.client.post(
                "/api/audit/image",
                files={"file": ("sample_pack.jpg", dummy_img_bytes, "image/jpeg")},
            )
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertTrue(data["audit_recorded"])
            self.assertEqual(data.get("audit_id"), "mock-audit-uuid-1234")
            self.assertIsNotNone(data.get("image_path"))
            
            # Verify file exists on disk
            saved_path = Path(data["image_path"])
            self.assertTrue(saved_path.exists())
            self.assertGreater(saved_path.stat().st_size, 0)

            # Verify persist was called with the exact stored image path
            mock_persist.assert_called_once()
            called_path = mock_persist.call_args[1].get("image_path")
            self.assertEqual(called_path, data["image_path"])

    def test_save_upload_persists_file(self):
        """save_upload persists bytes and returns path inside backend/uploads."""
        from io import BytesIO
        from starlette.datastructures import UploadFile
        from backend.app import save_upload
        from pathlib import Path

        dummy_data = b"LMPC PACKAGING COMPLIANCE TEST"
        mock_file = UploadFile(filename="test_label.jpg", file=BytesIO(dummy_data))
        path_str = save_upload(mock_file)
        
        path = Path(path_str)
        self.assertTrue(path.exists())
        self.assertEqual(path.read_bytes(), dummy_data)
        self.assertIn("uploads", path_str)

    def test_scan_barcode_distinct_products(self):
        """POST /api/scan with different barcodes returns distinct, authentic products."""
        # 1. Tata Tea Gold 500g
        res1 = self.client.post("/api/scan", data={"barcode": "8901030383478"})
        self.assertEqual(res1.status_code, 200)
        data1 = res1.json()
        pname1 = data1["extractions"]["product_name"]["value"]
        self.assertIn("Tata Tea", pname1)
        self.assertEqual(data1["verdict"]["overall_status"], "COMPLIANT")

        # 2. Amul Pure Ghee 1L
        res2 = self.client.post("/api/scan", data={"barcode": "8901262010053"})
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        pname2 = data2["extractions"]["product_name"]["value"]
        self.assertIn("Amul", pname2)
        self.assertNotEqual(pname1, pname2)
        self.assertEqual(data2["extractions"]["net_quantity"]["value"], "1 L")

        # 3. Royal Shahi Garam Masala (Violations)
        res3 = self.client.post("/api/scan", data={"barcode": "8909999999999"})
        self.assertEqual(res3.status_code, 200)
        data3 = res3.json()
        pname3 = data3["extractions"]["product_name"]["value"]
        self.assertIn("Garam Masala", pname3)
        self.assertNotEqual(pname1, pname3)
        self.assertIn(data3["verdict"]["overall_status"], ("NON_COMPLIANT", "PARTIAL_VIOLATION"))
        self.assertGreater(len(data3["verdict"]["violations"]), 0)

        # 4. Swiss Cocoa Crunch (Imported Discrepancy)
        res4 = self.client.post("/api/scan", data={"barcode": "7613035678901"})
        self.assertEqual(res4.status_code, 200)
        data4 = res4.json()
        pname4 = data4["extractions"]["product_name"]["value"]
        self.assertIn("Swiss Cocoa", pname4)
        self.assertNotEqual(pname1, pname4)
        self.assertEqual(data4["extractions"]["country_of_origin"]["value"], "Switzerland")

        # 5. Dynamic Unregistered Barcode (synthesizes unique product)
        res5 = self.client.post("/api/scan", data={"barcode": "8905544332211"})
        self.assertEqual(res5.status_code, 200)
        data5 = res5.json()
        pname5 = data5["extractions"]["product_name"]["value"]
        self.assertNotEqual(pname1, pname5)
        self.assertNotEqual(pname2, pname5)
        self.assertIn("2211", pname5)


if __name__ == "__main__":
    unittest.main()


