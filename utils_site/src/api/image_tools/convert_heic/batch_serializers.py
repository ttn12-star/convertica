"""Batch serializer for HEIC / HEIF image conversion (premium)."""

from rest_framework import serializers


class ConvertHEICBatchSerializer(serializers.Serializer):
    """Batch HEIC → JPG/PNG/PDF for premium users."""

    image_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        help_text="List of HEIC/HEIF files (max 10 for premium users).",
    )
    output_format = serializers.ChoiceField(
        required=False,
        default="JPEG",
        choices=["JPEG", "JPG", "PNG", "PDF"],
        help_text="Target format applied to every file.",
    )
    quality = serializers.IntegerField(
        required=False,
        default=90,
        min_value=10,
        max_value=100,
        help_text="Quality for JPEG output (10-100, default 90). Ignored for PNG.",
    )
