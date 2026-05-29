"""Admin analytics date-window helper (CONVERTICA audit Perf-4).

monthly_stats / user_activity ran unbounded full-table aggregations over the
high-volume OperationRun table. Default to a recent window (12 months) so the
indexes apply and the admin page stays fast, with ?all=1 to expand.
"""

from __future__ import annotations

from datetime import timedelta

from django.test import RequestFactory, SimpleTestCase
from django.utils import timezone
from src.users.admin import analytics_window_start


class AnalyticsWindowTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_default_is_about_12_months_ago(self):
        since = analytics_window_start(self.rf.get("/admin/x/"))
        self.assertIsNotNone(since)
        delta_days = (timezone.now() - since).days
        self.assertGreater(delta_days, 300)
        self.assertLess(delta_days, 400)

    def test_all_param_returns_none_for_full_history(self):
        self.assertIsNone(analytics_window_start(self.rf.get("/admin/x/?all=1")))
