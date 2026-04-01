# serializers.py
from rest_framework import serializers


class FlattenPDFSerializer(serializers.Serializer):
    """Serializer for PDF flatten requests."""

    pdf_file = serializers.FileField(
        required=True,
        help_text="PDF file to flatten (removes interactive form fields and annotations)",
    )
