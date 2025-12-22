"""
Serializers for HTML to PDF conversion API.
"""

from rest_framework import serializers


class HTMLToPDFSerializer(serializers.Serializer):
    """Serializer for HTML to PDF conversion requests."""

    html_content = serializers.CharField(
        required=True, help_text="HTML content to convert to PDF"
    )

    filename = serializers.CharField(
        required=False,
        default="converted",
        help_text="Base filename for the output PDF",
    )

    page_size = serializers.ChoiceField(
        choices=[
            ("A4", "A4"),
            ("A3", "A3"),
            ("A5", "A5"),
            ("Letter", "Letter"),
            ("Legal", "Legal"),
        ],
        default="A4",
        required=False,
        help_text="PDF page size",
    )

    margin_top = serializers.CharField(
        default="1cm", required=False, help_text="Top margin (e.g., '1cm', '0.5in')"
    )

    margin_bottom = serializers.CharField(
        default="1cm", required=False, help_text="Bottom margin (e.g., '1cm', '0.5in')"
    )

    margin_left = serializers.CharField(
        default="1cm", required=False, help_text="Left margin (e.g., '1cm', '0.5in')"
    )

    margin_right = serializers.CharField(
        default="1cm", required=False, help_text="Right margin (e.g., '1cm', '0.5in')"
    )


class URLToPDFSerializer(serializers.Serializer):
    """Serializer for URL to PDF conversion requests."""

    url = serializers.URLField(
        required=True, help_text="URL to convert to PDF (must be publicly accessible)"
    )

    filename = serializers.CharField(
        required=False,
        default="converted",
        help_text="Base filename for the output PDF",
    )

    page_size = serializers.ChoiceField(
        choices=[
            ("A4", "A4"),
            ("A3", "A3"),
            ("A5", "A5"),
            ("Letter", "Letter"),
            ("Legal", "Legal"),
        ],
        default="A4",
        required=False,
        help_text="PDF page size",
    )

    margin_top = serializers.CharField(
        default="1cm", required=False, help_text="Top margin (e.g., '1cm', '0.5in')"
    )

    margin_bottom = serializers.CharField(
        default="1cm", required=False, help_text="Bottom margin (e.g., '1cm', '0.5in')"
    )

    margin_left = serializers.CharField(
        default="1cm", required=False, help_text="Left margin (e.g., '1cm', '0.5in')"
    )

    margin_right = serializers.CharField(
        default="1cm", required=False, help_text="Right margin (e.g., '1cm', '0.5in')"
    )
