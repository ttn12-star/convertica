# utils_site/src/frontend/tests/test_install_page.py
from django.test import TestCase
from django.urls import reverse
from django.utils import translation


class InstallPageTests(TestCase):
    def setUp(self):
        # These assertions are on English copy, and reverse() builds the URL with
        # whatever language is currently active under i18n_patterns. Without
        # pinning it, a test that left another language active in this worker made
        # the page render translated and these fail depending on run order.
        translation.activate("en")

    def tearDown(self):
        translation.deactivate()

    def test_install_page_returns_200(self):
        resp = self.client.get(reverse("frontend:install_page"))
        self.assertEqual(resp.status_code, 200)

    def test_install_page_mentions_platforms(self):
        resp = self.client.get(reverse("frontend:install_page"))
        body = resp.content.decode()
        self.assertIn("iPhone", body)  # iOS manual-install section
        self.assertIn("Android", body)

    def test_has_ios_manual_step(self):
        body = self.client.get(reverse("frontend:install_page")).content.decode()
        self.assertIn("Add to Home Screen", body)

    def test_cross_device_is_honest_about_files(self):
        # We must NOT promise file/session sync — the page must state files
        # are never stored/synced.
        body = self.client.get(reverse("frontend:install_page")).content.decode()
        self.assertRegex(body.lower(), r"files? (are|is) never (stored|synced)")

    def test_faqpage_schema_present(self):
        body = self.client.get(reverse("frontend:install_page")).content.decode()
        self.assertIn('"@type": "FAQPage"', body)

    def test_install_in_sitemap(self):
        from src.frontend.views import _get_sitemap_pages

        urls = {p["url"] for p in _get_sitemap_pages()}
        self.assertIn("install/", urls)
