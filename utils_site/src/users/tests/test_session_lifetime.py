"""Guard the session lifetime: paid users must stay logged in.

Until 2026-09-21 this was 24h with no sliding window, so a premium user was
silently dropped to anonymous limits one day after logging in — and the tools
work anonymously, so nothing told them they'd lost what they paid for.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.test import Client, TestCase
from django.utils import timezone

User = get_user_model()

PASSWORD = "Str0ngPass!23"


class SessionLifetimeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="sess@t.test", password=PASSWORD)
        self.client = Client()

    def test_session_outlives_a_day(self):
        """A day-long session logs paying users out mid-subscription."""
        self.assertGreater(settings.SESSION_COOKIE_AGE, 86400)

    def test_expiry_slides_forward_on_use(self):
        self.assertTrue(self.client.login(email="sess@t.test", password=PASSWORD))
        session = Session.objects.get(session_key=self.client.session.session_key)
        # Backdate the stored expiry, then make an ordinary request: a sliding
        # window re-stamps it, a fixed one leaves it where it is.
        stale = timezone.now() + timedelta(seconds=60)
        Session.objects.filter(pk=session.pk).update(expire_date=stale)

        self.client.get("/")

        refreshed = Session.objects.get(pk=session.pk)
        self.assertGreater(refreshed.expire_date, stale)
