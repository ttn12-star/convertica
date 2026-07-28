"""Size-limit errors must quote the limits of the operation's own tier.

Heavy converters (pdf_to_word & co) cap free users at 15 MB, not the global
25 MB. A rejected 16.9 MB upload used to be told "Free users: max 25 MB.
Upgrade to Premium for 15 MB limit" — both numbers wrong.
"""

from unittest.mock import Mock

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from src.api.base_views import BaseConversionAPIView
from src.api.conversion_limits import (
    MAX_FILE_SIZE,
    MAX_FILE_SIZE_HEAVY,
    MAX_FILE_SIZE_HEAVY_PREMIUM,
    MAX_FILE_SIZE_PREMIUM,
    get_file_size_limits,
)

MB = 1024 * 1024


class _HeavyView(BaseConversionAPIView):
    CONVERSION_TYPE = "pdf_to_word"

    def get_serializer_class(self):
        pass

    def get_docs_decorator(self):
        pass

    def perform_conversion(self, file, context, **kwargs):
        pass


class FileSizeLimitMessageTests(TestCase):
    def test_heavy_operation_has_its_own_tier(self):
        self.assertEqual(
            get_file_size_limits("pdf_to_word"),
            (MAX_FILE_SIZE_HEAVY, MAX_FILE_SIZE_HEAVY_PREMIUM),
        )

    def test_light_operation_uses_global_tier(self):
        self.assertEqual(
            get_file_size_limits("jpg_to_pdf"), (MAX_FILE_SIZE, MAX_FILE_SIZE_PREMIUM)
        )

    def test_rejection_message_quotes_heavy_limits(self):
        request = RequestFactory().post("/api/pdf-to-word/")
        request.user = AnonymousUser()
        file = Mock(size=int(16.9 * MB), content_type="application/pdf")

        response = _HeavyView().validate_file_basic(file, {"request": request})

        self.assertEqual(response.status_code, 413)
        error = response.data["error"]
        self.assertIn("16.9 MB", error)
        self.assertIn("max 15 MB", error)
        self.assertIn("100 MB", error)
        self.assertNotIn("25 MB", error)
