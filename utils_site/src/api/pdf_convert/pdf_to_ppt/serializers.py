"""Serializers for PDF to PowerPoint conversion."""

from rest_framework import serializers


class PDFToPowerPointSerializer(serializers.Serializer):
    """Serializer for PDF to PowerPoint conversion requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to convert to PowerPoint format",
    )

    extract_images = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Extract and include images from PDF",
    )
