from django.test import Client, TestCase
from django.urls import reverse


class PdfEditorPageTests(TestCase):
    def test_page_renders_en(self):
        resp = Client().get("/en/pdf-editor/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PDF Editor")

    def test_page_has_free_offer_jsonld(self):
        resp = Client().get("/en/pdf-editor/")
        self.assertContains(resp, '"price": "0"')

    def test_reverse(self):
        path = reverse("frontend:pdf_editor_page")
        self.assertTrue(path.endswith("/pdf-editor/"))
