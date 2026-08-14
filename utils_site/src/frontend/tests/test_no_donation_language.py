"""The pages a merchant of record scans must not read like a donation page.

Lemon Squeezy closed our account and Paddle rejected the application with the
category "Other/Donations". The Ko-fi page was only half of it: /pricing/ (the
URL we ourselves submit as the payment link) and the home page carried
"Support Our Project", "this project survives solely through the support of
users like you" and "you're not just a user, you're a project partner". A risk
classifier reads that as patronage, whatever the checkout actually sells.

So the wording is a compliance surface, not taste. This test fails if it comes
back. Plan names ("Hero", "Heroes Hall of Fame") are deliberate branding and
stay allowed: they describe who subscribed, not a plea for support.
"""

import re
from pathlib import Path

from django.test import TestCase

TEMPLATES = Path(__file__).resolve().parents[4] / "templates/frontend"
SCANNED = ("pricing.html", "index.html")

# Each pattern is wording that reads as soliciting donations rather than
# selling a subscription.
FORBIDDEN = (
    r"support (?:our|the) project",
    r"\bdonat",  # donate, donation, donations
    r"ko-?fi",
    r"buy me a coffee",
    r"venture capital",
    r"survives solely",
    r"project partner",
    r"your support (?:powers|matters|keeps)",
)


class NoDonationLanguageTests(TestCase):
    def test_scanned_pages_do_not_solicit_support(self):
        offenders = []
        for name in SCANNED:
            text = (TEMPLATES / name).read_text(encoding="utf-8")
            for pattern in FORBIDDEN:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    line = text.count("\n", 0, match.start()) + 1
                    offenders.append(f"{name}:{line} {match.group(0)!r}")
        self.assertEqual(
            offenders,
            [],
            "donation wording is back on a page payment providers scan: "
            + "; ".join(offenders),
        )
