# serializers.py
from rest_framework import serializers


class CropPDFSerializer(serializers.Serializer):
    """Serializer for PDF cropping requests."""

    pdf_file = serializers.FileField(required=True)
    x = serializers.FloatField(
        required=False,
        default=0.0,
        min_value=0.0,
        help_text="X coordinate of crop box (left edge in points).",
    )
    y = serializers.FloatField(
        required=False,
        default=0.0,
        min_value=0.0,
        help_text="Y coordinate of crop box (bottom edge in points).",
    )
    width = serializers.FloatField(
        required=False,
        help_text="Width of crop box in points. If not provided, uses remaining width.",
    )
    height = serializers.FloatField(
        required=False,
        help_text="Height of crop box in points. If not provided, uses remaining height.",
    )
    pages = serializers.CharField(
        required=False,
        default="all",
        help_text="Pages to crop. Use 'all' for all pages, or comma-separated page numbers (1-indexed).",
    )
