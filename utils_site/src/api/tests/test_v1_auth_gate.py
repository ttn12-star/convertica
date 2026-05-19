from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from src.api.auth.web_token import mint_web_token


@override_settings(RATELIMIT_ENABLE=False)
class V1AuthGateTest(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_anon_raw_call_rejected(self):
        # No Authorization header — should be 401 or 403
        r = self.client.post("/api/v1/jpg-to-pdf/", {})
        self.assertIn(r.status_code, (401, 403))

    def test_web_token_call_proceeds(self):
        # Mint a token, attach it; the view should NOT 401/403 (it'll
        # fail later for missing file, but auth passes).
        token = mint_web_token(scope=["*"], ip="127.0.0.1")
        r = self.client.post(
            "/api/v1/jpg-to-pdf/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # Not 401/403 — should be 400 (no file) or similar
        self.assertNotIn(r.status_code, (401, 403))

    def test_web_token_call_proceeds_pdf_to_word(self):
        token = mint_web_token(scope=["*"], ip="127.0.0.1")
        r = self.client.post(
            "/api/v1/pdf-to-word/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        # 400/415 (no file) or 202 (if it goes async on empty payload) — anything but 401/403
        self.assertNotIn(r.status_code, (401, 403))

    def test_web_token_call_proceeds_compress_pdf(self):
        token = mint_web_token(scope=["*"], ip="127.0.0.1")
        r = self.client.post(
            "/api/v1/pdf-organize/compress/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertNotIn(r.status_code, (401, 403))

    def test_web_token_call_proceeds_image_optimize(self):
        token = mint_web_token(scope=["*"], ip="127.0.0.1")
        r = self.client.post(
            "/api/v1/image/optimize/",
            {},
            HTTP_AUTHORIZATION=f"Bearer {token}",
        )
        self.assertNotIn(r.status_code, (401, 403))
