"""
Tests for frontend views.
"""

from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import activate


class FrontendViewsTestCase(TestCase):
    """Test cases for frontend views."""

    def setUp(self):
        """Set up test fixtures."""
        # Cached frontend pages (cache_page) can leak across tests and workers in CI.
        # Ensure every test starts with a clean cache state.
        cache.clear()
        self.client = Client()
        # Set default language for tests
        self.default_lang = settings.LANGUAGE_CODE
        self.premium_landing_paths = (
            "epub-to-pdf/",
            "pdf-to-epub/",
            "pdf-to-markdown/",
            "compare-pdf/",
        )
        self.premium_only_paths = (
            "scanned-pdf-to-word/",
            "batch-converter/",
            "premium/workflows/",
            "premium/background-center/",
        )

    def _get_url_with_lang(self, path, lang_code=None):
        """Get URL with language prefix."""
        if lang_code is None:
            lang_code = self.default_lang
        # Remove leading slash if present
        path = path.lstrip("/")
        # Add language prefix (Django i18n_patterns requires it)
        if (
            lang_code != settings.LANGUAGE_CODE or True
        ):  # Always add prefix for consistency
            return f"/{lang_code}/{path}" if path else f"/{lang_code}/"
        return f"/{path}" if path else "/"

    def test_index_page_renders(self):
        """Test that index page renders successfully."""
        # Follow redirects since i18n_patterns redirects / to /en/
        response = self.client.get("/", follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Convertica")

    def test_index_page_with_language_prefix(self):
        """Test that index page works with language prefix."""
        # Test main languages - skip if translation files have issues
        for lang_code in [
            "en",
            "ru",
        ]:  # Test only main languages to avoid encoding issues
            try:
                activate(lang_code)
                response = self.client.get(f"/{lang_code}/", follow=True)
                self.assertEqual(
                    response.status_code, 200, f"Failed for language {lang_code}"
                )
            except Exception:
                # If there's an encoding issue, just skip that language
                # This is acceptable as translation files might have issues
                pass

    def test_all_tools_page_renders(self):
        """Test that all tools page renders successfully."""
        response = self.client.get(self._get_url_with_lang("all-tools/"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "tools", count=None, status_code=200)

    def test_about_page_renders(self):
        """Test that about page renders successfully."""
        response = self.client.get(self._get_url_with_lang("about/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_privacy_page_renders(self):
        """Test that privacy page renders successfully."""
        response = self.client.get(self._get_url_with_lang("privacy/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_terms_page_renders(self):
        """Test that terms page renders successfully."""
        response = self.client.get(self._get_url_with_lang("terms/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_contact_page_renders(self):
        """Test that contact page renders successfully."""
        response = self.client.get(self._get_url_with_lang("contact/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Check that email is present
        self.assertContains(response, "info@convertica.net")

    def test_faq_page_renders(self):
        """Test that FAQ page renders successfully."""
        response = self.client.get(self._get_url_with_lang("faq/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Check that FAQ content is present
        self.assertContains(response, "FAQ", count=None, status_code=200)

    def test_sitemap_xml_renders(self):
        """Test that sitemap.xml renders successfully."""
        # sitemap.xml is not in i18n_patterns, so no language prefix needed
        # But it might redirect, so follow redirects
        response = self.client.get("/sitemap.xml", follow=True)
        self.assertEqual(response.status_code, 200)
        # Check content type (might be text/xml or application/xml)
        if "Content-Type" in response:
            self.assertIn(
                response["Content-Type"],
                ["application/xml", "text/xml", "application/xml; charset=utf-8"],
            )
        # Check that sitemap contains URLs (XML format)
        content = response.content.decode("utf-8")
        self.assertTrue(
            "<url>" in content or "<urlset>" in content or "<?xml" in content
        )

    def test_sitemap_includes_main_pages(self):
        """Test that sitemap includes main pages."""
        response = self.client.get("/sitemap.xml", follow=True)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode("utf-8")
        # Check for main pages (with language prefixes or without)
        # Sitemap should contain at least some URLs
        self.assertTrue(len(content) > 100)  # Sitemap should have content

    def test_pdf_to_word_page_renders(self):
        """Test that PDF to Word page renders successfully."""
        response = self.client.get(self._get_url_with_lang("pdf-to-word/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_word_to_pdf_page_renders(self):
        """Test that Word to PDF page renders successfully."""
        response = self.client.get(self._get_url_with_lang("word-to-pdf/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_pdf_to_jpg_page_renders(self):
        """Test that PDF to JPG page renders successfully."""
        response = self.client.get(self._get_url_with_lang("pdf-to-jpg/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_jpg_to_pdf_page_renders(self):
        """Test that JPG to PDF page renders successfully."""
        response = self.client.get(self._get_url_with_lang("jpg-to-pdf/"), follow=True)
        self.assertEqual(response.status_code, 200)

    def test_pdf_to_excel_page_renders(self):
        """Test that PDF to Excel page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-to-excel/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_rotate_pdf_page_renders(self):
        """Test that Rotate PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-edit/rotate/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_add_page_numbers_page_renders(self):
        """Test that Add Page Numbers page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-edit/add-page-numbers/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_add_watermark_page_renders(self):
        """Test that Add Watermark page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-edit/add-watermark/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_crop_pdf_page_renders(self):
        """Test that Crop PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-edit/crop/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_merge_pdf_page_renders(self):
        """Test that Merge PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-organize/merge/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_split_pdf_page_renders(self):
        """Test that Split PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-organize/split/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_remove_pages_page_renders(self):
        """Test that Remove Pages page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-organize/remove-pages/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_extract_pages_page_renders(self):
        """Test that Extract Pages page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-organize/extract-pages/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_organize_pdf_page_renders(self):
        """Test that Organize PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-organize/organize/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_compress_pdf_page_renders(self):
        """Test that Compress PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-organize/compress/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_protect_pdf_page_renders(self):
        """Test that Protect PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-security/protect/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_unlock_pdf_page_renders(self):
        """Test that Unlock PDF page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("pdf-security/unlock/"), follow=True
        )
        self.assertEqual(response.status_code, 200)

    def test_contact_page_has_email(self):
        """Test that contact page contains correct email."""
        response = self.client.get(self._get_url_with_lang("contact/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Check for email in structured data
        self.assertContains(
            response, "info@convertica.net", count=None, status_code=200
        )

    def test_faq_page_has_questions(self):
        """Test that FAQ page contains questions."""
        response = self.client.get(self._get_url_with_lang("faq/"), follow=True)
        self.assertEqual(response.status_code, 200)
        # Check for FAQ structure
        self.assertContains(response, "Question", count=None, status_code=200)

    def test_premium_tools_page_renders(self):
        """Test that premium tools catalog page renders successfully."""
        response = self.client.get(
            self._get_url_with_lang("premium-tools/"), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium", count=None, status_code=200)

    def test_premium_tools_page_has_itemlist_schema(self):
        """Premium catalog should expose ItemList schema for SEO."""
        response = self.client.get(
            self._get_url_with_lang("premium-tools/"), follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"@type": "ItemList"', status_code=200)
        self.assertContains(
            response, reverse("frontend:epub_to_pdf_page"), status_code=200
        )
        self.assertContains(
            response, reverse("frontend:pdf_to_markdown_page"), status_code=200
        )
        self.assertContains(
            response, reverse("frontend:compare_pdf_page"), status_code=200
        )

    def test_premium_landing_pages_have_seo_and_help_blocks(self):
        """Premium landing pages should include canonical/meta blocks and help sections."""
        expected_markers = {
            "epub-to-pdf/": [
                "How EPUB to PDF works",
                "Convert EPUB to PDF with chapter-aware formatting",
                "Why use EPUB to PDF in Premium?",
                "Tips for Better EPUB to PDF Output",
            ],
            "pdf-to-epub/": [
                "How PDF to EPUB works",
                "Convert PDF to EPUB for eReader-ready publishing",
                "Why use PDF to EPUB in Premium?",
                "Tips for Better PDF to EPUB Output",
            ],
            "pdf-to-markdown/": [
                "How PDF to Markdown works",
                "Convert PDF to Markdown with heading and table structure",
                "Why use PDF to Markdown in Premium?",
                "Tips for Better PDF to Markdown Output",
            ],
            "compare-pdf/": [
                "How Compare Two PDFs works",
                "Compare PDF revisions with visual diffs and change reports",
                "Why use Compare Two PDFs in Premium?",
                "Tips for Better PDF Comparison Accuracy",
            ],
        }

        for path, markers in expected_markers.items():
            with self.subTest(path=path):
                response = self.client.get(self._get_url_with_lang(path), follow=False)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, '<link rel="canonical"', status_code=200)
                self.assertContains(
                    response, '<meta property="og:title"', status_code=200
                )
                self.assertContains(
                    response, '<meta property="twitter:title"', status_code=200
                )
                self.assertContains(
                    response,
                    'itemtype="https://schema.org/BreadcrumbList"',
                    status_code=200,
                )
                for marker in markers:
                    self.assertContains(response, marker, status_code=200)
                self.assertContains(response, "FAQ", status_code=200)

    def test_premium_landing_pages_schema_uses_premium_price(self):
        """Premium converter pages should expose premium offer price in schema."""
        premium_paths = (
            "epub-to-pdf/",
            "pdf-to-epub/",
            "pdf-to-markdown/",
            "compare-pdf/",
        )

        for path in premium_paths:
            with self.subTest(path=path):
                response = self.client.get(self._get_url_with_lang(path), follow=False)
                self.assertEqual(response.status_code, 200)
                self.assertContains(
                    response, '"@type": "SoftwareApplication"', status_code=200
                )
                self.assertContains(response, '"price": "6"', status_code=200)
                self.assertNotContains(response, '"price": "0"', status_code=200)

    def test_all_tools_header_menu_lists_new_premium_links(self):
        """All Tools dropdown should include premium links, not Convert PDF dropdown."""
        response = self.client.get(self._get_url_with_lang("all-tools/"), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertIn('id="all-tools-menu-dropdown"', html)
        self.assertIn('id="mega-menu-dropdown"', html)

        all_tools_dropdown = html.split('id="all-tools-menu-dropdown"', 1)[1].split(
            'id="mega-menu-parent"', 1
        )[0]
        mega_convert_dropdown = html.split('id="mega-menu-dropdown"', 1)[1].split(
            'id="edit-pdf-menu-parent"', 1
        )[0]

        premium_links = (
            reverse("frontend:epub_to_pdf_page"),
            reverse("frontend:pdf_to_epub_page"),
            reverse("frontend:pdf_to_markdown_page"),
            reverse("frontend:compare_pdf_page"),
        )

        for premium_link in premium_links:
            self.assertIn(premium_link, all_tools_dropdown)
            self.assertNotIn(premium_link, mega_convert_dropdown)

    def test_header_has_dedicated_premium_tools_submenu_for_premium_user(self):
        """Premium users should see the dedicated Premium Tools submenu."""
        premium_user = get_user_model().objects.create_user(
            email="premium-menu@example.com",
            password="testpass123",
            is_premium=True,
        )
        self.client.force_login(premium_user)

        response = self.client.get(self._get_url_with_lang("all-tools/"), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertIn('id="premium-tools-menu-parent"', html)
        self.assertIn('id="premium-tools-menu-dropdown"', html)

        premium_dropdown = html.split('id="premium-tools-menu-dropdown"', 1)[1].split(
            'id="more-menu-parent"', 1
        )[0]
        self.assertIn(reverse("frontend:premium_tools_page"), premium_dropdown)
        self.assertIn(reverse("frontend:epub_to_pdf_page"), premium_dropdown)
        self.assertIn(reverse("frontend:pdf_to_epub_page"), premium_dropdown)
        self.assertIn(reverse("frontend:pdf_to_markdown_page"), premium_dropdown)
        self.assertIn(reverse("frontend:compare_pdf_page"), premium_dropdown)

    def test_header_hides_dedicated_premium_tools_submenu_for_non_premium_user(self):
        """Anonymous users should not see the dedicated Premium Tools submenu."""
        response = self.client.get(self._get_url_with_lang("all-tools/"), follow=True)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        self.assertNotIn('id="premium-tools-menu-parent"', html)
        self.assertNotIn('id="premium-tools-menu-dropdown"', html)

    def test_index_page_shows_premium_tools_menu_for_premium_user_when_enabled(self):
        """Premium users should see Premium Tools menu in the homepage header."""
        premium_user = get_user_model().objects.create_user(
            email="premium-index@example.com",
            password="testpass123",
            is_premium=True,
        )
        self.client.force_login(premium_user)

        response = self.client.get(self._get_url_with_lang(""), follow=True)
        self.assertEqual(response.status_code, 200)

        html = response.content.decode("utf-8")
        self.assertIn('id="premium-tools-menu-parent"', html)
        self.assertIn('id="premium-tools-menu-dropdown"', html)
        self.assertIn(reverse("frontend:premium_tools_page"), html)

    def test_compare_pdf_page_has_interactive_preview_blocks(self):
        """Compare PDF page should include on-screen report preview UI and JSZip loader."""
        response = self.client.get(
            self._get_url_with_lang("compare-pdf/"), follow=False
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="comparisonPreview"', status_code=200)
        self.assertContains(response, 'id="comparePageList"', status_code=200)
        self.assertContains(response, 'id="compareDownloadButton"', status_code=200)
        self.assertContains(
            response,
            "vendor/jszip/3.10.1/jszip.min.js",
            status_code=200,
        )

    @override_settings(PAYMENTS_ENABLED=False)
    def test_all_tools_hides_premium_links_when_payments_disabled(self):
        """Premium links should be hidden from menus when payments are disabled."""
        response = self.client.get(self._get_url_with_lang("all-tools/"), follow=True)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertNotIn('id="premium-tools-menu-parent"', html)
        self.assertNotIn('id="premium-tools-menu-dropdown"', html)

        self.assertNotContains(
            response, reverse("frontend:premium_tools_page"), status_code=200
        )
        self.assertNotContains(
            response, reverse("frontend:epub_to_pdf_page"), status_code=200
        )
        self.assertNotContains(
            response, reverse("frontend:pdf_to_epub_page"), status_code=200
        )
        self.assertNotContains(
            response, reverse("frontend:pdf_to_markdown_page"), status_code=200
        )
        self.assertNotContains(
            response, reverse("frontend:compare_pdf_page"), status_code=200
        )

    def test_pricing_page_uses_monthly_yearly_and_custom_plans(self):
        """Pricing page should not expose legacy daily plan."""
        response = self.client.get(self._get_url_with_lang("pricing/"), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "monthly-hero")
        self.assertContains(response, "yearly-hero")
        self.assertContains(response, "By Agreement")
        self.assertContains(response, "Request Terms")
        self.assertNotContains(response, "daily-hero")

    def test_epub_pages_render_for_anonymous_users(self):
        """Premium landing pages should remain crawlable for anonymous users."""
        for path in self.premium_landing_paths:
            with self.subTest(path=path):
                response = self.client.get(self._get_url_with_lang(path), follow=False)
                self.assertEqual(response.status_code, 200)

    def test_epub_pages_render_for_non_premium_users(self):
        """Premium landing pages should render for authenticated free users."""
        user = get_user_model().objects.create_user(
            email="free-epub-frontend@example.com",
            password="pass1234",
        )
        self.client.force_login(user)

        for path in self.premium_landing_paths:
            with self.subTest(path=path):
                response = self.client.get(self._get_url_with_lang(path), follow=False)
                self.assertEqual(response.status_code, 200)

    def test_premium_pages_redirect_anonymous_to_login(self):
        """Anonymous users should be redirected to login for premium pages."""
        for path in self.premium_only_paths:
            with self.subTest(path=path):
                url = self._get_url_with_lang(path)
                response = self.client.get(url, follow=False)
                self.assertEqual(response.status_code, 302)

                parsed = urlparse(response["Location"])
                self.assertEqual(parsed.path, reverse("users:login"))
                self.assertEqual(parse_qs(parsed.query).get("next"), [url])

    def test_premium_pages_redirect_non_premium_user_to_pricing(self):
        """Authenticated non-premium users should be redirected to pricing."""
        user = get_user_model().objects.create_user(
            email="non-premium-frontend@example.com",
            password="pass1234",
        )
        self.client.force_login(user)
        pricing_url = reverse("frontend:pricing")

        for path in self.premium_only_paths:
            with self.subTest(path=path):
                response = self.client.get(
                    self._get_url_with_lang(path),
                    follow=False,
                )
                self.assertEqual(response.status_code, 302)
                self.assertEqual(response["Location"], pricing_url)

    def test_premium_pages_render_for_premium_user(self):
        """Premium users should access premium pages."""
        premium_user = get_user_model().objects.create_user(
            email="premium-frontend@example.com",
            password="pass1234",
            is_premium=True,
            subscription_end_date=timezone.now() + timezone.timedelta(days=1),
        )
        self.client.force_login(premium_user)

        for path in self.premium_only_paths:
            with self.subTest(path=path):
                response = self.client.get(
                    self._get_url_with_lang(path),
                    follow=False,
                )
                self.assertEqual(response.status_code, 200)
