"""Serializers for PDF comparison."""

from rest_framework import serializers


class ComparePDFSerializer(serializers.Serializer):
    """Serializer for visual PDF comparison requests."""

    pdf_file_1 = serializers.FileField(
        required=True,
        help_text="Base PDF file",
    )
    pdf_file_2 = serializers.FileField(
        required=True,
        help_text="PDF file to compare against the base file",
    )
    diff_threshold = serializers.IntegerField(
        required=False,
        default=32,
        min_value=5,
        max_value=80,
        help_text="Visual diff sensitivity threshold (lower = more sensitive)",
    )
