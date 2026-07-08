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

    def test_falls_back_to_plan_duration_on_missing_renews_at(self):
        payload = subscription_created_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
        )
        # Simulate malformed renews_at. created_at must be ~now (a real
        # subscription_created arrives immediately); the fixture hardcodes a
        # fixed past date, which made this test time-fragile (the fallback
        # period_start + 30d drifts into the past as the wall clock advances).
        payload["data"]["attributes"]["renews_at"] = ""
        payload["data"]["attributes"]["created_at"] = timezone.now().isoformat()
        handle_subscription_created(payload)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)
        # Should NOT be lifetime — should be ~30 days from now
        self.assertIsNotNone(self.user.subscription_end_date)
        delta = self.user.subscription_end_date - timezone.now()
        self.assertGreater(delta.days, 25)  # allow some skew
        self.assertLess(delta.days, 35)

    def test_handles_non_numeric_user_id(self):
        payload = subscription_created_payload(
            user_id="not-a-number",
            plan_id=self.monthly.id,
        )
        # Should not raise
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
            ends_at=(timezone.now() + timedelta(days=20)).strftime(
                "%Y-%m-%dT%H:%M:%S.000000Z"
            ),
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
            ends_at=future.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
        )
        handle_subscription_cancelled(payload)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertTrue(sub.cancel_at_period_end)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)  # still premium until end

    def test_tolerates_missing_plan_in_custom_data(self):
        future = timezone.now() + timedelta(days=10)
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_end=future,
        )
        self.user.is_premium = True
        self.user.subscription_end_date = future
        self.user.save()
        payload = subscription_cancelled_payload(
            user_id=self.user.id,
            plan_id=99999,  # missing
            ends_at=future.strftime("%Y-%m-%dT%H:%M:%S.000000Z"),
        )
        # Should not raise; should still mark cancel_at_period_end
        handle_subscription_cancelled(payload)
        sub = UserSubscription.objects.get(user=self.user)
        self.assertTrue(sub.cancel_at_period_end)


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


@override_settings(PAYMENT_PAST_DUE_GRACE_DAYS=0)
class SubscriptionPaymentFailedNoGraceTests(HandlerTestCase):
    def test_single_failed_payment_does_not_revoke_premium(self):
        # Sec-5: Lemon Squeezy retries failed charges (dunning) for days; a
        # single payment_failed must NOT cut off a paying customer. Revocation
        # happens later via subscription_expired.
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_end=timezone.now() + timedelta(days=10),
        )
        self.user.is_premium = True
        self.user.subscription_end_date = timezone.now() + timedelta(days=10)
        self.user.save()
        handle_subscription_payment_failed(
            subscription_payment_failed_payload(
                user_id=self.user.id, plan_id=self.monthly.id
            )
        )
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)  # kept through dunning
        sub = UserSubscription.objects.get(provider_subscription_id="sub_1")
        self.assertEqual(sub.status, "past_due")


class SubscriptionPausedTests(HandlerTestCase):
    def test_paused_with_grace_keeps_streak(self):
        from src.payments.handlers import handle_subscription_paused
        from src.payments.tests.fixtures.ls_payloads import subscription_updated_payload

        # Pre-existing subscription
        UserSubscription.objects.create(
            user=self.user,
            plan=self.monthly,
            provider="lemonsqueezy",
            provider_subscription_id="sub_1",
            provider_customer_id="cust_1",
            status="active",
            current_period_end=timezone.now() + timedelta(days=15),
        )
        # subscription_start_date set 20 days ago so save()'s auto-calc
        # produces consecutive_subscription_days == 21 (start..today inclusive),
        # which is what we'll assert is preserved by deactivate_premium(expired).
        start = timezone.now() - timedelta(days=20)
        self.user.is_premium = True
        self.user.subscription_start_date = start
        self.user.subscription_end_date = timezone.now() + timedelta(days=15)
        self.user.save()
        self.user.refresh_from_db()
        streak_before = self.user.consecutive_subscription_days
        self.assertGreater(streak_before, 0)  # sanity check
        payload = subscription_updated_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,
            status="paused",
        )
        payload["meta"]["event_name"] = "subscription_paused"
        with self.settings(PAYMENT_PAST_DUE_GRACE_DAYS=0):
            handle_subscription_paused(payload)
        self.user.refresh_from_db()
        # Without grace, premium revoked, but streak preserved (reason=expired)
        self.assertFalse(self.user.is_premium)
        self.assertEqual(self.user.consecutive_subscription_days, streak_before)


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


class OrderCreatedSubscriptionNoDoublePaymentTests(HandlerTestCase):
    """A subscription purchase must yield exactly ONE Payment row.

    LS fires BOTH `order_created` AND `subscription_payment_success` on the
    first charge of a subscription. `order_created` keys its Payment on the
    order id; `subscription_payment_success` keys on the invoice/order_id from
    the subscription-invoice object — a DIFFERENT key — so `record_completed`
    can't dedupe them and two Payment rows appear for one real charge.
    `handle_order_created` must therefore skip subscription (non-lifetime)
    plans; the subscription_* events are the source of truth for those.
    """

    def test_order_created_for_subscription_plan_records_no_payment(self):
        payload = order_created_payload(
            user_id=self.user.id,
            plan_id=self.monthly.id,  # subscription plan (not lifetime)
            order_id="ord_sub_first",
        )
        handle_order_created(payload)
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 0)

    def test_subscription_first_purchase_records_single_payment(self):
        uid, pid = self.user.id, self.monthly.id
        # Real first-purchase event sequence for a subscription plan.
        handle_subscription_created(
            subscription_created_payload(user_id=uid, plan_id=pid)
        )
        handle_order_created(
            order_created_payload(user_id=uid, plan_id=pid, order_id="ord_sub_first")
        )
        handle_subscription_payment_success(
            subscription_payment_success_payload(
                user_id=uid, plan_id=pid, order_id="inv_order_ref"
            )
        )
        # Exactly one Payment — the authoritative subscription charge.
        self.assertEqual(Payment.objects.filter(user=self.user).count(), 1)
        # Premium still granted (via subscription_created), not lost by the skip.
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_premium)


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


class RefundReconciliationLoggingTests(HandlerTestCase):
    def test_refund_with_no_matching_payment_logs_warning(self):
        # Sec-6: refund revokes premium even if no Payment row matches; that
        # gap must be visible in logs for reconciliation.
        from src.payments.handlers import handle_order_refunded
        from src.payments.tests.fixtures.ls_payloads import order_refunded_payload

        self.user.is_premium = True
        self.user.save()
        payload = order_refunded_payload(user_id=self.user.id, plan_id=self.lifetime.id)
        with self.assertLogs("src.payments.handlers", level="WARNING") as cm:
            handle_order_refunded(payload)
        self.assertTrue(any("matched no Payment row" in m for m in cm.output))


class ZeroAmountPaymentLoggingTests(HandlerTestCase):
    def test_zero_amount_paid_plan_logs_warning(self):
        # Sec-7: a $0 completed payment for a paid plan is suspicious; log it.
        from src.payments.handlers import handle_order_created
        from src.payments.tests.fixtures.ls_payloads import order_created_payload

        payload = order_created_payload(user_id=self.user.id, plan_id=self.lifetime.id)
        payload["data"]["attributes"]["total"] = 0
        with self.assertLogs("src.payments.handlers", level="WARNING") as cm:
            handle_order_created(payload)
        self.assertTrue(any("non-positive amount" in m for m in cm.output))
