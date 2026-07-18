# serializers.py
import re

from rest_framework import serializers

# Only these two placeholders are meaningful; anything else (a bare "{}",
# "{0}", "{page.__class__}", or a width spec like "{page:>99999999}") is a
# malformed template or a str.format-injection attempt and must be rejected.
_ALLOWED_PLACEHOLDERS_RE = re.compile(r"\{(?!page\}|total\})[^}]*\}")


class AddPageNumbersSerializer(serializers.Serializer):
    """Serializer for adding page numbers to PDF."""

    pdf_file = serializers.FileField(required=True)
    position = serializers.ChoiceField(
        choices=[
            "bottom-center",
            "bottom-left",
            "bottom-right",
            "top-center",
            "top-left",
            "top-right",
        ],
        required=False,
        default="bottom-center",
        help_text="Position of page numbers on the page.",
    )
    font_size = serializers.IntegerField(
        required=False,
        default=12,
        min_value=8,
        max_value=72,
        help_text="Font size for page numbers (8-72).",
    )
    start_number = serializers.IntegerField(
        required=False, default=1, min_value=1, help_text="Starting page number."
    )
    format_str = serializers.CharField(
        required=False,
        default="{page}",
        max_length=100,
        help_text="Format string for page numbers. Use {page} for page number, {total} for total pages.",
    )

    def validate_format_str(self, value):
        """Reject any placeholder other than {page}/{total}: the value is fed
        to a template substitution, so a stray {..} is either malformed input
        (was a 500) or a format-string-injection attempt."""
        bad = _ALLOWED_PLACEHOLDERS_RE.search(value)
        if bad:
            raise serializers.ValidationError(
                "Only {page} and {total} are allowed in the format."
            )
        return value
