import json
from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from src.users.models import SubscriptionPlan, User, UserSubscription


@override_settings(
    LEMONSQUEEZY_API_KEY="key",
    LEMONSQUEEZY_STORE_ID="store_1",
    PAYMENTS_ENABLED=True,
)
class CreateCheckoutSessionTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="a@b.test", password="pw")
        self.plan = SubscriptionPlan.objects.create(
            name="Monthly",
            slug="monthly",
            price=Decimal("7.99"),
            currency="USD",
            duration_days=30,
            ls_variant_id="var_1",
            is_active=True,
        )
        self.client = Client()
        self.client.force_login(self.user)
        self.url = reverse("payments:create_checkout_session")

    def test_returns_checkout_url(self):
        with patch(
            "src.payments.views.LemonSqueezyClient.create_checkout"
        ) as mock_create:
            mock_create.return_value = {
                "id": "ck_1",
                "url": "https://example.lemonsqueezy.com/buy/abc",
            }
            r = self.client.post(
                self.url,
                data=json.dumps({"plan_slug": "monthly"}),
                content_type="application/json",
            )
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(
            body["checkout_url"], "https://example.lemonsqueezy.com/buy/abc"
        )

    def test_404_for_unknown_plan(self):
        r = self.client.post(
            self.url,
            data=json.dumps({"plan_slug": "nope"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 404)

    def test_409_when_already_subscribed(self):
        # Pre-existing active subscription
        UserSubscription.objects.create(
            user=self.user,
            plan=self.plan,
            provider="lemonsqueezy",
            provider_subscription_id="sub_x",
            provider_customer_id="cust_x",
            status="active",
            current_period_start=timezone.now() - timedelta(days=10),
            current_period_end=timezone.now() + timedelta(days=20),
        )
        with patch("src.payments.views.LemonSqueezyClient.get_customer") as mock_cust:
            mock_cust.return_value = {
                "urls": {"customer_portal": "https://app.lemonsqueezy.com/billing/x"}
            }
            r = self.client.post(
                self.url,
                data=json.dumps({"plan_slug": "monthly"}),
                content_type="application/json",
            )
        self.assertEqual(r.status_code, 409)
        self.assertIn("portal_url", r.json())

    def test_503_when_payments_disabled(self):
        with override_settings(PAYMENTS_ENABLED=False):
            r = self.client.post(
                self.url,
                data=json.dumps({"plan_slug": "monthly"}),
                content_type="application/json",
            )
        self.assertEqual(r.status_code, 503)

    def test_redirects_unauthenticated(self):
        anon = Client()
        r = anon.post(
            self.url,
            data=json.dumps({"plan_slug": "monthly"}),
            content_type="application/json",
        )
        self.assertIn(r.status_code, (302, 401, 403))
