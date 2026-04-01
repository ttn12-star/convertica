"""Serializers for batch PDF flatten."""

from rest_framework import serializers


class FlattenPDFBatchSerializer(serializers.Serializer):
    """Serializer for batch PDF flatten requests."""

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        help_text="List of PDF files to flatten (up to 10 for premium users)",
        required=True,
        min_length=1,
        max_length=10,
    )
