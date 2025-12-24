"""Serializers for batch PDF cropping."""

from rest_framework import serializers


class CropPDFBatchSerializer(serializers.Serializer):
    """Serializer for batch PDF cropping requests."""

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        help_text="List of PDF files to crop (up to 10 for premium users)",
        required=True,
        min_length=1,
        max_length=10,
    )

    x = serializers.FloatField(
        default=0.0,
        help_text="X coordinate of crop box (left edge) in PDF points",
    )

    y = serializers.FloatField(
        default=0.0,
        help_text="Y coordinate of crop box (bottom edge) in PDF points",
    )

    width = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Width of crop box in PDF points (null = use remaining width)",
    )

    height = serializers.FloatField(
        required=False,
        allow_null=True,
        help_text="Height of crop box in PDF points (null = use remaining height)",
    )

    pages = serializers.CharField(
        default="all",
        help_text="Pages to crop: 'all', 'current', or custom range like '1-3,5,7-9'",
    )

    scale_to_page_size = serializers.BooleanField(
        default=False,
        help_text="Scale cropped area to full page size",
    )
