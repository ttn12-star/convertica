"""Regression tests for Sentry noise filters.

Covers two failure modes that flooded Sentry on 2026-05-13/14:

1. ``pdf2docx`` logs ``Ignore page N due to making/parsing page error`` at
   ERROR level via the root logger when a single page fails to render. The
   library recovers internally (page is skipped, conversion continues), so
   these are not actionable bugs.

2. Intermediate retry diagnostics inside the LibreOffice conversion path
   (``no_pdf_created`` / ``no_pdf_created_fallback`` /
   ``conversion_fallback_timeout`` / ``conversion_all_failed``) were emitted
   at ERROR level even though a fallback or outer retry followed. With
   ``enable_logs=True`` they each became their own Sentry issue, splitting a
   single conversion failure across 4 issues.
"""

from __future__ import annotations

import re
from pathlib import Path

from django.test import SimpleTestCase
from src.api.sentry_filters import is_pdf2docx_page_skip_noise


class Pdf2docxNoiseFilterTests(SimpleTestCase):
    def test_drops_making_page_error_from_root_logger(self):
        event = {
            "logger": "root",
            "logentry": {
                "message": (
                    "Ignore page 26 due to making page error: "
                    "list index out of range"
                ),
            },
        }
        self.assertTrue(is_pdf2docx_page_skip_noise(event))

    def test_drops_parsing_page_error_from_root_logger(self):
        event = {
            "logger": "root",
            "logentry": {
                "message": "Ignore page 7 due to parsing page error: bad xref",
            },
        }
        self.assertTrue(is_pdf2docx_page_skip_noise(event))

    def test_keeps_event_when_logger_is_not_root(self):
        # An identically-worded log from our own code should not be filtered:
        # we *want* to know if our conversion code is logging it.
        event = {
            "logger": "src.api.pdf_convert",
            "logentry": {
                "message": (
                    "Ignore page 26 due to making page error: "
                    "list index out of range"
                ),
            },
        }
        self.assertFalse(is_pdf2docx_page_skip_noise(event))

    def test_keeps_unrelated_root_logger_event(self):
        event = {
            "logger": "root",
            "logentry": {"message": "Database connection lost"},
        }
        self.assertFalse(is_pdf2docx_page_skip_noise(event))

    def test_handles_missing_logentry(self):
        # Sentry sometimes ships events without logentry (e.g. exception
        # events). The filter must not crash, and must not drop them.
        self.assertFalse(is_pdf2docx_page_skip_noise({"logger": "root"}))
        self.assertFalse(is_pdf2docx_page_skip_noise({}))


class LibreOfficeIntermediateLogLevelTests(SimpleTestCase):
    """Guard that the 4 intermediate retry-path log calls stay at WARNING.

    These checks are intentionally source-level: each event tag is unique
    enough that an ``event="<tag>"`` string locates exactly one call site,
    and we only need to confirm the preceding ``logger.<level>(`` keyword.
    Cheaper than mocking the whole subprocess + asyncio retry chain.
    """

    SOURCE_PATH = (
        Path(__file__).resolve().parents[2]
        / "api"
        / "pdf_convert"
        / "word_to_pdf_optimized.py"
    )

    # Tag -> reason it must stay non-error.
    INTERMEDIATE_EVENTS = {
        "no_pdf_created": "first attempt; fallback runs next",
        "no_pdf_created_fallback": "second attempt; third (simple) follows",
        "conversion_fallback_timeout": "raised; outer retry can run",
        "conversion_all_failed": "raised; outer retry can run",
    }

    def setUp(self):
        self.source = self.SOURCE_PATH.read_text(encoding="utf-8")

    def test_intermediate_events_logged_as_warning(self):
        for event_tag, reason in self.INTERMEDIATE_EVENTS.items():
            with self.subTest(event=event_tag, reason=reason):
                # Find the logger call immediately preceding this event tag.
                pattern = re.compile(
                    r"logger\.(\w+)\([^()]*?(?:\([^()]*\)[^()]*?)*?"
                    rf"\"event\": \"{re.escape(event_tag)}\"",
                    re.DOTALL,
                )
                matches = pattern.findall(self.source)
                self.assertEqual(
                    len(matches),
                    1,
                    f"expected exactly one logger call tagged {event_tag!r}, "
                    f"found {len(matches)}",
                )
                self.assertEqual(
                    matches[0],
                    "warning",
                    f"event={event_tag!r} ({reason}) must be logger.warning, "
                    f"found logger.{matches[0]} — see CONVERTICA-4V/W/X "
                    "in Sentry for why downgrading matters",
                )

    def test_final_conversion_failure_stays_error(self):
        # The post-retry final failure must remain at ERROR so we *do* alert.
        pattern = re.compile(
            r"logger\.(\w+)\([^()]*?(?:\([^()]*\)[^()]*?)*?"
            r"\"event\": \"conversion_failed\"",
            re.DOTALL,
        )
        matches = pattern.findall(self.source)
        self.assertEqual(len(matches), 1)
        self.assertEqual(
            matches[0],
            "error",
            "final conversion_failed event must stay logger.error so the "
            "real, post-retry failure still alerts in Sentry",
        )
