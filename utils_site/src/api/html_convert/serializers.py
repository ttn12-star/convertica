"""
Serializers for HTML to PDF conversion API.
"""

from django.conf import settings
from rest_framework import serializers


class HTMLToPDFSerializer(serializers.Serializer):
    """Serializer for HTML to PDF conversion requests."""

    html_content = serializers.CharField(
        required=True, help_text="HTML content to convert to PDF"
    )

    def validate_html_content(self, value):
        """Validate HTML content length based on user premium status."""
        request = self.context.get("request")
        is_premium = False

        if request and hasattr(request, "user") and request.user.is_authenticated:
            is_premium = getattr(request.user, "is_premium", False)

        max_length = (
            settings.HTML_TO_PDF_MAX_CHARS_PREMIUM
            if is_premium
            else settings.HTML_TO_PDF_MAX_CHARS_FREE
        )

        if len(value) > max_length:
            premium_limit = settings.HTML_TO_PDF_MAX_CHARS_PREMIUM
            raise serializers.ValidationError(
                f"HTML content exceeds maximum length of {max_length:,} characters. "
                f"{'Premium users' if is_premium else 'Free users'} are limited to "
                f"{max_length:,} characters."
                + (
                    ""
                    if is_premium
                    else f" Upgrade to Premium for up to {premium_limit:,} characters."
                )
            )

        return value

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
