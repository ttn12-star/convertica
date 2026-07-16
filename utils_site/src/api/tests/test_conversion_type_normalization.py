"""OperationRun.conversion_type is normalized to a single UPPER label.

The same tool used to be recorded under two labels (WORD_TO_PDF vs word_to_pdf)
depending on whether its view declared CONVERSION_TYPE or fell back to the
lowercase URL view_name, fragmenting every per-tool report.
"""

from __future__ import annotations

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, TestCase
from src.api.operation_run_middleware_utils import (
    create_operation_run,
    normalize_conversion_type,
)
from src.users.models import OperationRun


class NormalizeConversionTypeTests(TestCase):
    def test_lowercase_view_name_is_uppercased(self):
        self.assertEqual(normalize_conversion_type("word_to_pdf"), "WORD_TO_PDF")

    def test_already_upper_is_unchanged(self):
        self.assertEqual(normalize_conversion_type("PDF_TO_JPG"), "PDF_TO_JPG")

    def test_dev_api_endpoints_stay_distinct_from_ui(self):
        # …_api suffix is preserved, so MERGE_PDF and MERGE_PDF_API don't collide.
        self.assertEqual(normalize_conversion_type("merge_pdf_api"), "MERGE_PDF_API")
        self.assertNotEqual(
            normalize_conversion_type("merge_pdf_api"),
            normalize_conversion_type("MERGE_PDF"),
        )

    def test_none_and_empty_are_safe(self):
        self.assertEqual(normalize_conversion_type(None), "")
        self.assertEqual(normalize_conversion_type(""), "")

    def test_truncated_to_80(self):
        self.assertEqual(len(normalize_conversion_type("x" * 200)), 80)

    def test_create_operation_run_stores_uppercase(self):
        request = RequestFactory().post("/api/word-to-pdf/")
        request.user = AnonymousUser()
        create_operation_run(
            request=request, conversion_type="word_to_pdf", status="running"
        )
        row = OperationRun.objects.get()
        self.assertEqual(row.conversion_type, "WORD_TO_PDF")
