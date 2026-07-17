"""Premium permission toggles on Protect PDF (AES-256 + permissions_flag)."""

from __future__ import annotations

import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from pypdf import PdfReader, PdfWriter
from pypdf.constants import UserAccessPermissions
from rest_framework import status
from rest_framework.test import APITestCase
from src.api.pdf_security.protect_pdf.utils import permissions_flag, protect_pdf
from src.users.models import User


def _pdf(name="doc.pdf"):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buf = io.BytesIO()
    writer.write(buf)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="application/pdf")


class PermissionsFlagTests(APITestCase):
    def test_default_allows_everything(self):
        self.assertEqual(permissions_flag(), UserAccessPermissions.all())

    def test_restrictions_clear_the_right_bits(self):
        perms = permissions_flag(
            restrict_printing=True,
            restrict_copying=True,
            restrict_modifying=True,
        )
        self.assertFalse(perms & UserAccessPermissions.PRINT)
        self.assertFalse(perms & UserAccessPermissions.PRINT_TO_REPRESENTATION)
        self.assertFalse(perms & UserAccessPermissions.EXTRACT)
        self.assertFalse(perms & UserAccessPermissions.MODIFY)
        self.assertFalse(perms & UserAccessPermissions.ASSEMBLE_DOC)
        # Accessibility extraction must survive a copy restriction.
        self.assertTrue(perms & UserAccessPermissions.EXTRACT_TEXT_AND_GRAPHICS)

    def test_protect_pdf_applies_permissions(self):
        _input, output_path = protect_pdf(
            _pdf(),
            password="s3cret",
            restrict_printing=True,
        )
        reader = PdfReader(output_path)
        self.assertTrue(reader.is_encrypted)
        reader.decrypt("s3cret")
        perms = reader.user_access_permissions
        self.assertFalse(perms & UserAccessPermissions.PRINT)
        self.assertTrue(perms & UserAccessPermissions.EXTRACT)


@override_settings(
    CACHES={"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}},
    RATELIMIT_ENABLE=False,
)
class ProtectPermissionGateTests(APITestCase):
    ENDPOINT = "/api/pdf-security/protect/"

    def setUp(self):
        from django.core.cache import cache

        cache.clear()

    def test_anonymous_restriction_request_is_rejected(self):
        response = self.client.post(
            self.ENDPOINT,
            {"pdf_file": _pdf(), "password": "x", "restrict_printing": "true"},
            format="multipart",
            REMOTE_ADDR="127.0.0.51",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Premium", str(response.data))

    def test_free_user_restriction_request_is_rejected(self):
        user = User.objects.create_user(
            username="freeprot", email="freeprot@example.com", password="x"
        )
        self.client.force_authenticate(user=user)
        response = self.client.post(
            self.ENDPOINT,
            {"pdf_file": _pdf(), "password": "x", "restrict_copying": "true"},
            format="multipart",
            REMOTE_ADDR="127.0.0.52",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
