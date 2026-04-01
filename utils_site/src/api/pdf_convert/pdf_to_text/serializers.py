"""Serializers for PDF to Text conversion."""

from rest_framework import serializers


class PDFToTextSerializer(serializers.Serializer):
    """Serializer for PDF to Text conversion requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to extract text from",
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
