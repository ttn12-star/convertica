# serializers.py
"""Add-Text-to-PDF input validation.

The browser editor sends a PDF plus a JSON `operations` array. Each
operation is one placed object: a text box, a whiteout rectangle, or a
highlight rectangle. Symbols (checkmarks etc.) arrive as ordinary text
operations carrying the symbol character.
"""
import json
import re

from rest_framework import serializers

HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")

FONT_KEYS = ("sans", "serif", "mono")
OPERATION_TYPES = ("text", "whiteout", "highlight")


class OperationItemSerializer(serializers.Serializer):
    """One placed object: which page, where, what."""

    type = serializers.ChoiceField(choices=OPERATION_TYPES)
    page = serializers.IntegerField(
        min_value=0,
        help_text="0-indexed page number.",
    )
    x = serializers.FloatField(
        min_value=0,
        help_text="X coordinate (PDF points, top-left origin).",
    )
    y = serializers.FloatField(
        min_value=0,
        help_text="Y coordinate (PDF points, top-left origin).",
    )
    width = serializers.FloatField(
        min_value=4,
        max_value=1200,
        help_text="Width in PDF points.",
    )
    height = serializers.FloatField(
        min_value=4,
        max_value=1200,
        help_text="Height in PDF points.",
    )
    # text-only fields
    text = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        trim_whitespace=False,
        help_text="Text content (text operations only). Newlines preserved.",
    )
    font_key = serializers.ChoiceField(
        choices=FONT_KEYS, default="sans", required=False
    )
    font_size = serializers.FloatField(
        min_value=6, max_value=96, default=14, required=False
    )
    color = serializers.CharField(default="#111111", required=False)
    bold = serializers.BooleanField(default=False, required=False)
    italic = serializers.BooleanField(default=False, required=False)
    underline = serializers.BooleanField(default=False, required=False)
    align = serializers.ChoiceField(
        choices=("left", "center", "right"), default="left", required=False
    )

    def validate_color(self, value: str) -> str:
        if not HEX_COLOR_RE.match(value):
            raise serializers.ValidationError("color must be #rrggbb.")
        return value.lower()

    def validate(self, attrs):
        if attrs["type"] == "text" and not (attrs.get("text") or "").strip():
            raise serializers.ValidationError(
                {"text": "Text operations need non-empty text."}
            )
        return attrs


class AddTextPDFSerializer(serializers.Serializer):
    """Add-text input: a PDF plus a JSON array of placed operations."""

    MAX_OPERATIONS = 100

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to edit.",
    )
    operations = serializers.CharField(
        required=True,
        help_text=(
            "JSON-encoded array of operations. Each item: {type, page, x, y, "
            "width, height, text?, font_key?, font_size?, color?, bold?, "
            "italic?, underline?, align?}."
        ),
    )

    def validate_operations(self, value):
        try:
            items = json.loads(value) if isinstance(value, str) else value
        except (TypeError, ValueError) as exc:
            raise serializers.ValidationError(
                "operations must be a JSON array.",
            ) from exc

        if not isinstance(items, list):
            raise serializers.ValidationError("operations must be a JSON array.")
        if not items:
            raise serializers.ValidationError("At least one operation is required.")
        if len(items) > self.MAX_OPERATIONS:
            raise serializers.ValidationError(
                f"At most {self.MAX_OPERATIONS} operations per document.",
            )

        validated: list[dict] = []
        for index, item in enumerate(items):
            inner = OperationItemSerializer(data=item)
            if not inner.is_valid():
                raise serializers.ValidationError(
                    {f"operations[{index}]": inner.errors},
                )
            validated.append(inner.validated_data)
        return validated
