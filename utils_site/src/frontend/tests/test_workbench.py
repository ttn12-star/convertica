# utils_site/src/frontend/tests/test_workbench.py
"""Workbench: catalog built from TOOL_CONFIGS, tier limits, page view."""

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import translation


class WorkbenchCatalogTests(TestCase):
    def setUp(self):
        from src.frontend.workbench import build_catalog

        translation.activate("en")
        self.catalog = build_catalog()

    def tearDown(self):
        translation.deactivate()

    def test_every_entry_has_resolvable_urls(self):
        self.assertGreaterEqual(len(self.catalog), 40)
        for key, entry in self.catalog.items():
            self.assertTrue(entry["pageUrl"].startswith("/"), key)
            self.assertTrue(entry["apiUrl"].startswith("/api/"), key)
            self.assertTrue(entry["label"], key)
            self.assertIn(
                entry["group"],
                {"convert", "edit", "organize", "security", "epub", "image", "archive"},
                key,
            )

    def test_converter_generic_tools_are_droppable(self):
        for key in ("pdf_to_word", "word_to_pdf", "excel_to_pdf", "pdf_to_jpg"):
            self.assertTrue(self.catalog[key]["droppable"], key)
        self.assertGreaterEqual(
            sum(1 for e in self.catalog.values() if e["droppable"]), 20
        )

    def test_editors_are_not_droppable(self):
        for key in ("sign_pdf", "add_text_pdf", "pdf_editor", "rotate_pdf"):
            self.assertFalse(self.catalog[key]["droppable"], key)

    def test_batch_route_is_exposed(self):
        entry = self.catalog["pdf_to_word"]
        self.assertEqual(entry["batchApiUrl"], reverse("pdf_to_word_batch_api"))
        self.assertEqual(entry["batchFieldName"], "pdf_files")
        self.assertIsNone(self.catalog["pdf_to_pdfa"]["batchApiUrl"])

    def test_async_twin_is_exposed(self):
        entry = self.catalog["pdf_to_word"]
        self.assertEqual(entry["asyncApiUrl"], reverse("pdf_to_word_async_api"))
        # Generic ^(?P<batch_route>.+/batch)/async/$ twin.
        self.assertEqual(entry["batchAsyncApiUrl"], entry["batchApiUrl"] + "async/")
        # convert_image has no /async/ route; batch does have the generic twin.
        self.assertIsNone(self.catalog["convert_image"]["asyncApiUrl"])
        self.assertIsNotNone(self.catalog["convert_image"]["batchAsyncApiUrl"])
        # No batch route → no batch async twin.
        self.assertIsNone(self.catalog["pdf_to_pdfa"]["batchAsyncApiUrl"])

    def test_requires_config_keys_are_droppable_catalog_entries(self):
        from src.frontend.workbench import REQUIRES_CONFIG_KEYS

        self.assertTrue(REQUIRES_CONFIG_KEYS)
        for key in REQUIRES_CONFIG_KEYS:
            self.assertIn(key, self.catalog, key)
            self.assertTrue(self.catalog[key]["droppable"], key)
            self.assertTrue(self.catalog[key]["requiresConfig"], key)
        self.assertFalse(self.catalog["pdf_to_word"]["requiresConfig"])

    def test_premium_only_keys_exist_in_catalog(self):
        from src.frontend.workbench import PREMIUM_ONLY_KEYS

        self.assertTrue(PREMIUM_ONLY_KEYS)
        for key in PREMIUM_ONLY_KEYS:
            self.assertIn(key, self.catalog)
            self.assertTrue(self.catalog[key]["premiumOnly"])
        self.assertFalse(self.catalog["pdf_to_word"]["premiumOnly"])

    def test_label_is_str_not_lazy(self):
        self.assertIs(type(self.catalog["pdf_to_word"]["label"]), str)


class WorkbenchLimitsTests(TestCase):
    def setUp(self):
        # locmem test cache is shared across tests and PKs get reused after
        # each test's transaction rollback, so a premium-cache hit from one
        # test can leak into the next (see memory
        # project_flaky_premium_gating_subscription_cache).
        from django.core.cache import cache

        cache.clear()

    def _request(self, user=None):
        request = RequestFactory().get("/workbench/")
        from django.contrib.auth.models import AnonymousUser

        request.user = user or AnonymousUser()
        return request

    def test_anonymous(self):
        from src.frontend.workbench import limits_for

        self.assertEqual(
            limits_for(self._request()),
            {
                "tier": "anonymous",
                "boards": 1,
                "tiles": 3,
                "sync": False,
                "system": False,
            },
        )

    def test_registered(self):
        from src.frontend.workbench import limits_for

        user = get_user_model().objects.create_user(
            username="wbr", email="wbr@example.com", password="x"
        )
        self.assertEqual(limits_for(self._request(user))["tier"], "registered")
        self.assertEqual(limits_for(self._request(user))["tiles"], 6)

    def test_premium(self):
        from src.frontend.workbench import limits_for

        user = get_user_model().objects.create_user(
            username="wbp", email="wbp@example.com", password="x", is_premium=True
        )
        limits = limits_for(self._request(user))
        self.assertEqual(
            limits,
            {"tier": "premium", "boards": 5, "tiles": 20, "sync": True, "system": True},
        )


class WorkbenchPageTests(TestCase):
    def test_page_renders_with_catalog_and_limits(self):
        response = self.client.get(reverse("frontend:workbench_page"))
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        self.assertIn('id="workbench-catalog"', html)
        self.assertIn('id="workbench-limits"', html)
        self.assertIn('"tier": "anonymous"', html)
        self.assertIn("noindex", html)
        self.assertIn('id="wb-tile-template"', html)

    def test_page_is_not_cached_across_users(self):
        # anonymous_cache_page must NOT wrap this view: limits differ per tier.
        from src.frontend import views

        self.assertFalse(hasattr(views.workbench_page, "__wrapped__"))

    @override_settings(WORKBENCH_ENABLED=False)
    def test_kill_switch_returns_404(self):
        self.assertEqual(
            self.client.get(reverse("frontend:workbench_page")).status_code, 404
        )


class WorkbenchTemplatesTests(TestCase):
    def test_templates_resolve_to_droppable_tools(self):
        from django.utils import translation
        from src.frontend.workbench import (
            BOARD_TEMPLATES,
            build_catalog,
            build_templates,
        )

        translation.activate("en")
        catalog = build_catalog()
        templates = build_templates(catalog)
        self.assertEqual([t["key"] for t in templates], ["office", "scans", "images"])
        for template in templates:
            self.assertIs(type(template["name"]), str)
            self.assertGreaterEqual(len(template["tools"]), 2)
            for key in template["tools"]:
                self.assertTrue(catalog[key]["droppable"], key)
                self.assertFalse(catalog[key]["requiresConfig"], key)
        self.assertEqual(len(BOARD_TEMPLATES), 3)

    def test_page_inlines_templates(self):
        html = self.client.get(reverse("frontend:workbench_page")).content.decode()
        self.assertIn('id="workbench-templates"', html)
        self.assertIn('"office"', html)
