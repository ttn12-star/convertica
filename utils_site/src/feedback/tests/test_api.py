from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from rest_framework.test import APIClient
from src.feedback.models import ToolRating
from src.feedback.tokens import create_feedback_token
from src.users.models import OperationRun

URL = "/api/v1/feedback/"


class FeedbackAPITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.op = OperationRun.objects.create(
            conversion_type="pdf_to_word", status="success", task_id="task-1"
        )
        self.token = create_feedback_token(task_id="task-1")

    def test_five_star_no_comment_accepted(self):
        resp = self.client.post(URL, {"feedback_token": self.token, "rating": 5})
        self.assertEqual(resp.status_code, 201)
        rating = ToolRating.objects.get()
        self.assertEqual(rating.rating, 5)
        self.assertEqual(rating.tool_slug, "pdf_to_word")
        self.assertEqual(rating.operation_run_id, self.op.id)

    def test_low_star_requires_comment(self):
        resp = self.client.post(URL, {"feedback_token": self.token, "rating": 2})
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(ToolRating.objects.exists())

    def test_low_star_with_comment_accepted(self):
        resp = self.client.post(
            URL,
            {"feedback_token": self.token, "rating": 2, "comment": "Tables broke"},
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(ToolRating.objects.get().comment, "Tables broke")

    def test_sync_slug_token_accepted_without_operation(self):
        token = create_feedback_token(tool_slug="rotate_pdf")
        resp = self.client.post(URL, {"feedback_token": token, "rating": 5})
        self.assertEqual(resp.status_code, 201)
        rating = ToolRating.objects.get()
        self.assertEqual(rating.tool_slug, "rotate_pdf")
        self.assertIsNone(rating.operation_run_id)

    def test_forged_token_silently_ignored(self):
        resp = self.client.post(URL, {"feedback_token": "forged", "rating": 5})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ToolRating.objects.exists())

    def test_non_success_operation_ignored(self):
        OperationRun.objects.create(
            conversion_type="merge_pdf", status="error", task_id="task-2"
        )
        token = create_feedback_token(task_id="task-2")
        resp = self.client.post(URL, {"feedback_token": token, "rating": 5})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(ToolRating.objects.exists())

    def test_duplicate_is_idempotent(self):
        self.client.post(URL, {"feedback_token": self.token, "rating": 5})
        resp = self.client.post(
            URL, {"feedback_token": self.token, "rating": 1, "comment": "x"}
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(ToolRating.objects.count(), 1)

    def test_authenticated_rating_is_linked_to_user(self):
        user = get_user_model().objects.create_user(
            email="rater@example.com", password="pw12345!"
        )
        api = APIClient()
        api.force_authenticate(user=user)
        resp = api.post(URL, {"feedback_token": self.token, "rating": 5})
        self.assertEqual(resp.status_code, 201)
        rating = ToolRating.objects.get()
        self.assertEqual(rating.user_id, user.id)
        self.assertEqual(rating.operation_run_id, self.op.id)
