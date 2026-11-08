"""Cloudflare Web Analytics beacon is on the page and the CSP lets it run.

The zone-level auto-inject never fired here (strict CSP), so the beacon lives in
base.html; without both CSP hosts the browser silently drops it and the
dashboard just shows zero visits.
"""

from pathlib import Path

from django.test import TestCase

LOCALE = Path(__file__).resolve().parents[4] / "locale"


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

    def test_privacy_discloses_web_analytics_in_every_locale(self):
        r = self.client.get("/en/privacy/")
        self.assertEqual(r.status_code, 200)
        self.assertIn("Cloudflare Web Analytics", r.content.decode())
        msgid = 'msgid "We also use Cloudflare Web Analytics'
        for po in sorted(LOCALE.glob("*/LC_MESSAGES/django.po")):
            text = po.read_text(encoding="utf-8")
            self.assertIn(msgid, text, po)
            if po.parts[-3] != "en":
                msgstr = (
                    text.split(msgid, 1)[1].split("msgstr ", 1)[1].split("\n", 1)[0]
                )
                self.assertNotEqual(msgstr, '""', f"untranslated in {po}")
