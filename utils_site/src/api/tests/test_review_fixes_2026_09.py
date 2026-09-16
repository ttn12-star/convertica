"""One runnable check per non-trivial fix from the 2026-09 full review.

Each test is the smallest thing that fails if the corresponding fix regresses.
"""

import hashlib
import os
import tempfile
import time
from unittest import mock

from django.test import RequestFactory, TestCase, override_settings
from src.api.file_validation import is_removable_tmp_dir
from src.api.pdf_utils import parse_pages
from src.exceptions import InvalidPDFError


class RemovableTmpDirTests(TestCase):
    def test_system_temp_dir_and_root_are_never_removable(self):
        self.assertFalse(is_removable_tmp_dir(tempfile.gettempdir()))
        self.assertFalse(is_removable_tmp_dir(tempfile.gettempdir() + os.sep))
        self.assertFalse(is_removable_tmp_dir(os.sep))
        self.assertFalse(is_removable_tmp_dir(""))
        self.assertFalse(is_removable_tmp_dir(None))

    def test_per_request_dir_is_removable(self):
        d = tempfile.mkdtemp(prefix="review_")
        try:
            self.assertTrue(is_removable_tmp_dir(d))
        finally:
            os.rmdir(d)

    def test_jpg_to_pdf_optimized_returns_paths_inside_own_dir(self):
        # The sync view rmtree's dirname(input_path): a bare /tmp file here
        # used to wipe the whole container temp dir after every conversion.
        import asyncio
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        from src.api.pdf_convert.jpg_to_pdf_optimized import (
            convert_jpg_to_pdf_optimized,
        )

        buf = io.BytesIO()
        Image.new("RGB", (20, 20), (10, 20, 30)).save(buf, "JPEG")
        upload = SimpleUploadedFile("photo.jpg", buf.getvalue(), "image/jpeg")
        input_path, output_path = asyncio.run(
            convert_jpg_to_pdf_optimized(upload, suffix="_convertica", context={})
        )
        try:
            self.assertEqual(os.path.dirname(input_path), os.path.dirname(output_path))
            self.assertNotEqual(os.path.dirname(output_path), tempfile.gettempdir())
            self.assertTrue(is_removable_tmp_dir(os.path.dirname(output_path)))
        finally:
            import shutil

            shutil.rmtree(os.path.dirname(output_path), ignore_errors=True)


class ParsePagesTests(TestCase):
    def test_empty_selection_raises_instead_of_silent_noop(self):
        for bad in ("5-2", "0", "abc", "-5", "99"):
            with self.assertRaises(InvalidPDFError, msg=bad):
                parse_pages(bad, total_pages=10)

    def test_valid_selection_unchanged(self):
        self.assertEqual(parse_pages("1,3-4", 10), [0, 2, 3])
        self.assertEqual(parse_pages("all", 3), [0, 1, 2])


class WebTokenUserTests(TestCase):
    def test_web_token_request_gets_anonymous_user_not_none(self):
        from src.api.auth.web_token import WebTokenAuthentication, mint_web_token

        token = mint_web_token(scope=["*"], ip="127.0.0.1")
        request = RequestFactory().get(
            "/", HTTP_AUTHORIZATION=f"Bearer {token}", REMOTE_ADDR="127.0.0.1"
        )
        user, payload = WebTokenAuthentication().authenticate(request)
        self.assertIsNotNone(user)
        self.assertFalse(user.is_authenticated)
        self.assertEqual(payload.get("sub"), "web")


class RateLimitClientIPTests(TestCase):
    def test_ratelimit_buckets_use_trusted_client_ip(self):
        # Behind nginx REMOTE_ADDR is the proxy: every visitor shared one bucket.
        from django_ratelimit.core import _get_ip

        request = RequestFactory().get(
            "/", REMOTE_ADDR="172.18.0.5", HTTP_CF_CONNECTING_IP="203.0.113.9"
        )
        self.assertEqual(_get_ip(request), "203.0.113.9")


class CeleryTaskOptionsTests(TestCase):
    def test_generic_conversion_task_has_no_callable_queue(self):
        # A callable queue= leaked into the publish options and made every
        # self.retry() raise, leaving tasks PENDING forever.
        from src.tasks.pdf_conversion import generic_conversion_task

        self.assertFalse(callable(getattr(generic_conversion_task, "queue", None)))


class ParallelOrderTests(TestCase):
    def test_batch_results_keep_input_order(self):
        from src.api.parallel_processing import MemorySafeBatchProcessor

        def slow_for_small(n):
            time.sleep(0.05 if n < 3 else 0)
            return n * 10

        out = MemorySafeBatchProcessor(batch_size=8).process_in_batches(
            list(range(6)), slow_for_small, {}
        )
        self.assertEqual(out, [0, 10, 20, 30, 40, 50])


class CancelTaskAuthTests(TestCase):
    def test_abandon_without_token_is_rejected(self):
        from django.test import Client

        resp = Client().post(
            "/api/operation-abandon/",
            data='{"task_id": "11111111-1111-4111-8111-111111111111"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 403)


@override_settings(RATELIMIT_ENABLE=False)
class APIKeyQuotaAggregateTests(TestCase):
    def test_quota_is_summed_across_all_active_keys(self):
        from rest_framework.exceptions import AuthenticationFailed
        from src.api.auth.api_key_auth import APIKeyAuthentication
        from src.users.models import APIKey, User

        user = User.objects.create_user(email="k@t.test", password="x")
        plaintext_a = "cvk_live_aaaaaaaaaaaa" + "A" * 43
        plaintext_b = "cvk_live_bbbbbbbbbbbb" + "B" * 43
        for prefix, plaintext, used in (
            ("aaaaaaaaaaaa", plaintext_a, 60),
            ("bbbbbbbbbbbb", plaintext_b, 50),
        ):
            APIKey.objects.create(
                user=user,
                name=prefix,
                prefix=prefix,
                key_hash=hashlib.sha256(plaintext.encode()).hexdigest(),
                scope=["*"],
                usage_this_month=used,
            )
        request = RequestFactory().get(
            "/api/v1/x/", HTTP_AUTHORIZATION=f"Bearer {plaintext_a}"
        )
        with (
            mock.patch.object(User, "is_subscription_active", return_value=True),
            mock.patch.object(
                User, "api_quota_per_month", new_callable=mock.PropertyMock
            ) as quota,
        ):
            quota.return_value = 100
            # 60 + 50 >= 100: the second key must not extend the plan.
            with self.assertRaises(AuthenticationFailed):
                APIKeyAuthentication().authenticate(request)


class SpamCounterAtomicityTests(TestCase):
    def test_ip_rate_limit_blocks_the_call_over_the_limit(self):
        from django.core.cache import cache
        from src.api.spam_protection import check_rate_limit_by_ip

        cache.clear()
        request = RequestFactory().post("/api/x/", REMOTE_ADDR="198.51.100.7")
        results = [
            check_rate_limit_by_ip(request, limit=3, window=60)[0] for _ in range(4)
        ]
        self.assertEqual(results, [True, True, True, False])


class AddTextColourDefaultTests(TestCase):
    def test_whiteout_without_color_is_white_not_black(self):
        from src.api.pdf_edit.add_text.serializers import OperationItemSerializer

        base = {"page": 0, "x": 10, "y": 10, "width": 50, "height": 20}
        white = OperationItemSerializer(data={**base, "type": "whiteout"})
        self.assertTrue(white.is_valid(), white.errors)
        self.assertEqual(white.validated_data["color"], "#ffffff")
        text = OperationItemSerializer(data={**base, "type": "text", "text": "hi"})
        self.assertTrue(text.is_valid(), text.errors)
        self.assertEqual(text.validated_data["color"], "#111111")


class DailyQuotaCacheAliasTests(TestCase):
    def test_quota_counters_live_in_the_release_independent_alias(self):
        from django.conf import settings
        from src.api import daily_quota

        self.assertIn("quota", settings.CACHES)
        key = daily_quota._cache_key("ip:203.0.113.5")
        daily_quota.consume_quota_unit(key)
        from django.core.cache import caches

        self.assertEqual(int(caches["quota"].get(key)), 1)


class LogoutCrossSiteTests(TestCase):
    def test_cross_site_get_does_not_log_out(self):
        from django.urls import reverse
        from src.users.models import User

        user = User.objects.create_user(email="lo@t.test", password="x")
        self.client.force_login(user)
        self.client.get(reverse("users:logout"), HTTP_SEC_FETCH_SITE="cross-site")
        self.assertIn("_auth_user_id", self.client.session)
        self.client.get(reverse("users:logout"), HTTP_SEC_FETCH_SITE="same-origin")
        self.assertNotIn("_auth_user_id", self.client.session)
