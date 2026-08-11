"""Sign-in/sign-up must survive PAYMENTS_ENABLED=False.

The whole account block used to sit inside the payments guard, so turning
payments off (LS closed, Paddle pending) silently removed every entry point to
registration from the nav. The paid entries may hide; the auth ones may not.
"""

from __future__ import annotations

from django.test import TestCase, override_settings
from django.urls import reverse


# The homepage is wrapped in anonymous_cache_page, so without a dummy cache the
# second case would read the first case's HTML.
@override_settings(
    DEBUG=False,
    CACHES={"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}},
)
class HeaderAuthLinksTests(TestCase):
    def _home(self) -> str:
        return self.client.get(reverse("frontend:index_page_lang")).content.decode()

    @override_settings(PAYMENTS_ENABLED=False)
    def test_auth_links_present_and_paid_links_gone_without_payments(self):
        html = self._home()
        self.assertIn(reverse("users:register"), html)
        self.assertIn(reverse("users:login"), html)
        self.assertNotIn(reverse("frontend:pricing"), html)

    @override_settings(PAYMENTS_ENABLED=True)
    def test_auth_links_present_with_payments(self):
        html = self._home()
        self.assertIn(reverse("users:register"), html)
        self.assertIn(reverse("users:login"), html)
        self.assertIn(reverse("frontend:pricing"), html)
