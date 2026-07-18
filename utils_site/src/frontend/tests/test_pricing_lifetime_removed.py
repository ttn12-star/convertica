"""Lifetime plan is retired: it must not surface on any public page.

Guards the removal end-to-end — even if a stray lifetime-hero row still exists
in the DB, neither the pricing page nor the API landing may render it, and the
checkout JS must not offer it.
"""

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase, override_settings
from django.urls import reverse
from src.users.models import SubscriptionPlan


@override_settings(DEBUG=False)
class LifetimeRemovedTests(TestCase):
    def setUp(self):
        # A lingering lifetime plan must still not appear anywhere.
        SubscriptionPlan.objects.create(
            name="Lifetime Hero Access",
            slug="lifetime-hero",
            price=Decimal("129.00"),
            currency="USD",
            duration_days=0,
            is_lifetime=True,
            is_active=True,
        )

    def test_pricing_page_drops_lifetime_and_keeps_others(self):
        html = self.client.get(reverse("frontend:pricing")).content.decode()
        self.assertNotIn("Lifetime Hero", html)
        self.assertNotIn("lifetime-hero", html)  # checkout JS map cleaned
        self.assertIn("Yearly Hero", html)
        self.assertIn("Monthly Hero", html)

    def test_api_landing_drops_lifetime_tier(self):
        html = self.client.get(reverse("api_landing")).content.decode()
        self.assertNotIn("Lifetime", html)
        self.assertIn("Yearly", html)
