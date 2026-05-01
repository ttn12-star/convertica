from decimal import Decimal

from django.test import TestCase
from src.users.models import Payment, SubscriptionPlan, User, UserSubscription


class ProviderFieldsTests(TestCase):
    def test_user_has_provider_fields_with_defaults(self):
        u = User.objects.create_user(email="a@b.test", password="x")
        self.assertEqual(u.payment_provider, "")
        self.assertEqual(u.provider_customer_id, "")

    def test_subscription_plan_has_ls_fields_and_lifetime_flag(self):
        plan = SubscriptionPlan.objects.create(
            name="Lifetime Hero",
            slug="lifetime-hero",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            ls_variant_id="abc123",
            ls_product_id="prod_xyz",
        )
        self.assertTrue(plan.is_lifetime)
        self.assertEqual(plan.ls_variant_id, "abc123")
        self.assertEqual(plan.ls_product_id, "prod_xyz")

    def test_user_subscription_provider_fields(self):
        u = User.objects.create_user(email="b@c.test", password="x")
        plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="m",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )
        sub = UserSubscription.objects.create(
            user=u,
            plan=plan,
            provider="lemonsqueezy",
            provider_subscription_id="ls_sub_1",
            provider_customer_id="ls_cust_1",
        )
        self.assertEqual(sub.provider, "lemonsqueezy")
        self.assertEqual(sub.provider_subscription_id, "ls_sub_1")
        self.assertEqual(sub.provider_customer_id, "ls_cust_1")

    def test_payment_provider_field_defaults_to_lemonsqueezy(self):
        u = User.objects.create_user(email="c@d.test", password="x")
        plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="m",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )
        p = Payment.objects.create(
            user=u,
            plan=plan,
            amount=Decimal("7.99"),
            payment_id="pay_1",
            status="completed",
        )
        self.assertEqual(p.provider, "lemonsqueezy")
