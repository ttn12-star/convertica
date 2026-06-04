from django.db import IntegrityError
from django.test import TestCase
from src.feedback.models import ToolRating
from src.users.models import OperationRun


class ToolRatingModelTests(TestCase):
    def test_one_rating_per_operation(self):
        op = OperationRun.objects.create(
            conversion_type="pdf_to_word", status="success", request_id="req-1"
        )
        ToolRating.objects.create(tool_slug="pdf_to_word", rating=5, operation_run=op)
        with self.assertRaises(IntegrityError):
            ToolRating.objects.create(
                tool_slug="pdf_to_word", rating=1, operation_run=op
            )
