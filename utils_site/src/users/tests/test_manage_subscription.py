from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from src.users.models import SubscriptionPlan, User, UserSubscription


@override_settings(LEMONSQUEEZY_API_KEY="k")
class ManageSubscriptionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="m@t.test", password="x")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("users:manage_subscription")

    def test_no_subscription_redirects_to_pricing(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/pricing/", r.url)

    def test_active_subscription_redirects_to_portal(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_customer_id="cust_x",
            provider_subscription_id="sub_x",
            status="active",
            current_period_start=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
        )
        with patch("src.users.views.LemonSqueezyClient") as mock_client:
            inst = mock_client.return_value
            inst.get_customer.return_value = {
                "urls": {"customer_portal": "https://app.lemonsqueezy.com/billing/abc"}
            }
            r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "https://app.lemonsqueezy.com/billing/abc")

    def test_subscription_without_customer_id_falls_back_to_pricing(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_customer_id="",  # missing
            provider_subscription_id="sub_x",
            status="active",
            current_period_start=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
        )
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/pricing/", r.url)

    def test_ls_error_falls_back_to_pricing(self):
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_customer_id="cust_x",
            provider_subscription_id="sub_x",
            status="active",
            current_period_start=timezone.now() - timedelta(days=5),
            current_period_end=timezone.now() + timedelta(days=25),
        )
        from src.payments.lemonsqueezy import LemonSqueezyError

        with patch("src.users.views.LemonSqueezyClient") as mock_client:
            inst = mock_client.return_value
            inst.get_customer.side_effect = LemonSqueezyError("boom")
            r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("/pricing/", r.url)
