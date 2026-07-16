"""The site stylesheet is inlined (zero render-blocking CSS requests)."""

from django.test import Client, TestCase


class InlineCssTests(TestCase):
    def test_stylesheet_inlined_with_absolutized_font_urls(self):
        html = Client().get("/", follow=True).content.decode()
        # No render-blocking <link> to the bundle…
        self.assertNotIn('rel="stylesheet" href="/static/css/tailwind', html)
        # …the CSS is inline, with url(../fonts/…) rewritten to /static/fonts/…
        # (relative refs would resolve against the page URL and 404 the fonts).
        self.assertIn("font-family:Inter", html)
        self.assertIn("url(/static/fonts/inter/", html)
        self.assertNotIn("url(../", html)
