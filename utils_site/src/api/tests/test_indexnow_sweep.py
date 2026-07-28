"""Tests for the IndexNow sitemap-sweep maintenance task.

Manual/one-shot only — it is deliberately off the beat schedule (a nightly full
sweep is the "IndexNow is in batch mode" warning in Bing Webmaster Tools).
Routine per-locale pings happen in src.blog.signals on real article changes.
"""

from __future__ import annotations

from unittest import mock

from django.test import SimpleTestCase, override_settings
from src.tasks.maintenance import submit_sitemap_indexnow


class IndexNowSweepTaskTests(SimpleTestCase):
    @override_settings(INDEXNOW_ENABLED=False, INDEXNOW_KEY="")
    def test_skips_when_disabled(self):
        # Must not call the command or raise when IndexNow is off (e.g. dev).
        with mock.patch("django.core.management.call_command") as called:
            result = submit_sitemap_indexnow()
        self.assertEqual(result, {"skipped": True})
        called.assert_not_called()

    @override_settings(INDEXNOW_ENABLED=True, INDEXNOW_KEY="0" * 32)
    def test_runs_command_when_enabled(self):
        with mock.patch("django.core.management.call_command") as called:
            result = submit_sitemap_indexnow()
        self.assertEqual(result, {"submitted": True})
        called.assert_called_once_with("submit_sitemap_indexnow")

    @override_settings(INDEXNOW_ENABLED=True, INDEXNOW_KEY="0" * 32)
    def test_swallows_command_errors(self):
        # A failing submit must be logged, not crash the beat worker.
        with mock.patch(
            "django.core.management.call_command", side_effect=RuntimeError("boom")
        ):
            result = submit_sitemap_indexnow()
        self.assertFalse(result["submitted"])
        self.assertIn("boom", result["error"])
