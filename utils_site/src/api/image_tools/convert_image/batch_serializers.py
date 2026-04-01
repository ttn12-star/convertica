"""Batch serializers for image format conversion."""

from rest_framework import serializers


class ConvertImageBatchSerializer(serializers.Serializer):
    """Serializer for batch image format conversion requests."""

    image_files = serializers.ListField(
        child=serializers.ImageField(),
        required=True,
        help_text="List of image files to convert (max 10 for premium users)",
    )
    output_format = serializers.ChoiceField(
        required=True,
        choices=["JPEG", "PNG", "WebP", "GIF", "BMP", "TIFF"],
        help_text="Target format for all images",
    )
    quality = serializers.IntegerField(
        required=False,
        default=90,
        min_value=10,
        max_value=100,
        help_text="Quality for lossy formats (JPEG, WebP) — 10-100, default 90",
    )
