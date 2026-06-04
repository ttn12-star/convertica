"""End-to-end premium gating tests.

Verifies that premium-only features (batch processing) are correctly:
- BLOCKED for authenticated free users (premium gate, 403).
- UNBLOCKED for users whose premium was activated via the LS webhook flow.
- Re-blocked when subscription expires.

These tests exercise the real view stack (URL → middleware → view → premium_utils),
not just unit-level logic.

Note: anonymous users hit DRF's IsAuthenticated layer first and get 403 with a
generic auth error — that's tested separately as an auth concern, not a premium one.
"""

from __future__ import annotations

import hashlib
import hmac
import io
import json
from datetime import timedelta
from decimal import Decimal

from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from src.payments.tests.fixtures.ls_payloads import (
    order_created_payload,
    subscription_created_payload,
)
from src.users.models import SubscriptionPlan, User, UserSubscription


def _fake_pdf(name: str = "x.pdf") -> SimpleUploadedFile:
    """Cheap fake PDF — header bytes only, enough to pass MIME sniff."""
    return SimpleUploadedFile(
        name,
        b"%PDF-1.4\n%minimal\n",
        content_type="application/pdf",
    )


def _real_pdf(pages: int = 3, name: str = "multi.pdf") -> SimpleUploadedFile:
    """A genuinely parseable multi-page PDF, so page-count validation runs.

    The cheap `_fake_pdf` is unparseable, which makes `validate_pdf_pages`
    bail out as "can't read, allow" — useless for asserting the page cap.
    """
    from pypdf import PdfWriter

    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="application/pdf")


WEBHOOK_SECRET = "premium-gating-test-secret-32chars-or-more"


def _signed_webhook_post(client: Client, payload: dict) -> TestCase.client.response:
    body = json.dumps(payload).encode()
    sig = hmac.new(WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
    return client.post(
        "/payments/webhook/lemonsqueezy/",
        data=body,
        content_type="application/json",
        HTTP_X_SIGNATURE=sig,
        HTTP_X_EVENT_NAME=payload["meta"]["event_name"],
    )


@override_settings(
    PAYMENTS_ENABLED=True,
    LEMONSQUEEZY_WEBHOOK_SECRET=WEBHOOK_SECRET,
    MAX_BATCH_FILES_FREE=1,
    MAX_BATCH_FILES_PREMIUM=10,
    # Otherwise the global 10/h IP rate-limit tally accumulates across the six
    # test methods in this class and the later cases get short-circuited at the
    # rate-limit layer before reaching the premium gate, surfacing as
    # `assertIn("Upgrade to Premium", body["error"])` failures.
    RATELIMIT_ENABLE=False,
)
class PremiumGatingViaCropBatchTests(TestCase):
    """Premium gating exercised through the crop-pdf batch endpoint.

    The batch endpoint runs `can_use_batch_processing(user, len(files))`
    BEFORE any PDF parsing, so we can verify the gate without supplying
    valid PDFs — a 403 with the "Free users can only process 1 file..."
    message is the success criterion.
    """

    BATCH_URL = "/api/pdf-edit/crop/batch/"

    def setUp(self):
        # Redis cache survives across TestCase runs; flush stale
        # `user_premium_active:{pk}` keys from prior tests.
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(email="gate@t.test", password="passw0rd!")
        # Belt-and-suspenders: ensure user is genuinely free before each test.
        self.assertFalse(self.user.is_premium)
        self.monthly = SubscriptionPlan.objects.create(
            name="Monthly Hero",
            slug="monthly-hero",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
            ls_variant_id="1599021",
        )
        self.lifetime = SubscriptionPlan.objects.create(
            name="Lifetime Hero",
            slug="lifetime-hero",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            ls_variant_id="1599032",
        )

    def _post_batch(self, file_count: int):
        files = [_fake_pdf(f"f{i}.pdf") for i in range(file_count)]
        return self.client.post(
            self.BATCH_URL,
            data={
                "pdf_files": files,
                "x": "0",
                "y": "0",
                "width": "100",
                "height": "100",
                "pages": "all",
            },
            format="multipart",
        )

    def test_anonymous_user_blocked_by_auth_layer(self):
        """Anon hits DRF IsAuthenticated and gets 403 before premium gate.

        This tests the auth boundary, not the premium gate. The error body
        comes from DRF, not from `can_use_batch_processing`.
        """
        response = self._post_batch(file_count=5)
        self.assertEqual(response.status_code, 403)

    def test_authenticated_free_user_blocked_on_5_files(self):
        """Authenticated user without premium = same as free."""
        self.client.force_login(self.user)
        response = self._post_batch(file_count=5)
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertIn("Upgrade to Premium", body.get("error", ""))

    def test_subscription_webhook_unblocks_batch_for_user(self):
        """End-to-end: webhook activates premium → batch endpoint stops blocking."""
        self.client.force_login(self.user)

        # 1. Confirm currently blocked
        response = self._post_batch(file_count=5)
        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)

        # 2. Send signed `subscription_created` webhook
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
        )
        webhook_response = _signed_webhook_post(self.client, payload)
        self.assertEqual(webhook_response.status_code, 200)

        # 3. Verify premium activated in DB
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertTrue(self.user.is_subscription_active())
        self.assertTrue(
            UserSubscription.objects.filter(user=self.user, status="active").exists()
        )

        # 4. Repeat batch — should NOT be 403 now
        # Re-create client with same session to refresh request.user state
        self.client.force_login(self.user)
        response = self._post_batch(file_count=5)
        self.assertNotEqual(
            response.status_code,
            403,
            f"Premium user still blocked: {response.content[:300]}",
        )

    def test_lifetime_order_webhook_grants_unlimited_premium(self):
        """Lifetime: order_created → user.is_premium=True, end_date=None,
        is_subscription_active() returns True forever."""
        self.client.force_login(self.user)

        payload = order_created_payload(
            user_id=self.user.id,
            plan_id=self.lifetime.id,
        )
        webhook_response = _signed_webhook_post(self.client, payload)
        self.assertEqual(webhook_response.status_code, 200)

        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNone(self.user.subscription_end_date)
        self.assertTrue(self.user.is_subscription_active())

        # Batch unblocked
        self.client.force_login(self.user)
        response = self._post_batch(file_count=5)
        self.assertNotEqual(response.status_code, 403)

    def test_premium_at_max_batch_size_passes_gate(self):
        """Premium user with exactly 10 files (the cap) — gate passes."""
        # Activate premium directly (skip the webhook step).
        now = timezone.now()
        self.user.activate_premium(
            plan=self.monthly,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_test",
            provider_customer_id="cust_test",
        )
        self.client.force_login(self.user)

        response = self._post_batch(file_count=10)
        # 10 files is at MAX_BATCH_FILES_PREMIUM=10 — premium gate passes.
        # Downstream may 400/500 due to fake PDFs; we only verify gate.
        self.assertNotEqual(response.status_code, 403)

    def test_premium_above_max_batch_size_blocked(self):
        """Premium user with 11 files — exceeds 10-file cap, still 403."""
        now = timezone.now()
        self.user.activate_premium(
            plan=self.monthly,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_test",
            provider_customer_id="cust_test",
        )
        self.client.force_login(self.user)

        response = self._post_batch(file_count=11)
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertIn("Maximum 10 files allowed", body.get("error", ""))

    def test_expired_subscription_blocks_batch(self):
        """Premium that expired (end_date in past) — gate blocks again."""
        # Activate, then artificially expire.
        now = timezone.now()
        self.user.activate_premium(
            plan=self.monthly,
            period_start=now - timedelta(days=40),
            period_end=now - timedelta(days=10),  # expired
            provider="lemonsqueezy",
            provider_subscription_id="sub_test",
            provider_customer_id="cust_test",
        )
        # Confirm is_subscription_active() returns False with expired date
        self.assertFalse(self.user.is_subscription_active())

        self.client.force_login(self.user)
        response = self._post_batch(file_count=5)
        self.assertEqual(response.status_code, 403)


@override_settings(PAYMENTS_ENABLED=True)
class PremiumFeaturesDictTests(TestCase):
    """Verify get_premium_features() returns correct flags per user state."""

    def setUp(self):
        cache.clear()  # purge stale user_premium_active:{pk} keys
        self.user = User.objects.create_user(email="f@t.test", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="M",
            slug="m",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def test_anonymous_returns_free_features(self):
        from django.contrib.auth.models import AnonymousUser
        from src.api.premium_utils import get_premium_features

        features = get_premium_features(AnonymousUser())
        self.assertFalse(features["is_premium"])
        self.assertFalse(features["api_access"])
        self.assertFalse(features["priority_queue"])

    def test_authenticated_free_returns_free_features(self):
        from src.api.premium_utils import get_premium_features

        features = get_premium_features(self.user)
        self.assertFalse(features["is_premium"])

    def test_premium_user_returns_premium_features(self):
        from src.api.premium_utils import get_premium_features

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_x",
            provider_customer_id="cust_x",
        )
        features = get_premium_features(self.user)
        self.assertTrue(features["is_premium"])
        self.assertTrue(features["priority_queue"])
        self.assertTrue(features["api_access"])
        self.assertTrue(features["no_ads"])


# ---------------------------------------------------------------------------
# A1. File size limit
# ---------------------------------------------------------------------------


@override_settings(PAYMENTS_ENABLED=True)
class FileSizeLimitTests(TestCase):
    """Verify get_max_file_size_for_user returns correct limit per user state.

    Covers premium gate #2 (file size cap) — the limit drives both the
    Nginx-level `client_max_body_size` selection and the in-Django
    validate_file_for_operation check in base_views.
    """

    def setUp(self):
        cache.clear()  # purge stale user_premium_active:{pk} keys
        self.user = User.objects.create_user(email="size@t.test", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Size",
            slug="monthly-size",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def test_anonymous_user_gets_free_limit(self):
        from django.contrib.auth.models import AnonymousUser
        from src.api.conversion_limits import MAX_FILE_SIZE, get_max_file_size_for_user

        self.assertEqual(get_max_file_size_for_user(AnonymousUser()), MAX_FILE_SIZE)

    def test_authenticated_free_user_gets_free_limit(self):
        from src.api.conversion_limits import MAX_FILE_SIZE, get_max_file_size_for_user

        self.assertEqual(get_max_file_size_for_user(self.user), MAX_FILE_SIZE)

    def test_premium_user_gets_premium_limit(self):
        from src.api.conversion_limits import (
            MAX_FILE_SIZE_PREMIUM,
            get_max_file_size_for_user,
        )

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_size",
            provider_customer_id="cust_size",
        )
        self.assertEqual(get_max_file_size_for_user(self.user), MAX_FILE_SIZE_PREMIUM)

    def test_premium_user_with_heavy_operation_gets_heavy_premium_limit(self):
        # `compress_pdf` is NOT in HEAVY_OPERATIONS (compress is a simple op),
        # so we use `pdf_to_word` which IS heavy.
        from src.api.conversion_limits import (
            HEAVY_OPERATIONS,
            MAX_FILE_SIZE_HEAVY_PREMIUM,
            get_max_file_size_for_user,
        )

        # Sanity: verify our chosen op is actually heavy.
        self.assertIn("pdf_to_word", HEAVY_OPERATIONS)

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_heavy",
            provider_customer_id="cust_heavy",
        )
        self.assertEqual(
            get_max_file_size_for_user(self.user, operation="pdf_to_word"),
            MAX_FILE_SIZE_HEAVY_PREMIUM,
        )

    def test_expired_premium_falls_back_to_free_limit(self):
        from src.api.conversion_limits import MAX_FILE_SIZE, get_max_file_size_for_user

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now - timedelta(days=40),
            period_end=now - timedelta(days=10),  # expired
            provider="lemonsqueezy",
            provider_subscription_id="sub_exp",
            provider_customer_id="cust_exp",
        )
        self.assertFalse(self.user.is_subscription_active())
        self.assertEqual(get_max_file_size_for_user(self.user), MAX_FILE_SIZE)


# ---------------------------------------------------------------------------
# A2. Page-count limit
# ---------------------------------------------------------------------------


@override_settings(PAYMENTS_ENABLED=True)
class PageCountLimitTests(TestCase):
    """Verify get_max_pages_for_user returns correct page cap per user state.

    Covers premium gate #3 (PDF page count). Per-operation overrides come
    from `settings.PREMIUM_PAGE_LIMITS`.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="pages@t.test", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Pages",
            slug="monthly-pages",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def test_anonymous_user_gets_free_pages(self):
        from django.contrib.auth.models import AnonymousUser
        from src.api.conversion_limits import MAX_PDF_PAGES, get_max_pages_for_user

        self.assertEqual(get_max_pages_for_user(AnonymousUser()), MAX_PDF_PAGES)

    def test_authenticated_free_user_gets_free_pages(self):
        from src.api.conversion_limits import MAX_PDF_PAGES, get_max_pages_for_user

        self.assertEqual(get_max_pages_for_user(self.user), MAX_PDF_PAGES)

    def test_premium_user_gets_premium_pages(self):
        from src.api.conversion_limits import (
            MAX_PDF_PAGES_PREMIUM,
            get_max_pages_for_user,
        )

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_pages",
            provider_customer_id="cust_pages",
        )
        self.assertEqual(get_max_pages_for_user(self.user), MAX_PDF_PAGES_PREMIUM)

    @override_settings(PREMIUM_PAGE_LIMITS={"pdf_to_word": 500})
    def test_premium_user_per_operation_override_wins(self):
        from src.api.conversion_limits import get_max_pages_for_user

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_override",
            provider_customer_id="cust_override",
        )
        # Override returns the configured value directly, NOT the global premium cap.
        self.assertEqual(
            get_max_pages_for_user(self.user, operation="pdf_to_word"),
            500,
        )


# ---------------------------------------------------------------------------
# A3. OCR gate
# ---------------------------------------------------------------------------


@override_settings(PAYMENTS_ENABLED=True, RATELIMIT_ENABLE=False)
class OCRGateTests(TestCase):
    """Verify the OCR-only-for-premium gate at /api/pdf-to-word/.

    The gate lives in `BaseConversionAPIView.post` and short-circuits with
    HTTP 403 + 'OCR is a premium feature' before any PDF parsing if the
    request includes `ocr_enabled=true` and the user isn't premium.

    We send a minimal fake PDF — premium path will fail later (real OCR
    needs a real PDF) but the gate runs *before* validation, so all we
    assert for premium is "not 403 with the OCR message".
    """

    OCR_URL = "/api/pdf-to-word/"

    def setUp(self):
        cache.clear()
        self.client = Client()
        self.user = User.objects.create_user(email="ocr@t.test", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly OCR",
            slug="monthly-ocr",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def _post_ocr(self) -> Client.response_class:
        # Browser-shaped Referer to satisfy the CAPTCHA origin gate
        # (CaptchaRequirementMiddleware flips captcha_required when the request
        # arrives without a convertica.net Referer or Origin).
        return self.client.post(
            self.OCR_URL,
            data={
                "pdf_file": _fake_pdf("ocr.pdf"),
                "ocr_enabled": "true",
            },
            format="multipart",
            HTTP_REFERER="https://convertica.net/",
        )

    def test_anonymous_user_blocked_with_ocr_message_or_auth(self):
        """Anon: either OCR gate (403 + OCR message) or DRF auth layer (403).

        Both outcomes mean OCR is correctly denied for unauthenticated users.
        """
        response = self._post_ocr()
        self.assertEqual(response.status_code, 403)

    def test_free_user_blocked_with_ocr_premium_message(self):
        self.client.force_login(self.user)
        response = self._post_ocr()
        self.assertEqual(response.status_code, 403)
        body = response.json()
        self.assertIn("OCR is a premium feature", body.get("error", ""))

    def test_premium_user_passes_ocr_gate(self):
        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_ocr",
            provider_customer_id="cust_ocr",
        )
        self.client.force_login(self.user)
        response = self._post_ocr()
        # Gate passed — downstream may 400/500 because the fake PDF can't be
        # OCRd, but it must NOT be a 403 with the OCR-premium message.
        if response.status_code == 403:
            body = response.json()
            self.assertNotIn(
                "OCR is a premium feature",
                body.get("error", ""),
                f"Premium user incorrectly blocked by OCR gate: {body}",
            )

    # ---- Async path OCR gate parity --------------------------------------

    ASYNC_OCR_URL = "/api/pdf-to-word/async/"

    def _post_async_ocr(self):
        return self.client.post(
            self.ASYNC_OCR_URL,
            data={"pdf_file": _fake_pdf("ocr.pdf"), "ocr_enabled": "true"},
            format="multipart",
            HTTP_REFERER="https://convertica.net/",
        )

    def test_free_user_blocked_with_ocr_premium_message_async(self):
        """OCR via the async endpoint must be premium-gated too (403)."""
        self.client.force_login(self.user)
        response = self._post_async_ocr()
        self.assertEqual(response.status_code, 403)
        self.assertIn("OCR is a premium feature", response.json().get("error", ""))

    def test_premium_user_passes_ocr_gate_async(self):
        """Premium user must NOT be blocked by the async OCR gate."""
        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_ocr_async",
            provider_customer_id="cust_ocr_async",
        )
        self.client.force_login(self.user)
        response = self._post_async_ocr()
        # Gate passed — fake PDF may fail downstream, but must not be the
        # OCR-premium 403.
        if response.status_code == 403:
            self.assertNotIn(
                "OCR is a premium feature", response.json().get("error", "")
            )

    def test_is_premium_active_unit_for_ocr_decision(self):
        """Direct unit test of the helper that drives the OCR gate.

        If the view-level integration above ever changes URL/serializer
        shape, this unit test still encodes the contract: free users
        return False, premium users return True.
        """
        from src.api.premium_utils import is_premium_active

        # Free user.
        self.assertFalse(is_premium_active(self.user))

        # Activate premium.
        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_unit",
            provider_customer_id="cust_unit",
        )
        # Cache is per-user, cleared in setUp; no need to clear again here.
        self.assertTrue(is_premium_active(self.user))


# ---------------------------------------------------------------------------
# A4. Priority queue routing
# ---------------------------------------------------------------------------


class PriorityQueueTests(TestCase):
    """Trivial unit tests for src.api.task_utils.

    Covers premium gate #5 — premium users land on the 'premium' Celery
    queue with priority 9; free users on 'regular' with priority 5.
    """

    def test_free_user_routes_to_regular_queue(self):
        from src.api.task_utils import get_task_queue

        self.assertEqual(get_task_queue(is_premium=False), "regular")

    def test_premium_user_routes_to_premium_queue(self):
        from src.api.task_utils import get_task_queue

        self.assertEqual(get_task_queue(is_premium=True), "premium")

    def test_free_user_priority_is_five(self):
        from src.api.task_utils import get_task_priority

        self.assertEqual(get_task_priority(is_premium=False), 5)

    def test_premium_user_priority_is_nine(self):
        from src.api.task_utils import get_task_priority

        self.assertEqual(get_task_priority(is_premium=True), 9)


# ---------------------------------------------------------------------------
# A5. Settings-level limits exposed
# ---------------------------------------------------------------------------


class SettingsLimitsExposedTests(TestCase):
    """Smoke-test that premium-superior settings are non-zero & > free.

    Catches the "env var typo silently makes premium worse than free"
    failure mode — covers gates #2, #3, #6.
    """

    def test_html_to_pdf_premium_chars_positive_and_above_free(self):
        from django.conf import settings

        self.assertGreater(settings.HTML_TO_PDF_MAX_CHARS_PREMIUM, 0)
        self.assertGreater(
            settings.HTML_TO_PDF_MAX_CHARS_PREMIUM,
            settings.HTML_TO_PDF_MAX_CHARS_FREE,
        )

    def test_max_file_size_premium_positive_and_above_free(self):
        from django.conf import settings

        self.assertGreater(settings.MAX_FILE_SIZE_PREMIUM, 0)
        self.assertGreater(
            settings.MAX_FILE_SIZE_PREMIUM,
            settings.MAX_FILE_SIZE_FREE,
        )

    def test_max_pdf_pages_premium_positive_and_above_free(self):
        from django.conf import settings

        self.assertGreater(settings.MAX_PDF_PAGES_PREMIUM, 0)
        self.assertGreater(
            settings.MAX_PDF_PAGES_PREMIUM,
            settings.MAX_PDF_PAGES_FREE,
        )


# ---------------------------------------------------------------------------
# A5a. get_max_batch_files honours settings (not hardcoded 1/10)
# ---------------------------------------------------------------------------


@override_settings(MAX_BATCH_FILES_FREE=1, MAX_BATCH_FILES_PREMIUM=3)
class GetMaxBatchFilesSettingsTests(TestCase):
    """get_max_batch_files must read the configured limits, so the advertised
    cap (get_premium_features, which reads settings) and the enforced cap can't
    diverge when an admin tunes the env var.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="mbf@t.test", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="MBF",
            slug="mbf",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def test_free_user_uses_settings_free_limit(self):
        from src.api.premium_utils import get_max_batch_files

        self.assertEqual(get_max_batch_files(self.user), 1)

    def test_premium_user_uses_settings_premium_limit(self):
        from src.api.premium_utils import get_max_batch_files

        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_mbf",
            provider_customer_id="cust_mbf",
        )
        self.assertEqual(get_max_batch_files(self.user), 3)


# ---------------------------------------------------------------------------
# A5b. Daily expiry sweep invalidates the premium cache
# ---------------------------------------------------------------------------


@override_settings(PAYMENTS_ENABLED=True)
class DailyExpirySweepCacheTests(TestCase):
    """The daily subscription task flips is_premium=False via bulk_update,
    which bypasses User.save() and therefore its cache invalidation. The task
    must delete the premium caches itself, or an expired user keeps premium
    behaviour until the short TTL lapses.
    """

    def setUp(self):
        cache.clear()
        self.user = User.objects.create_user(email="sweep@t.test", password="p")
        # Reproduce the genuine stale state: is_premium=True in the DB while the
        # end date is already in the past. This only arises WITHOUT a save()
        # (time elapsed since the last write) — exactly what the daily sweep is
        # for — so we bypass save()'s normalisation via .update().
        User.objects.filter(pk=self.user.pk).update(
            is_premium=True,
            subscription_start_date=timezone.now() - timedelta(days=31),
            subscription_end_date=timezone.now() - timedelta(days=1),
        )

    def test_sweep_clears_stale_premium_cache_for_expired_user(self):
        from src.tasks.maintenance import update_subscription_daily

        # Caches still say premium (as they would right after expiry).
        cache.set(f"user_premium_active:{self.user.pk}", True, 300)
        cache.set(f"user_subscription_status_{self.user.pk}", True, 300)

        update_subscription_daily()

        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        self.assertIsNone(cache.get(f"user_premium_active:{self.user.pk}"))
        self.assertIsNone(cache.get(f"user_subscription_status_{self.user.pk}"))


# ---------------------------------------------------------------------------
# A6. Batch path per-file limit parity (size / pages / OCR)
# ---------------------------------------------------------------------------


@override_settings(PAYMENTS_ENABLED=True, RATELIMIT_ENABLE=False)
class BatchPerFileLimitParityTests(TestCase):
    """Batch endpoints must enforce the SAME per-file premium limits as the
    single-file path.

    Access model (product decision): free users keep 1-file batch, but the
    batch path must not be a loophole around the size cap, the PDF page cap,
    or the OCR-premium gate that the single endpoint enforces. A free user
    routing one oversized / long / OCR-flagged file through /batch/ must be
    rejected exactly as the single endpoint would reject it.
    """

    CROP_BATCH = "/api/pdf-edit/crop/batch/"
    WORD_BATCH = "/api/pdf-to-word/batch/"
    TEXT_BATCH = "/api/pdf-to-text/batch/"
    REFERER = "https://convertica.net/"

    def setUp(self):
        cache.clear()  # purge stale user_premium_active:{pk} keys
        self.client = Client()
        self.user = User.objects.create_user(
            email="batchgate@t.test", password="passw0rd!"
        )
        self.assertFalse(self.user.is_premium)
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly Batch",
            slug="monthly-batch",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def _go_premium(self):
        now = timezone.now()
        self.user.activate_premium(
            plan=self.plan,
            period_start=now,
            period_end=now + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_batch",
            provider_customer_id="cust_batch",
        )

    def _crop_data(self, files):
        return {
            "pdf_files": files,
            "x": "0",
            "y": "0",
            "width": "10",
            "height": "10",
            "pages": "all",
        }

    # ---- OCR gate parity --------------------------------------------------

    def test_free_user_ocr_via_batch_blocked(self):
        """Free user requesting OCR through the batch endpoint → 403."""
        self.client.force_login(self.user)
        resp = self.client.post(
            self.WORD_BATCH,
            data={"pdf_files": [_fake_pdf("o.pdf")], "ocr_enabled": "true"},
            format="multipart",
            HTTP_REFERER=self.REFERER,
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("OCR is a premium feature", resp.json().get("error", ""))

    def test_premium_user_ocr_via_batch_passes_gate(self):
        """Premium user must NOT be blocked by the batch OCR gate."""
        self._go_premium()
        self.client.force_login(self.user)
        resp = self.client.post(
            self.WORD_BATCH,
            data={"pdf_files": [_fake_pdf("o.pdf")], "ocr_enabled": "true"},
            format="multipart",
            HTTP_REFERER=self.REFERER,
        )
        # Gate passed — the fake PDF may fail downstream, but it must not be a
        # 403 with the OCR-premium message.
        if resp.status_code == 403:
            self.assertNotIn("OCR is a premium feature", resp.json().get("error", ""))

    # ---- File-size cap parity --------------------------------------------

    @override_settings(MAX_FILE_SIZE_FREE=100)
    def test_free_user_oversized_file_via_batch_rejected(self):
        """Free user posting a file over the free size cap to /batch/ → 413."""
        big = SimpleUploadedFile(
            "big.pdf", b"%PDF-1.4\n" + b"x" * 500, content_type="application/pdf"
        )
        self.client.force_login(self.user)
        resp = self.client.post(
            self.CROP_BATCH,
            data=self._crop_data([big]),
            format="multipart",
            HTTP_REFERER=self.REFERER,
        )
        self.assertEqual(resp.status_code, 413)

    @override_settings(MAX_FILE_SIZE_FREE=100)
    def test_premium_user_large_file_via_batch_passes_size_gate(self):
        """Premium user above the *free* cap still passes (premium cap higher)."""
        self._go_premium()
        self.client.force_login(self.user)
        big = SimpleUploadedFile(
            "big.pdf", b"%PDF-1.4\n" + b"x" * 500, content_type="application/pdf"
        )
        resp = self.client.post(
            self.CROP_BATCH,
            data=self._crop_data([big]),
            format="multipart",
            HTTP_REFERER=self.REFERER,
        )
        self.assertNotEqual(resp.status_code, 413)

    # ---- Page-count cap parity -------------------------------------------

    @override_settings(MAX_PDF_PAGES_FREE=1)
    def test_free_user_too_many_pages_via_batch_rejected(self):
        """Free user posting a PDF over the free page cap to /batch/ → 400."""
        self.client.force_login(self.user)
        resp = self.client.post(
            self.TEXT_BATCH,
            data={"pdf_files": [_real_pdf(pages=3)]},
            format="multipart",
            HTTP_REFERER=self.REFERER,
        )
        self.assertEqual(resp.status_code, 400)

    # ---- Regression: Option B (free 1-file batch stays allowed) ----------

    def test_free_user_single_in_limit_file_passes_gates(self):
        """A free user's single in-limit file must still clear the premium
        gates (it may fail later on the unparseable fake PDF, but it must not
        be rejected as 403/413 — that would break free 1-file batch)."""
        self.client.force_login(self.user)
        resp = self.client.post(
            self.CROP_BATCH,
            data=self._crop_data([_fake_pdf("ok.pdf")]),
            format="multipart",
            HTTP_REFERER=self.REFERER,
        )
        self.assertNotIn(resp.status_code, (403, 413))
