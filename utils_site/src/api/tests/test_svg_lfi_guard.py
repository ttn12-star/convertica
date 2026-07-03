"""SVG rasterization must reject external <image> references (LFI guard).

Regression: svglib resolves a non-data <image> href as a local filesystem path,
so an uploaded SVG with an absolute or ../ href to the public svg-to-ico /
favicon-generator tools could read an arbitrary local file into the output.
"""

from django.test import SimpleTestCase
from src.api.image_tools.svg_raster import _reject_external_image_refs


class SvgLfiGuardTests(SimpleTestCase):
    def test_inline_data_image_allowed(self):
        _reject_external_image_refs(
            b'<svg><image href="data:image/png;base64,AAAA"/></svg>'
        )  # must not raise

    def test_no_image_element_allowed(self):
        _reject_external_image_refs(b'<svg><rect width="10" height="10"/></svg>')

    def test_absolute_href_rejected(self):
        with self.assertRaises(ValueError):
            _reject_external_image_refs(b'<svg><image xlink:href="/etc/passwd"/></svg>')

    def test_traversal_href_rejected(self):
        with self.assertRaises(ValueError):
            _reject_external_image_refs(b'<svg><image href="../../secret.png"/></svg>')

    def test_case_insensitive_and_single_quotes(self):
        with self.assertRaises(ValueError):
            _reject_external_image_refs(b"<svg><IMAGE HREF='/etc/hosts' /></svg>")
