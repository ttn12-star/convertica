"""Batch serializers for image optimization."""

from rest_framework import serializers


class OptimizeImageBatchSerializer(serializers.Serializer):
    """Serializer for batch image optimization requests."""

    image_files = serializers.ListField(
        child=serializers.ImageField(),
        required=True,
        help_text="List of image files to optimize (max 10 for premium users)",
    )
    quality = serializers.IntegerField(
        required=False,
        default=85,
        min_value=10,
        max_value=100,
        help_text="Compression quality (10-100, default 85)",
    )
    output_format = serializers.ChoiceField(
        required=False,
        default="",
        allow_blank=True,
        choices=["", "JPEG", "PNG", "WebP"],
        help_text="Output format (empty = keep each image's original format)",
    )
    max_width = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=100,
        max_value=10000,
        help_text="Maximum width in pixels (optional, aspect ratio preserved)",
    )
    max_height = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=100,
        max_value=10000,
        help_text="Maximum height in pixels (optional, aspect ratio preserved)",
    )
