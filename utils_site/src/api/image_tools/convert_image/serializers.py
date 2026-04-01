# serializers.py
from rest_framework import serializers


class ConvertImageSerializer(serializers.Serializer):
    """Serializer for image format conversion requests."""

    image_file = serializers.ImageField(
        required=True,
        help_text="Image file to convert (JPEG, PNG, WebP, GIF, BMP, TIFF)",
    )
    output_format = serializers.ChoiceField(
        required=True,
        choices=["JPEG", "PNG", "WebP", "GIF", "BMP", "TIFF"],
        help_text="Target image format",
    )
    quality = serializers.IntegerField(
        required=False,
        default=90,
        min_value=10,
        max_value=100,
        help_text="Quality for lossy formats (JPEG, WebP) — 10-100, default 90",
    )
