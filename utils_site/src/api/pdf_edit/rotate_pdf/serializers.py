# serializers.py
from rest_framework import serializers


class RotatePDFSerializer(serializers.Serializer):
    """Serializer for PDF rotation requests."""

    pdf_file = serializers.FileField(required=True)
    angle = serializers.IntegerField(
        required=False,
        default=90,
        help_text="Rotation angle in degrees. Must be 90, 180, or 270.",
    )
    pages = serializers.CharField(
        required=False,
        default="all",
        help_text="Pages to rotate. Use 'all' for all pages, or comma-separated page numbers (1-indexed), e.g., '1,3,5' or '1-5'.",
    )
