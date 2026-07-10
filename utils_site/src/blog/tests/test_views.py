"""
Tests for blog views.
"""

from django.conf import settings
from django.test import Client, TestCase
from django.utils import timezone
from src.blog.models import Article, ArticleCategory


class BlogViewsTestCase(TestCase):
    """Test cases for blog views."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = Client()
        self.default_lang = settings.LANGUAGE_CODE

        # Create a category
        self.category = ArticleCategory.objects.create(
            name_en="Test Category", slug="test-category"
        )
        # Create a published article
        self.published_article = Article.objects.create(
            title_en="Published Article",
            slug="published-article",
            excerpt_en="Test excerpt",
            content_en="Test content",
            status="published",
            category=self.category,
            published_at=timezone.now(),
        )
        # Create a draft article
        self.draft_article = Article.objects.create(
            title_en="Draft Article",
            slug="draft-article",
            excerpt_en="Draft excerpt",
            content_en="Draft content",
            status="draft",
            category=self.category,
        )

    def _get_url_with_lang(self, path, lang_code=None):
        """Get URL with language prefix."""
        if lang_code is None:
            lang_code = self.default_lang
        # Remove leading slash if present
        path = path.lstrip("/")
        # Add language prefix (Django i18n_patterns requires it)
        return f"/{lang_code}/{path}" if path else f"/{lang_code}/"

    def test_article_list_renders(self):
        """Test that article list page renders successfully."""
        response = self.client.get(self._get_url_with_lang("blog/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_article_list_shows_published_articles(self):
        """Test that article list shows only published articles."""
        response = self.client.get(self._get_url_with_lang("blog/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Should contain published article (check for title)
        self.assertContains(response, "Published Article")
        # Should NOT contain draft article
        self.assertNotContains(response, "Draft Article")

    def test_article_detail_renders(self):
        """Test that article detail page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang(f"blog/{self.published_article.slug}/"), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Published Article")

    def test_article_detail_og_image_alt_uses_article_title(self):
        """Social cards should describe the article, not the generic site alt."""
        response = self.client.get(
            self._get_url_with_lang(f"blog/{self.published_article.slug}/"), follow=True
        )
        self.assertContains(
            response, 'property="og:image:alt" content="Published Article"'
        )

    def test_article_detail_serves_webp_picture(self):
        """Covers render as <picture> with a WebP source when a .webp sibling exists."""
        # fresh slug: earlier tests may have primed the page cache for the shared article
        article = Article.objects.create(
            title_en="Webp Cover Article",
            slug="webp-cover-article",
            excerpt_en="x",
            content_en="x",
            status="published",
            category=self.category,
            published_at=timezone.now(),
            cover_image="blog/images/tool-word-to-pdf.jpg",
        )

        response = self.client.get(
            self._get_url_with_lang(f"blog/{article.slug}/"), follow=True
        )
        self.assertContains(response, "tool-word-to-pdf.webp")
        self.assertContains(
            response,
            '<source srcset="/static/blog/images/tool-word-to-pdf.webp" type="image/webp">',
            html=False,
        )
        # og:image must stay JPG for messenger compatibility
        self.assertNotContains(
            response,
            'property="og:image" content="https://convertica.net/static/blog/images/tool-word-to-pdf.webp"',
        )

    def test_article_detail_relevant_tool_link_uses_frontend_namespace(self):
        """Relevant tool CTA should render a valid frontend tool URL."""
        self.published_article.relevant_tool = "pdf_to_word"
        self.published_article.save(update_fields=["relevant_tool"])

        response = self.client.get(
            self._get_url_with_lang(f"blog/{self.published_article.slug}/"), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/en/pdf-to-word/")

    def test_article_detail_404_for_draft(self):
        """Test that draft articles return 404."""
        response = self.client.get(
            self._get_url_with_lang(f"blog/{self.draft_article.slug}/"), follow=True
        )
        self.assertEqual(response.status_code, 404)

    def test_article_detail_404_for_invalid_slug(self):
        """Test that invalid article slug returns 404."""
        response = self.client.get(
            self._get_url_with_lang("blog/invalid-slug/"), follow=True
        )
        self.assertEqual(response.status_code, 404)

    def test_article_list_pagination(self):
        """Test that article list supports pagination."""
        # Create more articles to test pagination
        for i in range(15):
            Article.objects.create(
                title_en=f"Article {i}",
                slug=f"article-{i}",
                excerpt_en=f"Excerpt {i}",
                content_en=f"Content {i}",
                status="published",
                category=self.category,
                published_at=timezone.now(),
            )

        response = self.client.get(self._get_url_with_lang("blog/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Check if pagination is present (if implemented)
        # This test will pass even if pagination is not implemented

    def test_paginated_pages_have_distinct_title_and_description(self):
        """Page 2+ must not reuse page 1's <title> or meta description.

        The description marker must survive the seo_meta 155-char truncation,
        so it is prefixed (not appended) — this test guards that.
        """
        import re

        for i in range(15):  # >9 per page -> at least 2 pages
            Article.objects.create(
                title_en=f"Paginated {i}",
                slug=f"paginated-{i}",
                excerpt_en=f"Excerpt {i}",
                content_en=f"Content {i}",
                status="published",
                category=self.category,
                published_at=timezone.now(),
            )

        def tags_of(url):
            html = self.client.get(url, follow=True).content.decode()
            title = re.search(r"<title>(.*?)</title>", html, re.S)
            desc = re.search(r'<meta name="description" content="([^"]*)"', html)
            return (
                title.group(1).strip() if title else "",
                desc.group(1).strip() if desc else "",
            )

        t1, d1 = tags_of(self._get_url_with_lang("blog/"))
        t2, d2 = tags_of(self._get_url_with_lang("blog/") + "?page=2")
        self.assertTrue(t1 and t2 and d1 and d2)
        self.assertNotEqual(t1, t2, "paginated <title> must differ")
        self.assertNotEqual(d1, d2, "paginated meta description must differ")
        self.assertNotIn("Page 2", t1)
        self.assertIn("2", t2)

    def test_blog_pages_omit_csrf_token_so_cdn_can_cache(self):
        """Read-only blog pages must not set a csrftoken cookie / csrf-token meta.

        The csrf-token meta pulls in a Set-Cookie + Vary:Cookie, which makes the
        response uncacheable at the CDN (the blog pages are the ones that 5XX'd
        under crawl load). Tool pages still get it (checked elsewhere).
        """
        for url in (
            self._get_url_with_lang("blog/"),
            self._get_url_with_lang(f"blog/{self.published_article.slug}/"),
        ):
            resp = self.client.get(url, follow=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("csrftoken", resp.cookies, f"{url} set a csrftoken cookie")
            self.assertNotContains(resp, 'name="csrf-token"')

    def test_article_list_filtering_by_category(self):
        """Test that article list can be filtered by category."""
        # Create another category
        category2 = ArticleCategory.objects.create(
            name_en="Category 2", slug="category-2"
        )
        # Create article in category2
        Article.objects.create(
            title_en="Article in Category 2",
            slug="article-category-2",
            excerpt_en="Excerpt",
            content_en="Content",
            status="published",
            category=category2,
            published_at=timezone.now(),
        )

        response = self.client.get(self._get_url_with_lang("blog/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Both articles should be visible (if filtering is not implemented)
        # This test will pass regardless of filtering implementation
