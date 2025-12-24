"""Serializers for batch PDF watermark."""

from rest_framework import serializers


class AddWatermarkBatchSerializer(serializers.Serializer):
    """Serializer for batch PDF watermark requests."""

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        help_text="List of PDF files to watermark (up to 10 for premium users)",
        required=True,
        min_length=1,
        max_length=10,
    )

    watermark_type = serializers.ChoiceField(
        choices=["text", "image"],
        default="text",
        help_text="Type of watermark: 'text' or 'image'",
    )

    watermark_text = serializers.CharField(
        required=False,
        default="CONFIDENTIAL",
        help_text="Text to use as watermark (for text type)",
    )

    watermark_image = serializers.FileField(
        required=False,
        allow_null=True,
        help_text="Image file to use as watermark (for image type)",
    )

    x = serializers.FloatField(
        default=0.0,
        help_text="X coordinate of watermark position in PDF points",
    )

    y = serializers.FloatField(
        default=0.0,
        help_text="Y coordinate of watermark position in PDF points",
    )

    opacity = serializers.FloatField(
        default=0.3,
        min_value=0.0,
        max_value=1.0,
        help_text="Watermark opacity (0.0 to 1.0)",
    )

    rotation = serializers.FloatField(
        default=0.0,
        help_text="Watermark rotation angle in degrees",
    )

    scale = serializers.FloatField(
        default=1.0,
        min_value=0.1,
        max_value=5.0,
        help_text="Watermark scale factor",
    )

    color = serializers.CharField(
        default="#000000",
        help_text="Text color in hex format (for text watermarks)",
    )

    font_size = serializers.IntegerField(
        default=72,
        min_value=8,
        max_value=200,
        help_text="Font size for text watermarks",
    )

    pages = serializers.CharField(
        default="all",
        help_text="Pages to watermark: 'all', 'current', or custom range",
    )
