"""Tests for the Password Protect Image tool page."""

from django.core.cache import cache
from django.test import Client, TestCase
from django.urls import reverse


class PasswordProtectImagePageTestCase(TestCase):
    """Render checks for the password-protect-image tool page."""

    def setUp(self):
        cache.clear()
        self.client = Client()

    def test_page_renders_with_expected_content(self):
        response = self.client.get(
            reverse("frontend:password_protect_image_page"), follow=True
        )
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        self.assertIn("Password Protect Image", html)
        self.assertIn('name="password"', html)
        self.assertIn("How do I password protect a photo?", html)
