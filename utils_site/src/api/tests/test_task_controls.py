"""
Tests for task control endpoints (cancel/background) and status handling.
"""

import json
from unittest.mock import MagicMock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from src.api.cancel_task_view import is_task_background
from src.api.task_tokens import create_task_token
from src.users.models import OperationRun


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    },
    CELERY_BROKER_URL="memory://",
    CELERY_RESULT_BACKEND="cache+memory://",
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
    LOGGING={
        "version": 1,
        "disable_existing_loggers": True,
        "handlers": {"null": {"class": "logging.NullHandler"}},
        "root": {"handlers": ["null"]},
    },
)
class TaskControlTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = get_user_model().objects.create_user(
            email="owner@example.com", password="pass1234"
        )
        self.other_user = get_user_model().objects.create_user(
            email="other@example.com", password="pass1234"
        )
        self.task_id = "task-123"

        OperationRun.objects.create(
            conversion_type="pdf_to_word",
            status="queued",
            user=self.user,
            task_id=self.task_id,
        )

    @patch("src.api.cancel_task_view.celery_app.control.revoke")
    @patch("src.api.cancel_task_view.AsyncResult")
    def test_cancel_task_anonymous_requires_token(self, mock_async, _mock_revoke):
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_async.return_value = mock_result

        response = self.client.post(
            "/api/cancel-task/",
            data=json.dumps({"task_id": self.task_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    @patch("src.api.cancel_task_view.celery_app.control.revoke")
    @patch("src.api.cancel_task_view.AsyncResult")
    def test_cancel_task_anonymous_with_token(self, mock_async, _mock_revoke):
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_async.return_value = mock_result

        token = create_task_token(self.task_id, None)
        response = self.client.post(
            "/api/cancel-task/",
            data=json.dumps({"task_id": self.task_id, "task_token": token}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("src.api.cancel_task_view.celery_app.control.revoke")
    @patch("src.api.cancel_task_view.AsyncResult")
    def test_cancel_task_authenticated_owner_without_token(
        self, mock_async, _mock_revoke
    ):
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_async.return_value = mock_result

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/cancel-task/",
            data=json.dumps({"task_id": self.task_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)

    @patch("src.api.cancel_task_view.celery_app.control.revoke")
    @patch("src.api.cancel_task_view.AsyncResult")
    def test_cancel_task_authenticated_wrong_user(self, mock_async, _mock_revoke):
        mock_result = MagicMock()
        mock_result.state = "PENDING"
        mock_async.return_value = mock_result

        self.client.force_login(self.other_user)
        response = self.client.post(
            "/api/cancel-task/",
            data=json.dumps({"task_id": self.task_id}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_mark_task_background_requires_premium(self):
        token = create_task_token(self.task_id, self.user.id)

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/task-background/",
            data=json.dumps({"task_id": self.task_id, "task_token": token}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_mark_task_background_premium_success(self):
        # Make user premium and active
        self.user.is_premium = True
        self.user.subscription_end_date = timezone.now() + timezone.timedelta(days=1)
        self.user.save(update_fields=["is_premium", "subscription_end_date"])

        token = create_task_token(self.task_id, self.user.id)

        self.client.force_login(self.user)
        response = self.client.post(
            "/api/task-background/",
            data=json.dumps({"task_id": self.task_id, "task_token": token}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(is_task_background(self.task_id))


@override_settings(
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }
)
class TaskStatusIgnoredTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    @patch("src.api.async_views.AsyncResult")
    def test_task_status_ignored_treated_as_cancelled(self, mock_async):
        mock_result = MagicMock()
        mock_result.status = "IGNORED"
        mock_result.info = {}
        mock_result.result = {}
        mock_async.return_value = mock_result

        response = self.client.get("/api/tasks/test-id/status/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data.get("status"), "REVOKED")
        self.assertTrue(response.data.get("cancelled"))
