"""Regression tests for the admin `is_premium` toggle.

History: ticking `is_premium` in admin used to leave a stale
`subscription_end_date` in place. The User.is_subscription_active()
method's strict `now <= end_date` branch then returned False, so every
premium gate stayed shut even though the admin checkbox was checked.

These tests pin down the admin-save_model contract:
  1. is_premium + no end_date  → premium active (lifetime / manual).
  2. is_premium + stale end_date → end_date cleared, premium active.
  3. is_premium + future end_date → end_date preserved, premium active.
"""

from __future__ import annotations

from datetime import timedelta

from django.contrib.admin.sites import AdminSite
from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone
from src.api.premium_utils import is_premium_active
from src.users.admin import UserAdmin
from src.users.models import User


class AdminPremiumToggleTests(TestCase):
    """Direct-call save_model() to mimic an admin form submission."""

    def setUp(self):
        cache.clear()
        self.admin = UserAdmin(User, AdminSite())

    def _apply_admin_save(self, user: User) -> User:
        """Run the admin's save_model hook and return a freshly fetched user."""
        self.admin.save_model(request=None, obj=user, form=None, change=True)
        return User.objects.get(pk=user.pk)

    def test_no_end_date_grants_premium(self):
        user = User.objects.create_user(email="adm1@t.test", password="x")
        user.is_premium = True
        fresh = self._apply_admin_save(user)
        self.assertTrue(fresh.is_premium)
        self.assertIsNone(fresh.subscription_end_date)
        self.assertTrue(is_premium_active(fresh))

    def test_stale_end_date_cleared_so_premium_activates(self):
        past = timezone.now() - timedelta(days=365)
        user = User.objects.create_user(
            email="adm2@t.test",
            password="x",
            subscription_end_date=past,
        )
        user.is_premium = True
        fresh = self._apply_admin_save(user)
        self.assertTrue(fresh.is_premium)
        # Stale end_date must be wiped so `is_subscription_active()` falls
        # through to the "no end_date → is_premium" branch.
        self.assertIsNone(fresh.subscription_end_date)
        self.assertTrue(is_premium_active(fresh))

    def test_future_end_date_preserved(self):
        future = timezone.now() + timedelta(days=30)
        user = User.objects.create_user(
            email="adm3@t.test",
            password="x",
            is_premium=True,
            subscription_end_date=future,
        )
        # Re-save through admin (admin "save" without changes).
        fresh = self._apply_admin_save(user)
        self.assertTrue(fresh.is_premium)
        self.assertIsNotNone(fresh.subscription_end_date)
        # Allow microsecond drift — compare dates instead of exact equality.
        self.assertEqual(
            fresh.subscription_end_date.date(),
            future.date(),
        )
        self.assertTrue(is_premium_active(fresh))

    def test_admin_save_invalidates_premium_cache(self):
        user = User.objects.create_user(email="adm4@t.test", password="x")
        # Pre-populate cache with a stale "False" entry.
        cache.set(f"user_premium_active:{user.pk}", False, 60)
        cache.set(f"user_subscription_status_{user.id}", False, 300)
        user.is_premium = True
        fresh = self._apply_admin_save(user)
        # Caches must be flushed by the save flow so the new state shows
        # up immediately on the next request.
        self.assertIsNone(cache.get(f"user_premium_active:{fresh.pk}"))
        self.assertIsNone(cache.get(f"user_subscription_status_{fresh.id}"))
        self.assertTrue(is_premium_active(fresh))
