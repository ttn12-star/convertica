"""Who the daily unverified-account cleanup deletes, and who it must not.

Also covers the admin "Email verified" column/filter that surfaces the same state.
"""

from allauth.account.models import EmailAddress
from allauth.socialaccount.models import SocialAccount
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from src.tasks.user_cleanup import delete_unverified_accounts

User = get_user_model()


class DeleteUnverifiedAccountsTests(TestCase):
    def _user(self, email, days_old, **kwargs):
        user = User.objects.create_user(
            username=email.split("@")[0], email=email, password="x", **kwargs
        )
        User.objects.filter(pk=user.pk).update(
            date_joined=timezone.now() - timezone.timedelta(days=days_old)
        )
        return user

    def test_deletes_only_stale_unverified_non_social_accounts(self):
        doomed = self._user("spam@example.com", 40)
        EmailAddress.objects.create(user=doomed, email=doomed.email, verified=False)

        fresh = self._user("fresh@example.com", 5)
        EmailAddress.objects.create(user=fresh, email=fresh.email, verified=False)

        verified = self._user("real@example.com", 40)
        EmailAddress.objects.create(user=verified, email=verified.email, verified=True)

        # Google login with an unverified provider email: no verified EmailAddress
        # row, but the account still works — must survive.
        social = self._user("google@example.com", 40)
        EmailAddress.objects.create(user=social, email=social.email, verified=False)
        SocialAccount.objects.create(user=social, provider="google", uid="uid-1")

        premium = self._user("premium@example.com", 40, is_premium=True)
        staff = self._user("staff@example.com", 40, is_staff=True)

        self.assertEqual(delete_unverified_accounts(), 1)
        self.assertFalse(User.objects.filter(pk=doomed.pk).exists())
        for survivor in (fresh, verified, social, premium, staff):
            self.assertTrue(
                User.objects.filter(pk=survivor.pk).exists(),
                f"{survivor.email} must not be deleted",
            )


class UserAdminEmailVerifiedColumnTests(TestCase):
    """The admin changelist column + filter must reflect the real verified state."""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="root", email="root@example.com", password="x"
        )
        EmailAddress.objects.create(
            user=self.admin, email=self.admin.email, verified=True
        )
        self.unverified = User.objects.create_user(
            username="spam", email="spam@example.com", password="x"
        )
        EmailAddress.objects.create(
            user=self.unverified, email=self.unverified.email, verified=False
        )
        # No EmailAddress row at all — must still count as "not verified".
        self.no_row = User.objects.create_user(
            username="norow", email="norow@example.com", password="x"
        )
        self.client.force_login(self.admin)
        self.url = reverse("admin:users_user_changelist")

    def test_filter_splits_verified_from_unverified(self):
        unverified = self.client.get(self.url, {"email_verified": "0"})
        self.assertEqual(unverified.status_code, 200)
        emails = {u.email for u in unverified.context["cl"].queryset}
        self.assertEqual(emails, {self.unverified.email, self.no_row.email})

        verified = self.client.get(self.url, {"email_verified": "1"})
        self.assertEqual(
            {u.email for u in verified.context["cl"].queryset}, {self.admin.email}
        )

    def test_column_annotation_is_available_on_rows(self):
        response = self.client.get(self.url)
        rows = {u.email: u._email_verified for u in response.context["cl"].queryset}
        self.assertTrue(rows[self.admin.email])
        self.assertFalse(rows[self.unverified.email])
        self.assertFalse(rows[self.no_row.email])
