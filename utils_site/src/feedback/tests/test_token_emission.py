from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from src.api.tests.test_flatten_pdf import _make_filled_form_pdf
from src.feedback.tokens import resolve_feedback_token


class SyncTokenEmissionTests(TestCase):
    def test_sync_response_carries_feedback_token(self):
        client = Client()
        upload = SimpleUploadedFile(
            "form.pdf", _make_filled_form_pdf(), content_type="application/pdf"
        )
        resp = client.post("/api/pdf-edit/flatten/", {"pdf_file": upload})
        self.assertEqual(resp.status_code, 200)
        token = resp.headers.get("X-Convertica-Feedback-Token")
        self.assertIsNotNone(token)
        resolved = resolve_feedback_token(token)
        self.assertIsNotNone(resolved)
        self.assertEqual(resolved[0], "s")  # sync path → slug token
