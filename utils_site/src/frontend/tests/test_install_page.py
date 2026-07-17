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
