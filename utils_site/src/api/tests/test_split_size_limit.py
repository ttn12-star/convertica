from types import SimpleNamespace

from django.test import SimpleTestCase
from src.api.conversion_limits import get_file_size_limits, get_max_file_size_for_user

MB = 1024 * 1024


class SplitSizeLimitTests(SimpleTestCase):
    def test_split_keeps_free_50mb_and_premium_gets_what_is_sold(self):
        # Split checked a flat 50 MB for everyone: Premium (sold 200 MB) got 50.
        self.assertEqual(get_file_size_limits("split_pdf"), (50 * MB, 200 * MB))
        self.assertEqual(get_file_size_limits("merge_pdf"), (25 * MB, 200 * MB))
        self.assertEqual(get_file_size_limits("word_to_pdf"), (15 * MB, 200 * MB))

        anon = SimpleNamespace(is_authenticated=False)
        premium = SimpleNamespace(
            is_authenticated=True, is_premium=True, is_subscription_active=lambda: True
        )
        lapsed = SimpleNamespace(
            is_authenticated=True, is_premium=True, is_subscription_active=lambda: False
        )
        self.assertEqual(get_max_file_size_for_user(anon, "split_pdf"), 50 * MB)
        self.assertEqual(get_max_file_size_for_user(premium, "split_pdf"), 200 * MB)
        self.assertEqual(get_max_file_size_for_user(lapsed, "split_pdf"), 50 * MB)
        self.assertEqual(get_max_file_size_for_user(premium, "word_to_pdf"), 200 * MB)
        self.assertEqual(get_max_file_size_for_user(anon, "word_to_pdf"), 15 * MB)
