"""Serializers for EPUB conversion endpoints."""

from rest_framework import serializers


class EPUBToPDFSerializer(serializers.Serializer):
    """Serializer for EPUB to PDF conversion requests."""

    epub_file = serializers.FileField(
        required=True,
        help_text="EPUB file to convert to PDF format",
    )


class PDFToEPUBSerializer(serializers.Serializer):
    """Serializer for PDF to EPUB conversion requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to convert to EPUB format",
    )
