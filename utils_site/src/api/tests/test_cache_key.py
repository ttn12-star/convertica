"""Tests for the conversion result-cache key (CONVERTICA review B5).

The key used hashlib.md5(str(kwargs))[:8] — only 32 bits, so birthday
collisions are plausible across the 24h cache window at volume, which would
serve one user's output bytes for another user's identical-SHA input. Use a
wider digest over a stable JSON serialization.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from src.tasks.pdf_conversion import _cache_key


class CacheKeyTests(SimpleTestCase):
    def test_stable_regardless_of_kwarg_order(self):
        k1 = _cache_key("abc", "split_pdf", {"pages": "1-3", "mode": "range"})
        k2 = _cache_key("abc", "split_pdf", {"mode": "range", "pages": "1-3"})
        self.assertEqual(k1, k2)

    def test_different_params_differ(self):
        k1 = _cache_key("abc", "split_pdf", {"pages": "1-3"})
        k2 = _cache_key("abc", "split_pdf", {"pages": "1-4"})
        self.assertNotEqual(k1, k2)

    def test_different_sha_differs(self):
        self.assertNotEqual(
            _cache_key("abc", "split_pdf", {}), _cache_key("xyz", "split_pdf", {})
        )

    def test_hash_segment_is_wide(self):
        # Last colon-segment is the params hash; must be >= 16 hex chars (64 bits).
        params_hash = _cache_key("abc", "split_pdf", {"pages": "1"}).rsplit(":", 1)[-1]
        self.assertGreaterEqual(len(params_hash), 16)
