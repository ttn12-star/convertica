"""Unit tests for scripts/fix_blog_yaml_links.py.

Run standalone (no Django needed):
    python scripts/test_fix_blog_yaml_links.py
"""

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from fix_blog_yaml_links import rewrite


class RewriteTests(unittest.TestCase):

    def test_rewrites_pdf_edit_root_to_specific_tool(self):
        text = '<a href="/en/pdf-edit/">remove pages</a>'
        new, n = rewrite(text)
        self.assertEqual(new, '<a href="/en/pdf-edit/rotate/">remove pages</a>')
        self.assertEqual(n, 1)

    def test_rewrites_pdf_organize_root_to_merge(self):
        text = '<a href="/ru/pdf-organize/">организовать</a>'
        new, n = rewrite(text)
        self.assertEqual(new, '<a href="/ru/pdf-organize/merge/">организовать</a>')
        self.assertEqual(n, 1)

    def test_rewrites_pdf_security_root_preventively(self):
        text = '<a href="/es/pdf-security/">protect</a>'
        new, n = rewrite(text)
        self.assertEqual(new, '<a href="/es/pdf-security/protect/">protect</a>')
        self.assertEqual(n, 1)

    def test_rewrites_image_root_preventively(self):
        text = '<a href="/pl/image/">optimize</a>'
        new, n = rewrite(text)
        self.assertEqual(new, '<a href="/pl/image/optimize/">optimize</a>')
        self.assertEqual(n, 1)

    def test_no_lang_prefix_form_also_rewritten(self):
        text = '<a href="/pdf-edit/">x</a>'
        new, n = rewrite(text)
        self.assertEqual(new, '<a href="/pdf-edit/rotate/">x</a>')
        self.assertEqual(n, 1)

    def test_already_specific_tool_links_untouched(self):
        text = '<a href="/en/pdf-edit/rotate/">x</a> <a href="/en/pdf-organize/merge/">y</a>'
        new, n = rewrite(text)
        self.assertEqual(new, text)
        self.assertEqual(n, 0)

    def test_idempotent_on_second_pass(self):
        text = '<a href="/en/pdf-edit/">x</a>'
        once, _ = rewrite(text)
        twice, n2 = rewrite(once)
        self.assertEqual(twice, once)
        self.assertEqual(n2, 0)

    def test_multiple_replacements_in_same_text(self):
        text = '<a href="/en/pdf-edit/">a</a> and <a href="/en/pdf-organize/">b</a>'
        new, n = rewrite(text)
        self.assertIn("/en/pdf-edit/rotate/", new)
        self.assertIn("/en/pdf-organize/merge/", new)
        self.assertEqual(n, 2)

    def test_empty_string(self):
        new, n = rewrite("")
        self.assertEqual(new, "")
        self.assertEqual(n, 0)

    def test_unrelated_links_untouched(self):
        text = '<a href="/en/about/">about</a>'
        new, n = rewrite(text)
        self.assertEqual(new, text)
        self.assertEqual(n, 0)


if __name__ == "__main__":
    unittest.main()
