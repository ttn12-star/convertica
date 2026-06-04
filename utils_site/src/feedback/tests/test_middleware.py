from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from src.api.tests.test_flatten_pdf import _make_filled_form_pdf
from src.feedback.tokens import resolve_feedback_token


class FeedbackTokenMiddlewareTests(TestCase):
    """The middleware stamps the token on tool downloads whose view doesn't
    set it itself (custom views like merge, batch ZIPs, post_async)."""

    def test_merge_download_gets_token_via_middleware(self):
        client = Client()
        f1 = SimpleUploadedFile(
            "a.pdf", _make_filled_form_pdf(), content_type="application/pdf"
        )
        f2 = SimpleUploadedFile(
            "b.pdf", _make_filled_form_pdf(), content_type="application/pdf"
        )
        resp = client.post("/api/pdf-organize/merge/", {"pdf_files": [f1, f2]})
        self.assertEqual(resp.status_code, 200)
        token = resp.headers.get("X-Convertica-Feedback-Token")
        self.assertIsNotNone(token, "merge response should carry a feedback token")
        kind, value = resolve_feedback_token(token)
        self.assertEqual(kind, "s")
        self.assertEqual(value, "MERGE_PDF")
