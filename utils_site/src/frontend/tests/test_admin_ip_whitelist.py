"""Admin IP whitelist: exact addresses and CIDR ranges."""

from django.test import SimpleTestCase
from src.frontend.admin_protection import ip_in_whitelist


class IpInWhitelistTests(SimpleTestCase):
    def test_exact_ipv4_match(self):
        self.assertTrue(ip_in_whitelist("83.175.181.7", ["83.175.181.7"]))

    def test_non_matching_ipv4_is_rejected(self):
        self.assertFalse(ip_in_whitelist("83.175.181.8", ["83.175.181.7"]))

    def test_ipv6_is_compared_as_an_address_not_a_string(self):
        # The same address written two legal ways must still match.
        self.assertTrue(
            ip_in_whitelist("2a02:a310:c18a:3880::1", ["2a02:a310:c18a:3880:0:0:0:1"])
        )

    def test_rotated_ipv6_host_part_matches_a_whitelisted_prefix(self):
        """The whole point: residential IPv6 rotates its host part.

        Both of these were the owner's address days apart; pinning either in
        full locks them out when the ISP rotates, so the /64 has to match.
        """
        net = ["2a02:a310:c18a:3880::/64"]
        self.assertTrue(ip_in_whitelist("2a02:a310:c18a:3880:7f06:9f32:3730:c400", net))
        self.assertTrue(ip_in_whitelist("2a02:a310:c18a:3880:b474:7ea5:bb81:200f", net))

    def test_a_different_prefix_is_still_rejected(self):
        self.assertFalse(
            ip_in_whitelist("2a02:a310:c18a:3881::1", ["2a02:a310:c18a:3880::/64"])
        )

    def test_ipv4_cidr(self):
        self.assertTrue(ip_in_whitelist("83.175.181.9", ["83.175.181.0/24"]))
        self.assertFalse(ip_in_whitelist("83.175.182.9", ["83.175.181.0/24"]))

    def test_a_broken_entry_is_skipped_rather_than_raising(self):
        # A stray control character in .env once made an entry unmatchable;
        # it must not take the whole admin down with a 500 either.
        self.assertTrue(
            ip_in_whitelist("127.0.0.1", ["8\x132.175.184.166", "127.0.0.1"])
        )

    def test_empty_client_ip_is_rejected(self):
        self.assertFalse(ip_in_whitelist("", ["127.0.0.1"]))

    def test_garbage_client_ip_is_rejected(self):
        self.assertFalse(ip_in_whitelist("not-an-ip", ["0.0.0.0/0"]))
