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
