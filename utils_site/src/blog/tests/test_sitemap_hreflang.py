"""Article hreflang in the sitemap must reflect real translations (review C4).

The sitemap emitted xhtml:link alternates for all 7 languages for every
article, even when a language had no translation (the page then served English
under a /xx/ URL). Google reads that as 'Duplicate, Google chose a different
canonical' and as hreflang return-tag mismatches. Only emit a language's
alternate (and list the article in that language's sitemap) when the article is
actually translated into it (English base always counts).
"""

from __future__ import annotations

from django.test import TestCase
from src.blog.models import Article


class ArticleSitemapHreflangTests(TestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()
        self.article = Article.objects.create(
            title_en="Hello",
            slug="hello-world",
            content_en="Body",
            status="published",
            translations={"ru": {"title": "Привет", "content": "Тело"}},
        )

    def test_en_sitemap_only_lists_available_language_alternates(self):
        body = self.client.get("/sitemap-en.xml").content.decode()
        # Static pages are translated in all 7 languages, so their all-language
        # hreflang is correct — C4 only constrains ARTICLE alternates. Scope the
        # assertion to the article's own <url> block.
        block = ""
        for chunk in body.split("<url>"):
            if "hello-world" in chunk:
                block = chunk.split("</url>")[0]
                break
        self.assertIn('hreflang="en"', block)
        self.assertIn('hreflang="ru"', block)
        self.assertIn('hreflang="x-default"', block)
        for absent in ("pl", "hi", "es", "id", "ar"):
            self.assertNotIn(f'hreflang="{absent}"', block)

    def test_untranslated_language_sitemap_omits_article(self):
        body = self.client.get("/sitemap-pl.xml").content.decode()
        self.assertNotIn("hello-world", body)

    def test_translated_language_sitemap_includes_article(self):
        body = self.client.get("/sitemap-ru.xml").content.decode()
        self.assertIn("hello-world", body)
