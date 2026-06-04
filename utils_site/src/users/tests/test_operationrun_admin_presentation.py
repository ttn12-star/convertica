"""Admin presentation regressions: premium badge + decluttered index.

Premium operations must stand out in the OperationRun changelist (gold badge,
row tint), and the admin index must not list models we never manage there
(Group, SocialToken) while keeping the ones that are functional (SocialApp
holds the OAuth credentials social login reads from the DB).
"""

from __future__ import annotations

from allauth.socialaccount.models import SocialApp, SocialToken
from django.contrib import admin
from django.contrib.auth.models import Group
from django.test import TestCase
from src.users.models import OperationRun


class AdminDeclutterTests(TestCase):
    def test_group_and_socialtoken_are_hidden(self):
        self.assertNotIn(Group, admin.site._registry)
        self.assertNotIn(SocialToken, admin.site._registry)

    def test_socialapp_is_kept(self):
        # SocialApp stores the Google/Facebook OAuth credentials that social
        # login reads from the DB — unregistering it would hide a live setting.
        self.assertIn(SocialApp, admin.site._registry)


class PremiumBadgeTests(TestCase):
    def _admin(self):
        return admin.site._registry[OperationRun]

    def test_badge_marks_premium_runs(self):
        run = OperationRun.objects.create(
            conversion_type="word_to_pdf", is_premium=True
        )
        html = self._admin().premium_badge(run)
        self.assertIn("PREMIUM", html)
        self.assertIn("premium-badge", html)  # the class the row-tint CSS targets

    def test_badge_is_muted_for_free_runs(self):
        run = OperationRun.objects.create(
            conversion_type="word_to_pdf", is_premium=False
        )
        html = self._admin().premium_badge(run)
        self.assertNotIn("PREMIUM", html)
        self.assertIn("free", html)
