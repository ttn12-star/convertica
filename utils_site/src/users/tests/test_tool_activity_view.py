"""Tool Activity admin view: per-tool op counts filterable by ?min_ops."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from src.users.models import OperationRun


class ToolActivityViewTests(TestCase):
    def setUp(self):
        admin = get_user_model().objects.create_superuser(
            email="admin@example.com", password="pw"
        )
        self.client.force_login(admin)
        for _ in range(5):
            OperationRun.objects.create(conversion_type="PDF_TO_WORD", status="success")
        OperationRun.objects.create(conversion_type="RARE_TOOL", status="success")
        self.url = reverse("admin:users_operationrun_tool_activity")

    def test_lists_all_tools_without_filter(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "PDF_TO_WORD")
        self.assertContains(resp, "RARE_TOOL")

    def test_min_ops_hides_tools_below_threshold(self):
        resp = self.client.get(self.url, {"min_ops": 2})
        self.assertContains(resp, "PDF_TO_WORD")  # 5 ops -> shown
        self.assertNotContains(resp, "RARE_TOOL")  # 1 op -> hidden
