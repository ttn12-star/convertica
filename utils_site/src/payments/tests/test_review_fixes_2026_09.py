"""One runnable check per non-trivial payments/users fix from the 2026-09 review."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from src.payments import handlers as h
from src.payments.paddle_webhook import _normalise
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription


def _plan(slug, **kw):
    return SubscriptionPlan.objects.create(
        name=slug, slug=slug, price="7.99", currency="USD", duration_days=30, **kw
    )


class PaddlePlanFromPriceTests(TestCase):
    def test_plan_comes_from_paid_price_not_client_custom_data(self):
        cheap = _plan("monthly", paddle_price_id="pri_monthly")
        lifetime = _plan("lifetime", is_lifetime=True, paddle_price_id="pri_life")
        payload = {
            "data": {
                "id": "txn_1",
                "status": "completed",
                "custom_data": {"user_id": "1", "plan_id": str(lifetime.id)},
                "items": [{"price": {"id": "pri_monthly"}}],
                "details": {"totals": {"grand_total": "799"}},
            }
        }
        norm = _normalise("transaction.completed", payload)
        self.assertEqual(norm["meta"]["custom_data"]["plan_id"], str(cheap.id))


class RevocationFallbackTests(TestCase):
    def test_expired_event_without_custom_data_still_revokes(self):
        user = User.objects.create_user(email="p@t.test", password="x")
        plan = _plan("monthly")
        user.activate_premium(
            plan=plan,
            period_start=timezone.now(),
            period_end=timezone.now() + timedelta(days=30),
            provider="lemonsqueezy",
            provider_subscription_id="sub_42",
            provider_customer_id="cus_1",
        )
        UserSubscription.objects.create(
            user=user,
            plan=plan,
            provider="lemonsqueezy",
            provider_subscription_id="sub_42",
            status="active",
        )
        h.handle_subscription_expired(
            {"meta": {}, "data": {"id": "sub_42", "attributes": {"status": "expired"}}}
        )
        user.refresh_from_db()
        self.assertFalse(user.is_premium)

    def test_unattributable_revocation_is_acked_without_crashing(self):
        # Deleted account / provider test event: nothing to revoke, no 500 loop.
        h.handle_subscription_expired(
            {"meta": {}, "data": {"id": "sub_unknown", "attributes": {}}}
        )


class LifetimeCountersTests(TestCase):
    def test_lifetime_activation_keeps_accrued_days(self):
        user = User.objects.create_user(email="l@t.test", password="x")
        monthly = _plan("monthly")
        start = timezone.now() - timedelta(days=100)
        user.activate_premium(
            plan=monthly,
            period_start=start,
            period_end=timezone.now() + timedelta(days=10),
            provider="polar",
            provider_subscription_id="s",
            provider_customer_id="c",
        )
        user.refresh_from_db()
        before = user.total_subscription_days
        self.assertGreater(before, 90)
        lifetime = _plan("lifetime", is_lifetime=True)
        user.activate_premium(
            plan=lifetime,
            period_start=start,
            period_end=None,
            provider="polar",
            provider_subscription_id="",
            provider_customer_id="c",
        )
        user.refresh_from_db()
        self.assertEqual(user.total_subscription_days, before)


class DataExportTests(TestCase):
    def test_download_data_works_for_a_paying_user(self):
        user = User.objects.create_user(email="d@t.test", password="x")
        plan = _plan("monthly")
        Payment.objects.create(
            user=user, plan=plan, amount="7.99", status="completed", payment_id="ord_1"
        )
        self.client.force_login(user)
        resp = self.client.get(reverse("users:download_data"), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b'"plan_type": "subscription"', resp.content)
