"""Serializer for Text to PDF conversion API."""

from django.conf import settings
from rest_framework import serializers


class TextToPDFSerializer(serializers.Serializer):
    """Validate pasted text + global style options for text -> PDF."""

    text = serializers.CharField(
        required=True,
        trim_whitespace=False,
        help_text="Plain text to render into a PDF",
    )

    font = serializers.ChoiceField(
        choices=[("sans", "Sans"), ("serif", "Serif"), ("mono", "Monospace")],
        default="sans",
        required=False,
    )
    font_size = serializers.IntegerField(
        min_value=8, max_value=72, default=12, required=False
    )
    # Hex color only (#rgb or #rrggbb) — keeps it out of arbitrary CSS.
    color = serializers.RegexField(
        r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$",
        default="#111111",
        required=False,
    )
    align = serializers.ChoiceField(
        choices=[
            ("left", "Left"),
            ("center", "Center"),
            ("right", "Right"),
            ("justify", "Justify"),
        ],
        default="left",
        required=False,
    )
    page_size = serializers.ChoiceField(
        choices=[("A4", "A4"), ("Letter", "Letter")],
        default="A4",
        required=False,
    )
    margin = serializers.ChoiceField(
        choices=[("narrow", "Narrow"), ("normal", "Normal"), ("wide", "Wide")],
        default="normal",
        required=False,
    )
    filename = serializers.CharField(
        required=False, default="document", help_text="Base filename for the PDF"
    )

    def validate_text(self, value):
        """Reject empty text and enforce the per-tier character limit."""
        if not value.strip():
            raise serializers.ValidationError("Please enter some text to convert.")

        request = self.context.get("request")
        is_premium = bool(
            request
            and getattr(request, "user", None)
            and request.user.is_authenticated
            and getattr(request.user, "is_premium", False)
        )
        max_length = (
            settings.TEXT_TO_PDF_MAX_CHARS_PREMIUM
            if is_premium
            else settings.TEXT_TO_PDF_MAX_CHARS_FREE
        )
        if len(value) > max_length:
            premium_limit = settings.TEXT_TO_PDF_MAX_CHARS_PREMIUM
            raise serializers.ValidationError(
                f"Text exceeds the maximum length of {max_length:,} characters."
                + (
                    ""
                    if is_premium
                    else f" Upgrade to Premium for up to {premium_limit:,} characters."
                )
            )
        return value
