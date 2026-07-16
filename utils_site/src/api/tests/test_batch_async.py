"""Async batch endpoint: submission gating + the Celery batch loop itself.

The generic ``<slug>/batch/async/`` route must apply the same premium gating
as the sync batch path, queue the task with the resolved view, and the task
must produce the same ZIP contract (including the failed-files manifest).
"""

from __future__ import annotations

import io
import os
import zipfile
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase
from src.users.models import User


def _jpeg(name="photo.jpg", colour=(200, 30, 30)):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), colour).save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class BatchAsyncSubmitTests(APITestCase):
    ENDPOINT = "/api/jpg-to-pdf/batch/async/"

    def setUp(self):
        # is_premium_active caches per user id; user ids repeat across test
        # classes in one process, so a stale non-premium entry from another
        # class 403s our premium user (order-dependent flake).
        from django.core.cache import cache

        cache.clear()

    def _premium_user(self):
        return User.objects.create_user(
            username="prem", email="prem@example.com", password="x", is_premium=True
        )

    def test_free_user_batch_is_rejected(self):
        response = self.client.post(
            self.ENDPOINT,
            {"image_files": [_jpeg("a.jpg"), _jpeg("b.jpg")]},
            format="multipart",
            REMOTE_ADDR="127.0.0.31",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_unknown_batch_route_404(self):
        self.client.force_authenticate(user=self._premium_user())
        response = self.client.post(
            "/api/no-such-tool/batch/async/",
            {"image_files": [_jpeg()]},
            format="multipart",
            REMOTE_ADDR="127.0.0.32",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_premium_batch_queues_task_with_resolved_view(self):
        self.client.force_authenticate(user=self._premium_user())
        with patch(
            "src.tasks.batch_conversion.batch_conversion_task.apply_async"
        ) as mock_apply:
            mock_apply.return_value = MagicMock(id="batch-task")
            response = self.client.post(
                self.ENDPOINT,
                {"image_files": [_jpeg("a.jpg"), _jpeg("b.jpg")]},
                format="multipart",
                REMOTE_ADDR="127.0.0.33",
            )

        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertTrue(response.data["task_id"])
        self.assertTrue(response.data["task_token"])

        kwargs = mock_apply.call_args.kwargs
        self.assertEqual(kwargs["queue"], "premium")
        task_kwargs = kwargs["kwargs"]
        self.assertEqual(
            task_kwargs["view_dotted"],
            "src.api.pdf_convert.jpg_to_pdf.batch_views.JPGToPDFBatchAPIView",
        )
        self.assertEqual(len(task_kwargs["input_files"]), 2)
        for entry in task_kwargs["input_files"]:
            self.assertTrue(os.path.exists(entry["path"]))


class BatchConversionTaskTests(APITestCase):
    @patch("src.tasks.batch_conversion.update_progress")
    def test_task_converts_files_and_zips_with_error_manifest(self, _mock_progress):
        from src.api.async_views import get_task_temp_dir
        from src.tasks.batch_conversion import batch_conversion_task

        task_id = "batch-test-task"
        task_dir = get_task_temp_dir(task_id)

        good = os.path.join(task_dir, "input_0")
        buf = io.BytesIO()
        Image.new("RGB", (40, 40), (10, 120, 10)).save(buf, "JPEG")
        with open(good, "wb") as f:
            f.write(buf.getvalue())
        bad = os.path.join(task_dir, "input_1")
        with open(bad, "wb") as f:
            f.write(b"not an image at all")

        result = batch_conversion_task.run(
            task_id=task_id,
            view_dotted="src.api.pdf_convert.jpg_to_pdf.batch_views.JPGToPDFBatchAPIView",
            input_files=[
                {"path": good, "name": "good.jpg"},
                {"path": bad, "name": "bad.jpg"},
            ],
            params={},
            output_zip_filename="jpg_to_pdf_convertica.zip",
        )

        self.assertEqual(result["batch_count"], 1)
        self.assertEqual(result["batch_failed_count"], 1)
        with zipfile.ZipFile(result["output_path"]) as zf:
            names = zf.namelist()
            self.assertIn("conversion_errors.txt", names)
            pdf_entries = [n for n in names if n.endswith(".pdf")]
            self.assertEqual(len(pdf_entries), 1)
            self.assertTrue(zf.read(pdf_entries[0]).startswith(b"%PDF"))
