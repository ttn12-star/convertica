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

    def test_every_sitemap_url_serves_an_indexable_200(self):
        """C5 guard: every advertised sitemap URL must serve a real 200 page.

        The hand-maintained _get_sitemap_pages() list is the root cause of the
        C1/C2 drift (a sitemap entry pointing at a redirect/404, or a live tool
        missing). This asserts no entry is stale or non-indexable; a redirect
        (301/302) or 404 fails the test.
        """
        for page in _get_sitemap_pages():
            url = f"/en/{page['url']}"
            with self.subTest(url=url):
                resp = self.client.get(url)
                self.assertEqual(
                    resp.status_code,
                    200,
                    f"{url} returned {resp.status_code} (stale/redirecting "
                    "sitemap entry or broken page)",
                )
