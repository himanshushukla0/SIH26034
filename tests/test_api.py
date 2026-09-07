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
        self.assertEqual(data["service"], "LMPC Compliance Engine")

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


if __name__ == "__main__":
    unittest.main()
