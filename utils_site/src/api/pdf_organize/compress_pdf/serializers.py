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
