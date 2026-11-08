"""Cloudflare Web Analytics beacon is on the page and the CSP lets it run.

The zone-level auto-inject never fired here (strict CSP), so the beacon lives in
base.html; without both CSP hosts the browser silently drops it and the
dashboard just shows zero visits.
"""

from django.test import TestCase


class CloudflareInsightsCSPTests(TestCase):
    def test_beacon_present_and_allowed(self):
        r = self.client.get("/en/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(
            "https://static.cloudflareinsights.com/beacon.min.js", r.content.decode()
        )
        csp = dict(
            d.strip().split(" ", 1)
            for d in r["Content-Security-Policy"].split(";")
            if " " in d.strip()
        )
        self.assertIn("https://static.cloudflareinsights.com", csp["script-src"])
        self.assertIn("https://cloudflareinsights.com", csp["connect-src"])

    def test_privacy_discloses_web_analytics_translated(self):
        r = self.client.get("/pl/privacy/")
        self.assertEqual(r.status_code, 200)
        html = r.content.decode()
        self.assertIn("Cloudflare Web Analytics", html)
        self.assertIn("art. 6 ust. 1 lit. f RODO", html)
