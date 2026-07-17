"""Guard that the PDF/A source strings stay present in every locale .po.

We assert .po *content* (not rendered output): the CI test job does not run
compilemessages, so a render-based check would pass locally on stale .mo yet
fail the tag-deploy gate. See memory feedback_ci_no_compilemessages_i18n_tests.
"""

import unittest
from pathlib import Path

# Representative msgids introduced by the PDF/A tool (config + template).
_MARKERS = (
    "PDF to PDF/A Converter",
    "What is PDF/A and why do I need it?",
    "PDF/A-2b — recommended (transparency, layers)",
)
_LANGS = ("ar", "en", "es", "hi", "id", "pl", "ru")


def _locale_dir() -> Path:
    # utils_site/src/api/pdf_convert/pdf_to_pdfa/tests/ -> repo root/locale
    here = Path(__file__).resolve()
    for parent in here.parents:
        cand = parent / "locale"
        if cand.is_dir():
            return cand
    raise AssertionError("locale/ directory not found")


class PdfToPdfaI18nTest(unittest.TestCase):
    def test_msgids_present_in_every_locale(self):
        locale = _locale_dir()
        for lang in _LANGS:
            po = (locale / lang / "LC_MESSAGES" / "django.po").read_text("utf-8")
            for marker in _MARKERS:
                self.assertIn(
                    'msgid "%s"' % marker,
                    po,
                    "missing PDF/A msgid %r in %s" % (marker, lang),
                )
