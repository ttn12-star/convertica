# serializers.py
from rest_framework import serializers


class CompressPDFSerializer(serializers.Serializer):
    """Serializer for compressing PDF."""

    pdf_file = serializers.FileField(required=True)
    compression_level = serializers.ChoiceField(
        choices=["low", "medium", "high"],
        default="medium",
        required=False,
        help_text="Compression level: low (faster, less compression), medium (balanced), high (slower, more compression).",
    )
    target_size_kb = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=20,
        max_value=500_000,
        help_text="Optional target size in KB (e.g. 100, 200, 500, 1024). Image "
        "quality and resolution are lowered step by step until the file fits; "
        "if it can't, the smallest result is returned (see X-Target-Met).",
    )
