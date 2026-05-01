from django.db import IntegrityError
from django.test import TestCase
from src.users.models import WebhookEvent


class WebhookEventTests(TestCase):
    def test_provider_event_id_unique(self):
        WebhookEvent.objects.create(
            provider="lemonsqueezy",
            event_id="evt_1",
            event_type="subscription_created",
        )
        with self.assertRaises(IntegrityError):
            WebhookEvent.objects.create(
                provider="lemonsqueezy",
                event_id="evt_1",
                event_type="subscription_updated",
            )

    def test_same_event_id_different_providers_allowed(self):
        WebhookEvent.objects.create(provider="lemonsqueezy", event_id="evt_1")
        # No exception — different provider scope
        WebhookEvent.objects.create(provider="stripe", event_id="evt_1")
        self.assertEqual(WebhookEvent.objects.count(), 2)

    def test_str_contains_provider_and_event_type(self):
        e = WebhookEvent.objects.create(
            provider="lemonsqueezy",
            event_id="evt_xyz",
            event_type="subscription_created",
        )
        self.assertIn("lemonsqueezy", str(e))
        self.assertIn("subscription_created", str(e))
