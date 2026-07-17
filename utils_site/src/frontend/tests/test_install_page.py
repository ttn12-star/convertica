# utils_site/src/frontend/tests/test_install_page.py
from django.test import TestCase
from django.urls import reverse


class InstallPageTests(TestCase):
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
