"""SSRF guard tests for HTML/URL -> PDF (CONVERTICA review, 2026-05-29).

The pre-navigation URL check resolves DNS once, but ``page.goto`` then follows
redirects (re-resolving) and loads embedded sub-resources, none of which were
re-validated. HTML->PDF additionally rendered user HTML from a ``file://``
origin. Together this allowed SSRF to internal/metadata hosts and local-file
reads. The fix installs a Playwright route guard that re-validates EVERY
request (initial, redirect, sub-resource) and aborts unsafe ones, and renders
HTML via ``set_content`` instead of ``file://``.

These tests exercise the guard decision with no real browser, using IP
literals (``getaddrinfo`` resolves those without a network lookup) so they are
deterministic offline.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

from asgiref.sync import async_to_sync
from django.test import SimpleTestCase
from src.api.html_convert.utils import HTMLToPDFConverter


class ValidateUrlSSRFTests(SimpleTestCase):
    def setUp(self):
        self.converter = HTMLToPDFConverter()

    def test_blocks_cloud_metadata_ip(self):
        ok, _ = self.converter._validate_url("http://169.254.169.254/latest/meta-data/")
        self.assertFalse(ok)

    def test_blocks_loopback(self):
        ok, _ = self.converter._validate_url("http://127.0.0.1:6379/")
        self.assertFalse(ok)

    def test_blocks_private_range(self):
        ok, _ = self.converter._validate_url("http://10.0.0.5/")
        self.assertFalse(ok)

    def test_rejects_non_http_scheme(self):
        ok, _ = self.converter._validate_url("file:///etc/passwd")
        self.assertFalse(ok)

    def test_allows_public_ip(self):
        ok, _ = self.converter._validate_url("http://8.8.8.8/")
        self.assertTrue(ok)


class RouteGuardTests(SimpleTestCase):
    def setUp(self):
        self.converter = HTMLToPDFConverter()

    def _run_guard(self, url):
        route = AsyncMock()
        route.request.url = url
        async_to_sync(self.converter._route_guard)(route)
        return route

    def test_aborts_request_to_metadata_host(self):
        route = self._run_guard("http://169.254.169.254/latest/meta-data/iam/")
        route.abort.assert_awaited()
        route.continue_.assert_not_awaited()

    def test_aborts_file_scheme_subresource(self):
        route = self._run_guard("file:///etc/passwd")
        route.abort.assert_awaited()
        route.continue_.assert_not_awaited()

    def test_continues_public_request(self):
        route = self._run_guard("http://8.8.8.8/page.css")
        route.continue_.assert_awaited()
        route.abort.assert_not_awaited()
