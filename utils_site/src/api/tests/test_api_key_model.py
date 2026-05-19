import hashlib

from django.test import TestCase
from src.users.models import APIKey, User


class APIKeyIssueTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(email="u@x.com", password="p")

    def test_issue_returns_plaintext_and_persists_hash_only(self):
        key, plaintext = APIKey.issue(user=self.user, name="ci", scope=["*"])
        self.assertTrue(plaintext.startswith("cvk_live_"))
        self.assertEqual(key.key_hash, hashlib.sha256(plaintext.encode()).hexdigest())
        # No way to derive plaintext from stored record
        self.assertNotIn(plaintext, str(key.__dict__))

    def test_revoke(self):
        key, _ = APIKey.issue(user=self.user, name="ci", scope=["*"])
        self.assertTrue(key.is_active)
        key.revoke()
        self.assertFalse(key.is_active)

    def test_two_keys_have_distinct_prefixes(self):
        k1, _ = APIKey.issue(user=self.user, name="a", scope=["*"])
        k2, _ = APIKey.issue(user=self.user, name="b", scope=["*"])
        self.assertNotEqual(k1.prefix, k2.prefix)

    def test_scope_stored_as_list(self):
        key, _ = APIKey.issue(user=self.user, name="ci", scope=["pdf-to-word", "merge"])
        key.refresh_from_db()
        self.assertEqual(key.scope, ["pdf-to-word", "merge"])
