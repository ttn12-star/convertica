# serializers.py
from rest_framework import serializers


class OptimizeImageSerializer(serializers.Serializer):
    """Serializer for image optimization requests."""

    image_file = serializers.ImageField(
        required=True,
        help_text="Image to optimize (JPEG, PNG, WebP, GIF)",
    )
    quality = serializers.IntegerField(
        required=False,
        default=85,
        min_value=10,
        max_value=100,
        help_text="Quality (10-100, default 85). Lower = smaller file, higher = better quality.",
    )
    output_format = serializers.ChoiceField(
        required=False,
        default="",
        allow_blank=True,
        choices=["", "JPEG", "PNG", "WebP"],
        help_text="Output format (empty = keep original format)",
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
