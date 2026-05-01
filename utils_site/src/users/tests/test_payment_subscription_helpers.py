from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription


class PaymentRecordCompletedTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="p@t.test", password="x")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="m",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def test_creates_payment_with_provider(self):
        payment, created = Payment.record_completed(
            user=self.user,
            plan=self.plan,
            amount=Decimal("7.99"),
            external_payment_id="ls_order_42",
            provider="lemonsqueezy",
        )
        self.assertTrue(created)
        self.assertEqual(payment.status, "completed")
        self.assertEqual(payment.provider, "lemonsqueezy")
        self.assertEqual(payment.payment_method, "lemonsqueezy")
        self.assertEqual(payment.payment_id, "ls_order_42")

    def test_idempotent_on_same_external_id(self):
        Payment.record_completed(
            user=self.user,
            plan=self.plan,
            amount=Decimal("7.99"),
            external_payment_id="ls_order_42",
            provider="lemonsqueezy",
        )
        payment, created = Payment.record_completed(
            user=self.user,
            plan=self.plan,
            amount=Decimal("7.99"),
            external_payment_id="ls_order_42",
            provider="lemonsqueezy",
        )
        self.assertFalse(created)
        self.assertEqual(Payment.objects.count(), 1)

    def test_handles_integrity_error_race(self):
        """If another worker inserted the row between our get and save,
        we should still return (existing, False) — not raise IntegrityError."""
        from unittest.mock import patch

        from django.db import IntegrityError

        # First call succeeds normally.
        first, created = Payment.record_completed(
            user=self.user,
            plan=self.plan,
            amount=Decimal("7.99"),
            external_payment_id="race_id",
            provider="lemonsqueezy",
        )
        self.assertTrue(created)

        # Simulate the race: ORM `get` claims DoesNotExist, but `save` then
        # raises IntegrityError because the row was created by a racer.
        # We monkeypatch `Payment.objects.get` to raise DoesNotExist on the
        # first call (mimicking the empty-table observation), then return the
        # real row.
        original_get = Payment.objects.get
        call_count = {"n": 0}

        def fake_get(*args, **kwargs):
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise Payment.DoesNotExist
            return original_get(*args, **kwargs)

        with patch.object(Payment.objects, "get", side_effect=fake_get):
            second, created = Payment.record_completed(
                user=self.user,
                plan=self.plan,
                amount=Decimal("7.99"),
                external_payment_id="race_id",
                provider="lemonsqueezy",
            )
        self.assertFalse(created)
        self.assertEqual(second.payment_id, "race_id")
        self.assertEqual(Payment.objects.filter(payment_id="race_id").count(), 1)


class UserSubscriptionUpsertTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="s@t.test", password="x")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="m",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )

    def test_creates_when_missing(self):
        now = timezone.now()
        sub, created = UserSubscription.upsert_from_event(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_1",
            provider_customer_id="ls_cust_1",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
        )
        self.assertTrue(created)
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.provider, "lemonsqueezy")

    def test_updates_when_exists(self):
        now = timezone.now()
        UserSubscription.upsert_from_event(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_1",
            provider_customer_id="ls_cust_1",
            status="active",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=False,
        )
        sub, created = UserSubscription.upsert_from_event(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_1",
            provider_customer_id="ls_cust_1",
            status="cancelled",
            current_period_start=now,
            current_period_end=now + timedelta(days=30),
            cancel_at_period_end=True,
        )
        self.assertFalse(created)
        self.assertEqual(sub.status, "cancelled")
        self.assertTrue(sub.cancel_at_period_end)
