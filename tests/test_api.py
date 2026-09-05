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


if __name__ == "__main__":
    unittest.main()
