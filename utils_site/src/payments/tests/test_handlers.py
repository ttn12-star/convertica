from datetime import timedelta
from decimal import Decimal

from django.test import TestCase, override_settings
from django.utils import timezone
from src.payments.handlers import (
    handle_order_created,
    handle_order_refunded,
    handle_subscription_cancelled,
    handle_subscription_created,
    handle_subscription_expired,
    handle_subscription_payment_failed,
    handle_subscription_payment_refunded,
    handle_subscription_payment_success,
    handle_subscription_resumed,
    handle_subscription_updated,
)
from src.payments.tests.fixtures.ls_payloads import (
    order_created_payload,
    order_refunded_payload,
    subscription_cancelled_payload,
    subscription_created_payload,
    subscription_expired_payload,
    subscription_payment_failed_payload,
    subscription_payment_refunded_payload,
    subscription_payment_success_payload,
)
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription


class HandlerTestCase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="hh@t.test", password="x")
        self.monthly = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
            ls_variant_id="var_1",
        )
        self.lifetime = SubscriptionPlan.objects.create(
            name="Lifetime",
            slug="lifetime",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            ls_variant_id="var_lifetime",
        )


class SubscriptionCreatedTests(HandlerTestCase):
    def test_creates_subscription_and_grants_premium(self):
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
        )
        handle_subscription_created(payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertEqual(sub.provider, "lemonsqueezy")
        self.assertEqual(sub.status, "active")
        self.assertEqual(sub.provider_subscription_id, "sub_1")

    def test_no_op_if_user_id_unknown(self):
        payload = subscription_created_payload(
            user_id=99999,
            plan_id=self.monthly.id,
        )
        # Must not raise; handler logs and returns.
        handle_subscription_created(payload)
        self.assertFalse(UserSubscription.objects.exists())

    def test_no_op_if_plan_id_unknown(self):
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=99999,
        )
        handle_subscription_created(payload)
        self.assertFalse(UserSubscription.objects.exists())


class SubscriptionUpdatedTests(HandlerTestCase):
    def test_updates_status_and_period(self):
        # Pre-existing subscription
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_start=timezone.now() - timedelta(days=10),
            current_period_end=timezone.now() + timedelta(days=20),
        )
        # Updated payload signals will-cancel
        from src.payments.tests.fixtures.ls_payloads import subscription_updated_payload

        payload = subscription_updated_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
            cancelled=True,
            status="active",
            ends_at="2026-06-15T00:00:00.000000Z",
        )
        handle_subscription_updated(payload)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertTrue(sub.cancel_at_period_end)


class SubscriptionCancelledTests(HandlerTestCase):
    def test_marks_will_cancel_keeps_premium_until_period_end(self):
        future = timezone.now() + timedelta(days=10)
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_start=timezone.now() - timedelta(days=20),
            current_period_end=future,
        )
        self.user.is_premium = True
        self.user.subscription_end_date = future
        self.user.save()

        payload = subscription_cancelled_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
            ends_at="2026-05-11T00:00:00.000000Z",
        )
        handle_subscription_cancelled(payload)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertTrue(sub.cancel_at_period_end)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)  # still premium until end


class SubscriptionExpiredTests(HandlerTestCase):
    def test_revokes_premium(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_start=timezone.now() - timedelta(days=40),
            current_period_end=timezone.now() - timedelta(days=1),
        )
        self.user.is_premium = True
        self.user.save()
        payload = subscription_expired_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
        )
        handle_subscription_expired(payload)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)


class SubscriptionPaymentSuccessTests(HandlerTestCase):
    def test_records_payment_and_extends_period(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now(),
        )
        payload = subscription_payment_success_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
        )
        handle_subscription_payment_success(payload)
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 1)


@override_settings(PAYMENT_PAST_DUE_GRACE_DAYS=3)
class SubscriptionPaymentFailedTests(HandlerTestCase):
    def test_extends_grace_period(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_start=timezone.now() - timedelta(days=30),
            current_period_end=timezone.now(),
        )
        self.user.is_premium = True
        self.user.subscription_end_date = timezone.now()
        self.user.save()
        payload = subscription_payment_failed_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
        )
        handle_subscription_payment_failed(payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)  # still premium during grace
        self.assertGreater(self.user.subscription_end_date, timezone.now())


class SubscriptionPaymentRefundedTests(HandlerTestCase):
    def test_revokes_premium_and_marks_payment_refunded(self):
        sub = UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_end=timezone.now() + timedelta(days=20),
        )
        Payment.objects.create(
            user=self.user,
            plan=self.monthly,
            amount=Decimal("7.99"),
            payment_id="ord_42",
            status="completed",
            payment_method="lemonsqueezy",
            provider="lemonsqueezy",
        )
        self.user.is_premium = True
        self.user.save()
        payload = subscription_payment_refunded_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
            order_id="ord_42",
        )
        handle_subscription_payment_refunded(payload)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
        p = Payment.objects.get(payment_id="ord_42")
        self.assertEqual(p.status, "refunded")


class OrderCreatedLifetimeTests(HandlerTestCase):
    def test_grants_lifetime_premium(self):
        payload = order_created_payload(
            user_id=self.user.id,
            plan_id=self.lifetime.id,
        )
        handle_order_created(payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        self.assertIsNone(self.user.subscription_end_date)
        self.assertTrue(self.user.is_subscription_active())
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 1)


class OrderRefundedLifetimeTests(HandlerTestCase):
    def test_revokes_premium(self):
        # Pre-create
        Payment.objects.create(
            user=self.user,
            plan=self.lifetime,
            amount=Decimal("129.00"),
            payment_id="ord_lifetime_1",
            status="completed",
            payment_method="lemonsqueezy",
            provider="lemonsqueezy",
        )
        self.user.is_premium = True
        self.user.subscription_end_date = None
        self.user.save()
        payload = order_refunded_payload(
            user_id=self.user.id,
            plan_id=self.lifetime.id,
        )
        handle_order_refunded(payload)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_premium)
