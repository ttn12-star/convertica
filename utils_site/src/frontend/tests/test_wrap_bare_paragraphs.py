"""Article intro paragraphs are written without <p>; the filter adds it.

Text nodes cannot be spaced by CSS, so unwrapped intro paragraphs rendered as
one run-on block. Existing block-level markup must be left exactly as it is.
"""

from django.test import SimpleTestCase
from src.frontend.templatetags.image_tags import wrap_bare_paragraphs


class WrapBareParagraphsTests(SimpleTestCase):
    def test_bare_intro_paragraphs_get_wrapped(self):
        html = wrap_bare_paragraphs("First intro line.\n\nSecond intro line.")

        self.assertEqual(html, "<p>First intro line.</p>\n\n<p>Second intro line.</p>")

    def test_existing_block_markup_is_untouched(self):
        source = "<h2>Heading</h2>\n\n<p>Body.</p>\n\n<ul>\n  <li>Item</li>\n</ul>"

        self.assertEqual(wrap_bare_paragraphs(source), source)

    def test_chunk_starting_with_inline_tag_is_a_paragraph(self):
        html = wrap_bare_paragraphs("<strong>Note:</strong> read this.")

        self.assertEqual(html, "<p><strong>Note:</strong> read this.</p>")

    def test_no_double_wrapping_on_reapply(self):
        once = wrap_bare_paragraphs("Intro.\n\n<p>Body.</p>")

        self.assertEqual(wrap_bare_paragraphs(once), once)

    def test_empty_value_survives(self):
        self.assertEqual(wrap_bare_paragraphs(""), "")

    def test_code_sample_with_blank_lines_is_left_alone(self):
        source = (
            "Intro line.\n\n"
            "<pre><code># Quarterly Report\n\n"
            "Revenue by region.\n\n"
            "| Region | Q1 |</code></pre>\n\n"
            "Closing line."
        )

        html = wrap_bare_paragraphs(source)

        self.assertIn("<p>Intro line.</p>", html)
        self.assertIn("<p>Closing line.</p>", html)
        # Nothing inside the code sample may be wrapped or re-spaced.
        self.assertIn(
            "<pre><code># Quarterly Report\n\nRevenue by region.\n\n| Region | Q1 |</code></pre>",
            html,
        )
