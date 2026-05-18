"""Serializer for HEIC / HEIF image conversion (premium)."""

from rest_framework import serializers


class ConvertHEICSerializer(serializers.Serializer):
    """Single-file HEIC → JPG/PNG/PDF.

    Uses FileField (not ImageField) because Pillow's image verification
    runs before pillow-heif's plugin is registered for the request's
    serializer context — extension whitelisting is enforced by the
    BaseConversionAPIView's ALLOWED_EXTENSIONS instead.
    """

    image_file = serializers.FileField(
        required=True,
        help_text="HEIC or HEIF image file (Apple iPhone / iPad photo).",
    )
    output_format = serializers.ChoiceField(
        required=False,
        default="JPEG",
        choices=["JPEG", "JPG", "PNG", "PDF"],
        help_text="Target format: JPEG (alias JPG), PNG, or PDF.",
    )
    quality = serializers.IntegerField(
        required=False,
        default=90,
        min_value=10,
        max_value=100,
        help_text="Quality for JPEG output (10-100, default 90). Ignored for PNG.",
    )
