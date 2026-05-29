# serializers.py
from rest_framework import serializers


class ICOToPNGSerializer(serializers.Serializer):
    """Serializer for ICO-to-PNG conversion requests."""

    ico_file = serializers.FileField(
        required=True,
        help_text="Source .ico file to convert to PNG.",
    )
