"""Premium conversion-history page: gating + row rendering."""

from django.test import TestCase
from django.urls import reverse
from src.users.models import OperationRun, User


class ConversionHistoryTests(TestCase):
    def _user(self, premium: bool):
        return User.objects.create_user(
            username="hist-prem" if premium else "hist-free",
            email=f"hist-{'prem' if premium else 'free'}@example.com",
            password="x",
            is_premium=premium,
        )

    def test_anonymous_redirected_to_login(self):
        response = self.client.get(reverse("users:history"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_non_premium_sees_upgrade_cta(self):
        self.client.force_login(self._user(premium=False))
        response = self.client.get(reverse("users:history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium feature")
        self.assertContains(response, reverse("frontend:pricing"))

    def test_premium_sees_own_runs_only(self):
        me = self._user(premium=True)
        other = User.objects.create_user(
            username="other", email="other@example.com", password="x"
        )
        OperationRun.objects.create(
            conversion_type="PDF_TO_WORD",
            status="success",
            user=me,
            input_size=1024,
            output_size=2048,
            duration_ms=350,
        )
        OperationRun.objects.create(
            conversion_type="SECRET_TOOL", status="success", user=other
        )
        OperationRun.objects.create(conversion_type="ANON_TOOL", status="success")

        self.client.force_login(me)
        response = self.client.get(reverse("users:history"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "PDF_TO_WORD")
        self.assertNotContains(response, "SECRET_TOOL")
        self.assertNotContains(response, "ANON_TOOL")
        self.assertContains(response, "350 ms")
