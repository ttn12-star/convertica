"""Truthful-copy fixes (2026-07-17): deletion-timing, free/premium wording, pricing stats.

Asserts .po content, not rendered output — the CI test job does not run
compilemessages, so render-based i18n assertions pass locally on stale .mo
and fail the deploy gate.
"""

import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase
from django.utils.functional import Promise

LOCALES = ["ar", "es", "hi", "id", "pl", "ru"]

# Template msgids (exact strings from templates/frontend/*.html).
TEMPLATE_MSGIDS = [
    "Files deleted automatically",
    "Right after download for instant conversions",
    "Within about an hour for background, batch, and failed tasks",
    "Daily Conversions",
    "Max File Size",
    "Files per Batch",
    "Yes, Convertica is free to use — every core tool works at no cost with generous daily limits. Optional Premium unlocks higher limits, batch processing, and extra features.",
    "No registration required. You can use most tools instantly without creating an account. Premium features are available for advanced users.",
    "Files from instant conversions are deleted right after download; background and batch results are removed within about an hour. We never store your files permanently.",
]

# tool_configs msgids — must also match the runtime concatenation (see
# test_tool_config_msgids_exist_in_source).
TOOL_CONFIG_MSGIDS = [
    "No registration, no watermarks. Files deleted automatically after conversion",
    "Your Excel files are processed securely and deleted automatically after conversion. We never store your files permanently. Perfect for confidential business documents.",
    "Files are transferred over an encrypted connection and deleted automatically after processing",
    "Files deleted automatically after processing. Your documents stay private",
    "Files are deleted automatically right after processing — your signature is never stored",
    "Files are processed on the server and deleted automatically after download — we never store your images permanently",
]


def _po_text(lang):
    path = Path(settings.BASE_DIR) / "locale" / lang / "LC_MESSAGES" / "django.po"
    return path.read_text(encoding="utf-8")


def _collect_lazy_strings(obj, out):
    if isinstance(obj, Promise):
        out.add(str(obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_lazy_strings(v, out)
    elif isinstance(obj, list | tuple):
        for v in obj:
            _collect_lazy_strings(v, out)


class TruthfulCopyI18nTests(SimpleTestCase):
    def test_new_msgids_translated_in_all_locales(self):
        for lang in LOCALES:
            text = _po_text(lang)
            for msgid in TEMPLATE_MSGIDS + TOOL_CONFIG_MSGIDS:
                m = re.search(r'msgid "%s"\s*\nmsgstr "(.+)"' % re.escape(msgid), text)
                self.assertIsNotNone(m, f"{lang}: msgid missing: {msgid[:60]}")
                self.assertNotEqual(
                    m.group(1).strip(), "", f"{lang}: empty msgstr: {msgid[:60]}"
                )

    def test_tool_config_msgids_exist_in_source(self):
        """The .po msgids must equal the runtime string concatenations."""
        from django.utils import translation
        from src.frontend.tool_configs import TOOL_CONFIGS

        collected: set[str] = set()
        with translation.override(None):
            _collect_lazy_strings(TOOL_CONFIGS, collected)
        for msgid in TOOL_CONFIG_MSGIDS:
            self.assertIn(msgid, collected, f"not in tool_configs: {msgid[:60]}")

    def test_false_claims_removed_from_templates(self):
        base = Path(settings.BASE_DIR) / "templates" / "frontend"
        for name in ["index.html", "faq.html", "contact.html", "privacy.html"]:
            text = (base / name).read_text(encoding="utf-8")
            for phrase in [
                "deleted instantly",
                "deleted immediately",
                "typically within minutes",
                "Immediately after successful processing",
            ]:
                self.assertNotIn(phrase, text, f"{name}: stale claim: {phrase}")
        pricing = (base / "pricing.html").read_text(encoding="utf-8")
        for fake in ["10M+", "50K+", "99.9%"]:
            self.assertNotIn(fake, pricing, f"pricing.html: fabricated stat {fake}")
