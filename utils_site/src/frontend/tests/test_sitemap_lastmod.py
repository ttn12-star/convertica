"""Sitemap lastmod stability (CONVERTICA review C3).

Static/tool pages stamped <lastmod> with datetime.now() on every 24h
regeneration, so every URL claimed to change every day and Google learned to
distrust the signal. Static/tool lastmod must come from a stable configured
date; blog articles keep their real updated_at.
"""

from __future__ import annotations

from django.test import TestCase, override_settings


class SitemapLastmodTests(TestCase):
    @override_settings(SITEMAP_STATIC_LASTMOD="2020-02-02")
    def test_static_pages_use_stable_lastmod(self):
        from django.core.cache import cache

        cache.clear()
        resp = self.client.get("/sitemap-en.xml")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode()
        # Homepage (a static page) must carry the stable date, not today's.
        self.assertIn("<lastmod>2020-02-02</lastmod>", body)
