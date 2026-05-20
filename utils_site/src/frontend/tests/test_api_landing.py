from django.test import TestCase
from django.urls import reverse


class APILandingTest(TestCase):
    def test_landing_returns_200(self):
        r = self.client.get(reverse("api_landing"))
        self.assertEqual(r.status_code, 200)

    def test_landing_mentions_dashboard(self):
        r = self.client.get(reverse("api_landing"))
        self.assertContains(r, "/users/api-keys/")

    def test_landing_mentions_docs(self):
        r = self.client.get(reverse("api_landing"))
        self.assertContains(r, "/api/docs/")

    def test_landing_works_under_every_locale_prefix(self):
        # Bare /api/ stays addressable for SEO/direct hits, and the same
        # landing is mirrored under every locale prefix so /ru/api/, /es/api/
        # etc. don't 404 when users click the menu link inside a localized page.
        for locale in ("en", "ru", "es", "pl", "ar", "hi", "id"):
            r = self.client.get(f"/{locale}/api/")
            self.assertEqual(
                r.status_code, 200, f"/{locale}/api/ should serve the landing"
            )
