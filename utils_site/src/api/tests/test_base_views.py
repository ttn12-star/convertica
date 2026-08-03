"""
Unit tests for base API views.
"""

from django.test import TestCase
from rest_framework.test import APIClient
from src.api.base_views import BaseConversionAPIView


class BaseConversionAPIViewTestCase(TestCase):
    """Test cases for BaseConversionAPIView."""

    def setUp(self):
        """Set up test fixtures."""
        self.client = APIClient()

    def test_base_view_is_abstract(self):
        """Test that base view cannot be instantiated directly."""
        with self.assertRaises(TypeError):
            BaseConversionAPIView()

    def test_get_output_content_type(self):
        """Test content type detection."""

        # Create a minimal subclass
        class TestView(BaseConversionAPIView):
            def get_serializer_class(self):
                pass

            def get_docs_decorator(self):
                pass

            def perform_conversion(self, file, context, **kwargs):
                pass

        view = TestView()

        # Test various file types
        test_cases = [
            ("/path/to/file.pdf", "application/pdf"),
            (
                "/path/to/file.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            ("/path/to/file.jpg", "image/jpeg"),
            ("/path/to/file.unknown", "application/octet-stream"),
        ]

        for file_path, expected_content_type in test_cases:
            with self.subTest(file_path=file_path):
                self.assertEqual(
                    view.get_output_content_type(file_path), expected_content_type
                )


class ContentTypeVsExtensionValidationTests(TestCase):
    """Client MIME must not veto a whitelisted extension (it is derived from
    the filename anyway), but stays the gate when no extension whitelist exists."""

    @staticmethod
    def _make_view(content_types, extensions):
        class TestView(BaseConversionAPIView):
            ALLOWED_CONTENT_TYPES = content_types
            ALLOWED_EXTENSIONS = extensions
            CONVERSION_TYPE = "test"

            def get_serializer_class(self):
                pass

            def get_docs_decorator(self):
                pass

            def perform_conversion(self, file, context, **kwargs):
                pass

        return TestView()

    def _validate(self, view, name, content_type):
        from django.core.files.uploadedfile import SimpleUploadedFile

        f = SimpleUploadedFile(name, b"x" * 200, content_type=content_type)
        return view.validate_file_basic(f, {})

    def test_allowed_extension_beats_misreported_mime(self):
        view = self._make_view({"application/zip"}, {".zip"})
        resp = self._validate(view, "a.zip", "application/x-msdownload")
        self.assertIsNone(resp)

    def test_wrong_extension_rejected_with_extension_message(self):
        view = self._make_view({"application/zip"}, {".zip"})
        resp = self._validate(view, "a.exe", "application/x-msdownload")
        self.assertEqual(resp.status_code, 400)
        self.assertIn(".zip", resp.data["error"])

    def test_mime_still_rejects_when_no_extension_whitelist(self):
        view = self._make_view({"text/plain"}, set())
        resp = self._validate(view, "a.bin", "application/pdf")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("application/pdf", resp.data["error"])
