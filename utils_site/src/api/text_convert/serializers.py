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
        """Reject empty text and enforce the per-tier character limit.

        Ladder: anonymous < registered (logged-in) < premium. The tier comes from
        the request in serializer context — base_views passes it, so this runs
        with the real user, not always the anonymous floor.
        """
        if not value.strip():
            raise serializers.ValidationError("Please enter some text to convert.")

        request = self.context.get("request")
        user = getattr(request, "user", None) if request else None
        is_authenticated = bool(user and user.is_authenticated)
        is_premium = is_authenticated and bool(getattr(user, "is_premium", False))

        if is_premium:
            max_length = settings.TEXT_TO_PDF_MAX_CHARS_PREMIUM
        elif is_authenticated:
            max_length = settings.TEXT_TO_PDF_MAX_CHARS_REGISTERED
        else:
            max_length = settings.TEXT_TO_PDF_MAX_CHARS_FREE

        if len(value) > max_length:
            # Point each tier at the next rung up so the message is actionable.
            if is_premium:
                upgrade_hint = ""
            elif is_authenticated:
                upgrade_hint = (
                    " Upgrade to Premium for up to "
                    f"{settings.TEXT_TO_PDF_MAX_CHARS_PREMIUM:,} characters."
                )
            else:
                upgrade_hint = (
                    " Log in for up to "
                    f"{settings.TEXT_TO_PDF_MAX_CHARS_REGISTERED:,}, or upgrade to "
                    f"Premium for {settings.TEXT_TO_PDF_MAX_CHARS_PREMIUM:,} characters."
                )
            raise serializers.ValidationError(
                f"Text exceeds the maximum length of {max_length:,} characters."
                + upgrade_hint
            )
        return value
