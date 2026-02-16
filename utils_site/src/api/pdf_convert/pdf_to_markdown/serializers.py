"""Serializers for PDF to Markdown conversion."""

from rest_framework import serializers


class PDFToMarkdownSerializer(serializers.Serializer):
    """Serializer for PDF to Markdown conversion requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to convert to Markdown",
    )
    detect_headings = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Detect heading structure from font sizes",
    )
    preserve_tables = serializers.BooleanField(
        required=False,
        default=True,
        help_text="Extract PDF tables and convert them to Markdown tables",
    )
