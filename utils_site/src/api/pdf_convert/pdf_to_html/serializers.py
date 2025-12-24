"""Serializers for PDF to HTML conversion."""

from rest_framework import serializers


class PDFToHTMLSerializer(serializers.Serializer):
    """Serializer for PDF to HTML conversion requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to convert to HTML format",
    )

    extract_images = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Extract and embed images from PDF",
    )

    preserve_layout = serializers.BooleanField(
        default=True,
        required=False,
        help_text="Preserve original PDF layout in HTML",
    )
