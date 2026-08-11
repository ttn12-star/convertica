"""Every directory badge in the footer must be allowed by the CSP img-src.

Adding a badge and forgetting the CSP entry has bitten us twice: the badge is
live in the template, the directory's verifier sees it via curl, and every real
browser silently blocks the image. Parse both sides and compare.
"""

import re
from pathlib import Path

from django.test import TestCase

FOOTER = Path(__file__).resolve().parents[4] / "templates/frontend/includes/footer.html"
MIDDLEWARE = Path(__file__).resolve().parents[2] / "api/middleware.py"


def _footer_img_hosts():
    html = FOOTER.read_text(encoding="utf-8")
    row = html.split("Featured on (directory badges", 1)[1]
    return {m.group(1) for m in re.finditer(r'<img src="https://([a-z0-9.-]+)/', row)}


def _csp_img_hosts():
    src = MIDDLEWARE.read_text(encoding="utf-8")
    block = src.split("Backlink directory badges", 1)[1].split("connect-src", 1)[0]
    return {m.group(1) for m in re.finditer(r'"https://([a-z0-9.-]+) ', block)}


class FooterBadgeCSPTests(TestCase):
    def test_every_badge_host_is_in_csp_img_src(self):
        badges = _footer_img_hosts()
        self.assertTrue(badges, "no badge <img> found — did the footer comment change?")
        missing = badges - _csp_img_hosts()
        self.assertEqual(
            missing, set(), f"badge hosts missing from CSP img-src: {sorted(missing)}"
        )
