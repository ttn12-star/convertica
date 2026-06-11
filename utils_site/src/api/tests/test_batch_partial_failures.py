"""Batch endpoints must surface per-file conversion failures.

Historically a file that blew up in convert_single was only logged: the
user got a smaller ZIP with no signal that anything was dropped. The
frontend (converter.js) already reads X-Convertica-Batch-Failed-Count to
warn the user — these tests pin the server side of that contract, plus a
conversion_errors.txt manifest inside the ZIP naming the dropped files.
"""

from __future__ import annotations

import io
import os
import tempfile
import zipfile
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from src.exceptions import ConversionError
from src.users.models import SubscriptionPlan, User


def _fake_pdf(name: str) -> SimpleUploadedFile:
    body = b"%PDF-1.4\n" + b"x" * 200 + b"\n%%EOF"
    return SimpleUploadedFile(name, body, content_type="application/pdf")


def _fake_convert_single(self, uploaded_file, context, **params):
    """Succeed for every file except bad.pdf, like a corrupt upload would."""
    if uploaded_file.name == "bad.pdf":
        raise ConversionError("simulated corrupt input")
    out_dir = tempfile.mkdtemp(prefix="batch_test_out_")
    out_path = os.path.join(out_dir, f"out_{uploaded_file.name}")
    with open(out_path, "wb") as f:
        f.write(b"%PDF-1.4 converted")
    return out_dir, out_path


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
    MAX_BATCH_FILES_FREE=1,
    MAX_BATCH_FILES_PREMIUM=10,
)
class BatchPartialFailureTests(TestCase):
    BATCH_URL = "/api/pdf-edit/crop/batch/"

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(email="batch@t.test", password="passw0rd!")
        plan = SubscriptionPlan.objects.create(
            name="Monthly Hero",
            slug="monthly-hero",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
            ls_variant_id="1599021",
        )
        now = timezone.now()
        self.user.activate_premium(
            plan=plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_test",
            provider_customer_id="cust_test",
        )
        self.client.force_login(self.user)

    def _post_batch(self, names: list[str]):
        crop_params = {
            "x": "0",
            "y": "0",
            "width": "100",
            "height": "100",
            "pages": "all",
        }
        return self.client.post(
            self.BATCH_URL,
            data={"pdf_files": [_fake_pdf(n) for n in names], **crop_params},
            format="multipart",
        )

    @patch(
        "src.api.pdf_edit.crop_pdf.batch_views.CropPDFBatchAPIView.convert_single",
        _fake_convert_single,
    )
    def test_partial_failure_reports_count_and_manifest(self):
        response = self._post_batch(["a.pdf", "bad.pdf", "c.pdf"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Convertica-Batch-Count"], "2")
        self.assertEqual(response["X-Convertica-Batch-Failed-Count"], "1")

        body = b"".join(response.streaming_content)
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            names = set(zf.namelist())
            self.assertIn("conversion_errors.txt", names)
            manifest = zf.read("conversion_errors.txt").decode("utf-8")
        self.assertIn("bad.pdf", manifest)

    @patch(
        "src.api.pdf_edit.crop_pdf.batch_views.CropPDFBatchAPIView.convert_single",
        _fake_convert_single,
    )
    def test_full_success_has_zero_failed_count_and_no_manifest(self):
        response = self._post_batch(["a.pdf", "c.pdf"])

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Convertica-Batch-Failed-Count"], "0")

        body = b"".join(response.streaming_content)
        with zipfile.ZipFile(io.BytesIO(body)) as zf:
            self.assertNotIn("conversion_errors.txt", zf.namelist())

    @patch(
        "src.api.pdf_edit.crop_pdf.batch_views.CropPDFBatchAPIView.convert_single",
        _fake_convert_single,
    )
    def test_all_failed_returns_error_with_file_names(self):
        response = self._post_batch(["bad.pdf"])

        self.assertEqual(response.status_code, 500)
        payload = response.json()
        self.assertIn("error", payload)
        self.assertEqual(payload.get("failed_files"), ["bad.pdf"])
