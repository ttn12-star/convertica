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

    def test_url_is_locale_less(self):
        # /api/ is OUTSIDE i18n_patterns. /en/api/ should NOT resolve to landing.
        r = self.client.get("/en/api/")
        # Either 404 or redirect — anything except 200-with-landing
        self.assertNotEqual(r.status_code, 200)
