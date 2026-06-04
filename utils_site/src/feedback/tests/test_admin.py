from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from src.feedback.models import ToolRating
from src.users.models import OperationRun


class FeedbackAdminTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            email="a@example.com", password="pw12345!"
        )
        self.client.force_login(self.admin)

    def test_changelist_loads(self):
        op = OperationRun.objects.create(
            conversion_type="pdf_to_word", status="success", task_id="t"
        )
        ToolRating.objects.create(
            tool_slug="pdf_to_word", rating=2, comment="bad", operation_run=op
        )
        resp = self.client.get(reverse("admin:feedback_toolrating_changelist"))
        self.assertEqual(resp.status_code, 200)

    def test_dashboard_loads(self):
        ToolRating.objects.create(tool_slug="rotate_pdf", rating=2, comment="x")
        resp = self.client.get(reverse("admin:feedback_quality_dashboard"))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "rotate_pdf")
