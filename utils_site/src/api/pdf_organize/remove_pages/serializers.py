# serializers.py
from rest_framework import serializers


class RemovePagesSerializer(serializers.Serializer):
    """Serializer for removing pages from PDF."""
    pdf_file = serializers.FileField(required=True)
    pages = serializers.CharField(
        required=True,
        help_text="Pages to remove. Comma-separated page numbers (1-indexed) or ranges like '1-3,5-7'."
    )

