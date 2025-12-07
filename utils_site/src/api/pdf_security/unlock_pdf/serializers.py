# serializers.py
from rest_framework import serializers


class UnlockPDFSerializer(serializers.Serializer):
    """Serializer for unlocking PDF."""

    pdf_file = serializers.FileField(required=True)
    password = serializers.CharField(
        required=True,
        min_length=1,
        max_length=100,
        write_only=True,
        trim_whitespace=True,
        help_text="Password to unlock the PDF.",
    )
