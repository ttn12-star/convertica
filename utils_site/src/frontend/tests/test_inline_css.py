"""The site stylesheet is inlined (zero render-blocking CSS requests)."""

import re

from django.test import Client, TestCase


class InlineCssTests(TestCase):
    def test_stylesheet_inlined_with_absolutized_font_urls(self):
        html = Client().get("/", follow=True).content.decode()
        # No render-blocking <link> to the bundle…
        self.assertNotIn('rel="stylesheet" href="/static/css/tailwind', html)
        # …the CSS is inline, with url(../fonts/…) rewritten to /static/fonts/…
        # (relative refs would resolve against the page URL and 404 the fonts).
        # The url() may be bare (tailwind build) or quoted (manifest post-process).
        self.assertIn("font-family:Inter", html)
        self.assertRegex(html, r'url\(["\']?/static/fonts/inter/')
        self.assertNotRegex(html, r'url\(["\']?\.\./')
