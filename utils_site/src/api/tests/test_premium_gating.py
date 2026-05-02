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
