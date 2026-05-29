# serializers.py
from rest_framework import serializers


class GenerateFaviconSerializer(serializers.Serializer):
    """Serializer for full favicon-package (ZIP) generation requests."""

    # FileField (not ImageField): SVG is a valid input here but is not a valid
    # ImageField payload.
    image_file = serializers.FileField(
        required=True,
        help_text="Source image (PNG, JPEG, WebP, GIF, BMP, TIFF, or SVG).",
    )
