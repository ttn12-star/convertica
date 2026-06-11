"""Social-login URL exposure tests.

Only Google login is live (via the custom /users/google-direct/ flow).
The Facebook button is commented out in the templates and no Facebook
SocialApp exists in production, yet the provider used to be listed in
INSTALLED_APPS — so allauth still routed /accounts/facebook/login/ and
any bot hitting it got an unhandled SocialApp.DoesNotExist (HTTP 500,
Sentry CONVERTICA-5E). Until Facebook login actually launches, the URL
must simply not exist.
"""

from django.test import Client, TestCase


class SocialLoginUrlExposureTests(TestCase):
    def test_facebook_login_url_is_not_routed(self):
        """Unlaunched provider URL must 404, not 500 (CONVERTICA-5E)."""
        response = Client().get("/accounts/facebook/login/")
        self.assertEqual(response.status_code, 404)
