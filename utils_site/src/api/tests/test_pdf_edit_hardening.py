"""pdf_edit hardening regressions:
- add_page_numbers format_str must reject str.format-injection / malformed
  templates as a clean 400 (was a 500 + injection surface).
- The maintenance tmp reaper must sweep every tool's temp-dir prefix, or a
  failed conversion leaks /tmp until ENOSPC downs the service.
"""

from django.test import SimpleTestCase
from src.api.pdf_edit.add_page_numbers.serializers import AddPageNumbersSerializer
from src.tasks.maintenance import _CONVERTER_TMP_PREFIXES


class FormatStrValidationTests(SimpleTestCase):
    def _errs(self, value):
        s = AddPageNumbersSerializer(data={"format_str": value})
        s.is_valid()
        return s.errors

    def test_valid_templates_accepted(self):
        for good in ("{page}", "{total}", "Page {page} of {total}", "- {page} -"):
            self.assertNotIn("format_str", self._errs(good), f"rejected {good!r}")

    def test_injection_and_malformed_rejected(self):
        for bad in (
            "{}",
            "{0}",
            "{foo}",
            "{page.__class__.__mro__}",
            "{page:>99999999}",
        ):
            self.assertIn("format_str", self._errs(bad), f"accepted {bad!r}")


class ReaperPrefixCoverageTests(SimpleTestCase):
    def test_all_known_tool_prefixes_are_swept(self):
        # Prefixes each tool actually passes to tempfile.mkdtemp / BasePDFProcessor.
        required = [
            # pdf_edit
            "rotate_pdf_",
            "add_pages_",
            "watermark_",
            "crop_pdf_",
            "sign_pdf_",
            "add_text_",
            "flatten_pdf_",
            # pdf_organize
            "merge_pdf_",
            "split_pdf_",
            "remove_pages_",
            "extract_pages_",
            "organize_pdf_",
            "compress_pdf_",
            # pdf_security
            "protect_pdf_",
            "unlock_pdf_",
            # image
            "protect_image_",
        ]
        missing = [p for p in required if not p.startswith(_CONVERTER_TMP_PREFIXES)]
        self.assertEqual(missing, [], f"reaper misses prefixes: {missing}")
