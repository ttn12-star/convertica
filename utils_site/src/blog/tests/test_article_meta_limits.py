"""Article meta tags must survive the SEO filters intact, and no two articles
may render the same title.

Yandex Webmaster flagged /hi/ and /en/ free-adobe-acrobat-alternatives-2026 as
sharing a title. The YAML titles were in fact different, but only after " - ":
seo_title trims to 60 chars at the last clause boundary, so
"Free Adobe Acrobat Alternatives 2026 - Full Comparison" and
"... - पूरी Comparison" collapsed to one string. A title-length check alone
would not have caught that, so this walks the whole corpus through the real
filters and compares rendered output.
"""

from __future__ import annotations

from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase
from src.frontend.templatetags.seo_extras import seo_meta, seo_title

CORPUS = Path(settings.BASE_DIR) / "content" / "blog_articles"
TITLE_LIMIT = 60
DESC_LIMIT = 200


def _articles():
    """Yield (locale, slug, data) for every article in the corpus."""
    for path in sorted(CORPUS.glob("*/*.yaml")):
        locale = path.parent.name
        yield locale, path.stem, yaml.safe_load(path.read_text(encoding="utf-8"))


class ArticleMetaLimitTests(SimpleTestCase):
    def test_meta_titles_are_not_truncated(self):
        """A title over the limit loses whatever sits at its end, which is
        usually the part that distinguishes it from its other-locale twins."""
        too_long = [
            (locale, slug, len(title))
            for locale, slug, data in _articles()
            if (title := data.get(f"meta_title_{locale}") or "")
            and len(title) > TITLE_LIMIT
        ]
        self.assertEqual(
            too_long, [], f"meta_title over {TITLE_LIMIT} chars: {too_long}"
        )

    def test_meta_descriptions_are_not_truncated(self):
        too_long = [
            (locale, slug, len(desc))
            for locale, slug, data in _articles()
            if (desc := data.get(f"meta_description_{locale}") or "")
            and len(desc) > DESC_LIMIT
        ]
        self.assertEqual(
            too_long, [], f"meta_description over {DESC_LIMIT} chars: {too_long}"
        )

    def test_no_two_articles_render_the_same_title(self):
        """Compares post-filter output, because the filter itself can collapse
        two distinct titles into one (the bug this test exists for)."""
        rendered: dict[str, list[str]] = {}
        for locale, slug, data in _articles():
            base = data.get(f"meta_title_{locale}") or data.get(f"title_{locale}") or ""
            if not base:
                continue
            if "|" not in base:
                base = f"{base} | Convertica"
            rendered.setdefault(seo_title(base), []).append(f"{locale}/{slug}")
        collisions = {title: urls for title, urls in rendered.items() if len(urls) > 1}
        self.assertEqual(collisions, {}, f"rendered title collisions: {collisions}")

    def test_filters_leave_compliant_meta_untouched(self):
        """Guards the limits above against drifting apart from the filters."""
        for locale, slug, data in _articles():
            title = data.get(f"meta_title_{locale}") or ""
            desc = data.get(f"meta_description_{locale}") or ""
            with self.subTest(locale=locale, slug=slug):
                if title:
                    self.assertEqual(seo_title(title), title.strip())
                if desc:
                    self.assertEqual(seo_meta(desc), desc.strip())
