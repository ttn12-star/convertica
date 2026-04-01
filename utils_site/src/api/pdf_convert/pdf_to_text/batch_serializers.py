"""Batch serializers for PDF to Text conversion."""

from rest_framework import serializers


class PDFToTextBatchSerializer(serializers.Serializer):
    """Serializer for batch PDF to Text conversion."""

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        help_text="List of PDF files to convert (max 10 for premium users)",
    )
    include_page_numbers = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Add page number dividers between pages",
    )
    preserve_layout = serializers.BooleanField(
        required=False,
        default=False,
        help_text="Try to preserve text layout/columns",
    )
