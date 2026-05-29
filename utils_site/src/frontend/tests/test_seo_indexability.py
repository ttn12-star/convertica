"""SEO / indexability regression tests (CONVERTICA review, 2026-05-29).

C1: scanned-pdf-to-word/ 302-redirected anonymous crawlers to /users/login/
    while robots.txt explicitly wanted it crawlable (high-CPC OCR keyword) ->
    "Page with redirect", never indexed. The landing page must serve a 200 to
    anonymous users; only the conversion action stays premium-gated at the API.

C2: the live ZIP tools (archive/protect/, archive/unlock/) were missing from
    the sitemap -> "Discovered - currently not indexed".
"""

from __future__ import annotations

from django.test import TestCase
from django.utils.translation import activate, deactivate
from src.frontend.views import _get_sitemap_pages


class ScannedPdfToWordIndexabilityTests(TestCase):
    def tearDown(self):
        deactivate()

    def test_scanned_pdf_to_word_serves_200_to_anonymous(self):
        activate("en")
        # follow=False: a 302 to /users/login/ is exactly the indexing bug.
        response = self.client.get("/en/scanned-pdf-to-word/")
        self.assertEqual(response.status_code, 200)


class SitemapCoverageTests(TestCase):
    def test_sitemap_includes_live_zip_tools_and_ocr_landing(self):
        urls = {page["url"] for page in _get_sitemap_pages()}
        for expected in (
            "archive/protect/",
            "archive/unlock/",
            "scanned-pdf-to-word/",
        ):
            with self.subTest(url=expected):
                self.assertIn(expected, urls)
