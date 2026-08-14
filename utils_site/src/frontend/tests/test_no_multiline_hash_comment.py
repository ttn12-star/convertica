"""`{# ... #}` comments out one line only. Spanning two renders as page text.

Django's `{# #}` is a single-line comment. Written across two lines it is not a
comment at all: the text is emitted into the page. This has now bitten the site
twice — once leaking into a <script> block and breaking every tool page, once
printing a note about badge rel attributes into the footer of every page on
prod. `{% comment %}` is the multi-line form.

Cheap to check, so check it: scan every template for a `{#` whose `#}` is not on
the same line.
"""

from pathlib import Path

from django.test import TestCase

TEMPLATES = Path(__file__).resolve().parents[4] / "templates"


def _unclosed_hash_comments():
    offenders = []
    for path in sorted(TEMPLATES.rglob("*.html")):
        for number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            # A line may hold several comments; only the last "{#" can dangle.
            if "{#" in line and line.count("{#") > line.count("#}"):
                rel = path.relative_to(TEMPLATES)
                offenders.append(f"{rel}:{number} {line.strip()[:70]}")
    return offenders


class NoMultilineHashCommentTests(TestCase):
    def test_every_hash_comment_closes_on_its_own_line(self):
        offenders = _unclosed_hash_comments()
        self.assertEqual(
            offenders,
            [],
            "{# #} spanning lines renders as page text, use {% comment %}: "
            + "; ".join(offenders),
        )
