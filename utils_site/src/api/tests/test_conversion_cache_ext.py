"""Regression tests for cached-result output extensions.

Bug (CONVERTICA review, 2026-05-29): FAST_CONVERSION_TYPES results are cached
by input SHA-256 for 24h. On a cache *hit* the served filename's extension was
rebuilt from a hardcoded map that only knew ``pdf_to_jpg`` (.zip) and
``jpg_to_pdf`` (.pdf), defaulting everything else to ``.pdf``. ``split_pdf``
produces a ZIP, so an identical re-upload within 24h was served as
``name_convertica.pdf`` containing ZIP bytes — a corrupt download.

These tests pin the extension resolution so multi-file ZIP outputs
(``split_pdf``, ``pdf_to_jpg``) keep their ``.zip`` extension on cache hits.
"""

from __future__ import annotations

from django.test import SimpleTestCase
from src.tasks.pdf_conversion import FAST_CONVERSION_TYPES, _cached_output_ext


class CachedOutputExtTests(SimpleTestCase):
    def test_split_pdf_resolves_to_zip(self):
        # The bug: split_pdf produces a ZIP but fell through to ".pdf".
        self.assertEqual(_cached_output_ext("split_pdf"), ".zip")

    def test_pdf_to_jpg_resolves_to_zip(self):
        self.assertEqual(_cached_output_ext("pdf_to_jpg"), ".zip")

    def test_single_file_pdf_types_resolve_to_pdf(self):
        for ctype in ("compress_pdf", "merge_pdf", "rotate_pdf", "jpg_to_pdf"):
            with self.subTest(conversion_type=ctype):
                self.assertEqual(_cached_output_ext(ctype), ".pdf")

    def test_every_fast_type_has_a_known_extension(self):
        # No FAST conversion type should silently default to the wrong ext.
        for ctype in FAST_CONVERSION_TYPES:
            with self.subTest(conversion_type=ctype):
                self.assertIn(_cached_output_ext(ctype), {".pdf", ".zip"})
