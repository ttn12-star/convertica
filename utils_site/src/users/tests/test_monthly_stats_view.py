"""Regression tests for the admin Monthly Operations Statistics view.

History: per-row success_rate fell back to 0 when an op only ever had
4xx-rejected events (e.g. UNLOCK_PDF with 3 wrong passwords, COMPARE_PDF
with a single unsupported upload). The displayed "0%" was misleading
because the month/grand totals use the same formula — success / (success + error) — which excludes rejected from both numerator and denominator,
so an all-rejected row contributed 0/0 to the totals and didn't actually
drag the percentage down. The "0%" was a meaningless artefact of the
0/0 fallback. The metric is undefined for those rows and should render
as an em-dash ("—") in the template.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from src.users.models import OperationRun


class MonthlyStatsViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(
            email="stats-admin@t.test", password="x"
        )

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)
        self.url = reverse("admin:users_operationrun_monthly_stats")

    def _make(self, conv_type: str, status: str, n: int = 1) -> None:
        for _ in range(n):
            OperationRun.objects.create(conversion_type=conv_type, status=status)

    def _row(self, response, conv_type: str) -> dict:
        """Return the per-conv_type stats dict from the most recent month."""
        months = response.context["months"]
        self.assertTrue(months, "expected at least one month bucket")
        return months[0]["operations"][conv_type]

    def _totals(self, response) -> dict:
        return response.context["months"][0]["totals"]

    def _grand(self, response) -> dict:
        return response.context["grand_totals"]

    def test_all_rejected_row_has_none_success_rate(self):
        """UNLOCK_PDF with only rejected events → success_rate is None."""
        self._make("UNLOCK_PDF", "rejected", n=3)
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        row = self._row(resp, "UNLOCK_PDF")
        self.assertEqual(row["rejected"], 3)
        self.assertEqual(row["success"], 0)
        self.assertEqual(row["error"], 0)
        self.assertIsNone(
            row["success_rate"],
            "all-rejected row has no system attempts; metric must be undefined",
        )

    def test_all_rejected_row_renders_dash_in_html(self):
        """The Success Rate cell for an all-rejected row must be "—", not "0%"."""
        self._make("UNLOCK_PDF", "rejected", n=3)
        resp = self.client.get(self.url)
        html = resp.content.decode()
        self.assertIn("UNLOCK_PDF", html)
        # The dash tooltip is unique to the per-row N/A path, so its presence
        # proves the success-rate cell rendered the em-dash and not "0%".
        self.assertIn("No system attempts (success + error) recorded — only 4xx", html)
        # And the row must NOT contain a "success-rate low" 0%-with-red-color span.
        self.assertNotIn('class="success-rate', html)

    def test_error_only_row_keeps_zero_percent(self):
        """A row with a real 5xx error (no rejected) IS a 0% system failure."""
        self._make("EXTRACT_PAGES", "error", n=1)
        resp = self.client.get(self.url)
        row = self._row(resp, "EXTRACT_PAGES")
        self.assertEqual(row["error"], 1)
        self.assertEqual(row["success_rate"], 0.0)

    def test_mixed_row_keeps_numeric_rate(self):
        """Rejected events still don't dilute success_rate for a normal row."""
        self._make("pdf_to_word", "success", n=66)
        self._make("pdf_to_word", "error", n=2)
        self._make("pdf_to_word", "rejected", n=4)
        self._make("pdf_to_word", "cancelled", n=6)
        self._make("pdf_to_word", "abandoned", n=4)
        resp = self.client.get(self.url)
        row = self._row(resp, "pdf_to_word")
        # success / (success + error) = 66 / 68 = 97.06% -> 97.1
        self.assertEqual(row["success_rate"], 97.1)

    def test_month_total_unchanged_by_all_rejected_rows(self):
        """All-rejected rows must not move the month-total success_rate."""
        self._make("UNLOCK_PDF", "rejected", n=3)
        self._make("COMPARE_PDF", "rejected", n=1)
        self._make("pdf_to_word", "success", n=66)
        self._make("pdf_to_word", "error", n=2)
        resp = self.client.get(self.url)
        totals = self._totals(resp)
        # 66 / (66+2) = 97.06% -> 97.1
        self.assertEqual(totals["success_rate"], 97.1)
        # Sanity: rejected events ARE counted into totals.rejected.
        self.assertEqual(totals["rejected"], 4)

    def test_month_total_none_when_no_system_attempts(self):
        """A month consisting entirely of rejected ops → totals.success_rate is None."""
        self._make("UNLOCK_PDF", "rejected", n=3)
        self._make("COMPARE_PDF", "rejected", n=1)
        resp = self.client.get(self.url)
        totals = self._totals(resp)
        self.assertIsNone(totals["success_rate"])
        # completion_rate is success/total — 0/4 = 0.0 (defined). Not None.
        self.assertEqual(totals["completion_rate"], 0.0)

    def test_grand_totals_none_when_no_system_attempts_anywhere(self):
        self._make("UNLOCK_PDF", "rejected", n=3)
        resp = self.client.get(self.url)
        grand = self._grand(resp)
        self.assertIsNone(grand["success_rate"])
