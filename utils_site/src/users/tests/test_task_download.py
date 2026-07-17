"""Human download page for emailed result links."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.urls import reverse
from src.users.models import OperationRun, User


class TaskDownloadPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="dl", email="dl@example.com", password="x", is_premium=True
        )
        self.url = reverse("users:task_download", args=["task-dl-1"])

    def test_anonymous_redirects_to_login(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)
        self.assertIn("next=", response.url)

    def test_foreign_task_shows_expired_not_leak(self):
        other = User.objects.create_user(
            username="other-dl", email="other-dl@example.com", password="x"
        )
        OperationRun.objects.create(
            conversion_type="PDF_TO_WORD",
            status="success",
            user=other,
            task_id="task-dl-1",
        )
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no longer available")

    def test_owner_with_live_result_gets_download_button(self):
        OperationRun.objects.create(
            conversion_type="PDF_TO_WORD",
            status="success",
            user=self.user,
            task_id="task-dl-1",
        )
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as fh:
            fh.write(b"result")
            path = fh.name
        try:
            fake = MagicMock()
            fake.status = "SUCCESS"
            fake.result = {
                "status": "success",
                "output_path": path,
                "output_filename": "report_convertica.docx",
            }
            self.client.force_login(self.user)
            with patch("celery.result.AsyncResult", return_value=fake):
                response = self.client.get(self.url)
        finally:
            os.unlink(path)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/api/tasks/task-dl-1/result/")
        self.assertContains(response, "report_convertica.docx")

    def test_owner_with_gone_result_gets_expired_screen(self):
        OperationRun.objects.create(
            conversion_type="PDF_TO_WORD",
            status="success",
            user=self.user,
            task_id="task-dl-1",
        )
        fake = MagicMock()
        fake.status = "SUCCESS"
        fake.result = {
            "status": "success",
            "output_path": "/nonexistent/gone.docx",
            "output_filename": "gone.docx",
        }
        self.client.force_login(self.user)
        with patch("celery.result.AsyncResult", return_value=fake):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no longer available")

    def test_downloaded_and_forgotten_result_reads_expired_not_processing(self):
        """After browser download the Celery result is forgotten (PENDING) —
        the page must show expired, not an eternal 'still processing'."""
        OperationRun.objects.create(
            conversion_type="PDF_TO_WORD",
            status="success",
            user=self.user,
            task_id="task-dl-1",
        )
        fake = MagicMock()
        fake.status = "PENDING"
        fake.result = None
        self.client.force_login(self.user)
        with patch("celery.result.AsyncResult", return_value=fake):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no longer available")

    def test_owner_with_pending_result_sees_processing(self):
        OperationRun.objects.create(
            conversion_type="PDF_TO_WORD",
            status="queued",
            user=self.user,
            task_id="task-dl-1",
        )
        fake = MagicMock()
        fake.status = "PENDING"
        self.client.force_login(self.user)
        with patch("celery.result.AsyncResult", return_value=fake):
            response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Still processing")
