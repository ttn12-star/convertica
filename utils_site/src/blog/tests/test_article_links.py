"""Every internal link in the article corpus must resolve.

Articles are hand-written YAML in seven languages, so a tool link is just a
string nobody type-checks. A previous audit found 84 dead tool links this way;
they cost crawl budget and send readers to a 404 from the one place we asked
them to click. This walks the whole corpus so a typo fails locally instead of
in production.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml
from django.conf import settings
from django.test import SimpleTestCase
from django.urls import Resolver404, resolve
from django.utils.translation import override

CORPUS = Path(settings.BASE_DIR) / "content" / "blog_articles"
HREF_RE = re.compile(r'href="(/[^"#?]*)"')
LANG_CODES = {code for code, _ in settings.LANGUAGES}


def _article_slugs() -> set[str]:
    return {p.stem for p in (CORPUS / "en").glob("*.yaml")}


def _content_fields(data: dict) -> list[str]:
    """Every field that can contain markup, across base and translation YAML."""
    return [
        v for k, v in data.items() if k.startswith("content_") and isinstance(v, str)
    ]


class ArticleInternalLinkTests(SimpleTestCase):
    def test_every_internal_link_resolves(self):
        self.assertTrue(CORPUS.is_dir(), f"corpus not found at {CORPUS}")
        slugs = _article_slugs()
        broken: list[str] = []

        for yaml_path in sorted(CORPUS.glob("*/*.yaml")):
            data = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                continue
            for content in _content_fields(data):
                for href in sorted(set(HREF_RE.findall(content))):
                    where = f"{yaml_path.parent.name}/{yaml_path.name}: {href}"
                    # Asset paths, not navigation: the favicon guide shows
                    # <link href="/favicon.ico"> markup inside a code sample.
                    # Every real page route ends in a slash, never a filename.
                    if Path(href).suffix:
                        continue
                    # Blog links point at a sibling article, not a URLconf entry:
                    # the detail route matches any slug, so resolve() would pass
                    # even for an article that does not exist.
                    if "/blog/" in href:
                        slug = href.rstrip("/").rsplit("/", 1)[-1]
                        if slug not in slugs and not href.rstrip("/").endswith("blog"):
                            broken.append(f"{where} (no such article)")
                        continue
                    # Tool routes live inside i18n_patterns, so the locale
                    # prefix only resolves while that language is active.
                    lang = href.strip("/").split("/")[0]
                    if lang not in LANG_CODES:
                        broken.append(f"{where} (unknown locale prefix)")
                        continue
                    try:
                        with override(lang):
                            resolve(href)
                    except Resolver404:
                        broken.append(f"{where} (Resolver404)")

        self.assertEqual(broken, [], "Dead internal links:\n  " + "\n  ".join(broken))
