"""Opt-in "email me the result" plumbing.

The premium flag must thread notify_user_id/notify_lang into the Celery
kwargs on both the single-file async path and the batch path, must be
ignored for non-premium users, and the email task itself must attach small
files / fall back to a download link for big ones.
"""

from __future__ import annotations

import io
import os
import tempfile
from unittest.mock import MagicMock, patch

from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image
from pypdf import PdfWriter
from rest_framework import status
from rest_framework.test import APITestCase
from src.users.models import User


def _pdf(name="doc.pdf"):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="application/pdf")


def _jpeg(name="photo.jpg"):
    buf = io.BytesIO()
    Image.new("RGB", (40, 40), (200, 30, 30)).save(buf, "JPEG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class EmailResultFlagTests(APITestCase):
    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def _user(self, premium: bool):
        return User.objects.create_user(
            username="prem" if premium else "free",
            email=f"{'prem' if premium else 'free'}@example.com",
            password="x",
            is_premium=premium,
        )

    def test_premium_async_submit_threads_notify_kwargs(self):
        self.client.force_authenticate(user=self._user(premium=True))
        with patch(
            "src.tasks.pdf_conversion.generic_conversion_task.apply_async"
        ) as mock_apply:
            mock_apply.return_value = MagicMock(id="t1")
            response = self.client.post(
                "/api/pdf-to-word/async/",
                {"pdf_file": _pdf(), "email_result": "true"},
                format="multipart",
                REMOTE_ADDR="127.0.0.41",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task_kwargs = mock_apply.call_args.kwargs["kwargs"]
        self.assertEqual(
            task_kwargs["notify_user_id"],
            User.objects.get(email="prem@example.com").id,
        )
        self.assertIn("notify_lang", task_kwargs)

    def test_registered_non_premium_flag_is_ignored(self):
        self.client.force_authenticate(user=self._user(premium=False))
        with patch(
            "src.tasks.pdf_conversion.generic_conversion_task.apply_async"
        ) as mock_apply:
            mock_apply.return_value = MagicMock(id="t2")
            response = self.client.post(
                "/api/pdf-to-word/async/",
                {"pdf_file": _pdf(), "email_result": "true"},
                format="multipart",
                REMOTE_ADDR="127.0.0.42",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task_kwargs = mock_apply.call_args.kwargs["kwargs"]
        self.assertNotIn("notify_user_id", task_kwargs)

    def test_premium_async_without_flag_has_no_notify(self):
        self.client.force_authenticate(user=self._user(premium=True))
        with patch(
            "src.tasks.pdf_conversion.generic_conversion_task.apply_async"
        ) as mock_apply:
            mock_apply.return_value = MagicMock(id="t3")
            response = self.client.post(
                "/api/pdf-to-word/async/",
                {"pdf_file": _pdf()},
                format="multipart",
                REMOTE_ADDR="127.0.0.43",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertNotIn("notify_user_id", mock_apply.call_args.kwargs["kwargs"])

    def test_batch_submit_threads_notify_kwargs(self):
        self.client.force_authenticate(user=self._user(premium=True))
        with patch(
            "src.tasks.batch_conversion.batch_conversion_task.apply_async"
        ) as mock_apply:
            mock_apply.return_value = MagicMock(id="b1")
            response = self.client.post(
                "/api/jpg-to-pdf/batch/async/",
                {
                    "image_files": [_jpeg("a.jpg"), _jpeg("b.jpg")],
                    "email_result": "true",
                },
                format="multipart",
                REMOTE_ADDR="127.0.0.44",
            )
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        task_kwargs = mock_apply.call_args.kwargs["kwargs"]
        self.assertIn("notify_user_id", task_kwargs)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    SITE_URL="https://convertica.net",
)
class SendConversionResultTaskTests(APITestCase):
    def _user(self):
        return User.objects.create_user(
            username="mailme",
            email="mailme@example.com",
            password="x",
            is_premium=True,
        )

    def _run(self, user, output_path, lang=""):
        from src.tasks.email import send_conversion_result

        send_conversion_result.apply(
            kwargs={
                "user_id": user.id,
                "task_id": "task-xyz",
                "output_path": output_path,
                "output_filename": os.path.basename(output_path),
                "lang": lang,
            }
        )

    def test_small_file_is_attached(self):
        user = self._user()
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as fh:
            fh.write(b"tiny result")
            path = fh.name
        try:
            self._run(user, path)
        finally:
            os.unlink(path)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.to, [user.email])
        self.assertEqual(len(msg.attachments), 1)
        self.assertIn(os.path.basename(path), msg.subject)
        self.assertIn("/api/tasks/task-xyz/result/", msg.body)

    @override_settings(EMAIL_RESULT_MAX_ATTACHMENT_MB=0)
    def test_big_file_falls_back_to_link(self):
        user = self._user()
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as fh:
            fh.write(b"too big for a zero-MB cap")
            path = fh.name
        try:
            self._run(user, path)
        finally:
            os.unlink(path)

        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertEqual(msg.attachments, [])
        self.assertIn("/api/tasks/task-xyz/result/", msg.body)

    def test_missing_file_still_sends_link_email(self):
        user = self._user()
        self._run(user, "/nonexistent/gone.docx")
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].attachments, [])

    def test_localized_template_used(self):
        user = self._user()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
            fh.write(b"x")
            path = fh.name
        try:
            self._run(user, path, lang="ru")
        finally:
            os.unlink(path)

        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("готов", mail.outbox[0].subject)
