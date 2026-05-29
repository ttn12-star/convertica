"""API-key quota refund on failed requests (CONVERTICA audit Sec-4).

Quota is charged at authentication time (race-safe F() increment). Without a
refund, a request that 400s/413s/429s/500s still burns a paid monthly quota
unit. APIKeyAuthentication marks the request; APIKeyQuotaRefundMiddleware
refunds the unit on any non-2xx response. OPTIONS preflight is not metered.
"""

from __future__ import annotations

from datetime import timedelta

from django.http import HttpResponse
from django.test import RequestFactory, TestCase
from django.utils import timezone
from src.api.auth.api_key_auth import APIKeyAuthentication
from src.api.middleware import APIKeyQuotaRefundMiddleware
from src.users.models import APIKey, SubscriptionPlan, User, UserSubscription


class _Base(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="dev2@x.com", password="p")
        self.plan = SubscriptionPlan.objects.create(
            name="Yearly",
            slug="yearly-hero",
            price=79,
            duration_days=365,
            api_quota_per_month=100,
        )
        self.user.activate_subscription(self.plan)
        now = timezone.now()
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            provider="test",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=365),
        )
        self.key, self.plaintext = APIKey.issue(user=self.user, name="ci", scope=["*"])
        self.rf = RequestFactory()
        self.auth = APIKeyAuthentication()

    def _usage(self):
        return APIKey.objects.get(pk=self.key.pk).usage_this_month


class AuthChargeMarkerTests(_Base):
    def test_authenticate_charges_and_marks_request(self):
        req = self.rf.post(
            "/api/v1/pdf-to-word/", HTTP_AUTHORIZATION=f"Bearer {self.plaintext}"
        )
        self.auth.authenticate(req)
        self.assertEqual(self._usage(), 1)
        self.assertEqual(getattr(req, "_cvk_api_key_charge", None), self.key.pk)

    def test_options_preflight_is_not_metered(self):
        req = self.rf.generic(
            "OPTIONS",
            "/api/v1/pdf-to-word/",
            HTTP_AUTHORIZATION=f"Bearer {self.plaintext}",
        )
        self.auth.authenticate(req)
        self.assertEqual(self._usage(), 0)


class RefundMiddlewareTests(_Base):
    def setUp(self):
        super().setUp()
        self.mw = APIKeyQuotaRefundMiddleware(lambda r: None)
        APIKey.objects.filter(pk=self.key.pk).update(usage_this_month=5)

    def test_refund_on_4xx(self):
        req = self.rf.post("/api/v1/x/")
        req._cvk_api_key_charge = self.key.pk
        self.mw.process_response(req, HttpResponse(status=400))
        self.assertEqual(self._usage(), 4)

    def test_no_refund_on_2xx(self):
        req = self.rf.post("/api/v1/x/")
        req._cvk_api_key_charge = self.key.pk
        self.mw.process_response(req, HttpResponse(status=200))
        self.assertEqual(self._usage(), 5)

    def test_no_refund_when_not_api_key_request(self):
        req = self.rf.post("/api/v1/x/")  # no marker
        self.mw.process_response(req, HttpResponse(status=400))
        self.assertEqual(self._usage(), 5)
