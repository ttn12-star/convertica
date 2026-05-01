import json

import responses
from django.test import TestCase, override_settings
from src.payments.lemonsqueezy import LemonSqueezyClient


@override_settings(
    LEMONSQUEEZY_API_KEY="test_api_key",
    LEMONSQUEEZY_STORE_ID="store_1",
    LEMONSQUEEZY_API_BASE="https://api.lemonsqueezy.com/v1",
)
class LemonSqueezyClientTests(TestCase):
    @responses.activate
    def test_create_checkout_posts_correct_payload(self):
        responses.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            json={
                "data": {
                    "id": "ck_1",
                    "attributes": {
                        "url": "https://convertica.lemonsqueezy.com/checkout/buy/abc"
                    },
                }
            },
            status=201,
        )
        client = LemonSqueezyClient(api_key="test_api_key")
        result = client.create_checkout(
            store_id="store_1",
            variant_id="var_42",
            custom_data={"user_id": "1", "plan_id": "2"},
            success_url="https://convertica.net/payments/success/",
            email="u@t.test",
            locale="en",
        )
        self.assertEqual(
            result,
            {
                "id": "ck_1",
                "url": "https://convertica.lemonsqueezy.com/checkout/buy/abc",
            },
        )
        sent = json.loads(responses.calls[0].request.body)
        self.assertEqual(sent["data"]["type"], "checkouts")
        self.assertEqual(
            sent["data"]["attributes"]["checkout_data"]["custom"],
            {"user_id": "1", "plan_id": "2"},
        )
        self.assertEqual(
            sent["data"]["attributes"]["checkout_data"]["email"], "u@t.test"
        )

    @responses.activate
    def test_get_subscription(self):
        responses.get(
            "https://api.lemonsqueezy.com/v1/subscriptions/sub_1",
            json={"data": {"id": "sub_1", "attributes": {"status": "active"}}},
            status=200,
        )
        client = LemonSqueezyClient(api_key="test_api_key")
        result = client.get_subscription("sub_1")
        self.assertEqual(result["id"], "sub_1")

    @responses.activate
    def test_get_customer_returns_portal_url(self):
        responses.get(
            "https://api.lemonsqueezy.com/v1/customers/cust_1",
            json={
                "data": {
                    "id": "cust_1",
                    "attributes": {
                        "urls": {
                            "customer_portal": "https://app.lemonsqueezy.com/billing/abc"
                        }
                    },
                }
            },
            status=200,
        )
        client = LemonSqueezyClient(api_key="test_api_key")
        result = client.get_customer("cust_1")
        self.assertEqual(
            result["urls"]["customer_portal"],
            "https://app.lemonsqueezy.com/billing/abc",
        )

    @responses.activate
    def test_cancel_subscription_uses_delete(self):
        responses.delete(
            "https://api.lemonsqueezy.com/v1/subscriptions/sub_x",
            json={"data": {"id": "sub_x", "attributes": {"status": "cancelled"}}},
            status=200,
        )
        client = LemonSqueezyClient(api_key="test_api_key")
        client.cancel_subscription("sub_x")
        self.assertEqual(len(responses.calls), 1)
        self.assertEqual(responses.calls[0].request.method, "DELETE")
