# serializers.py
from rest_framework import serializers


class OrganizePDFSerializer(serializers.Serializer):
    """Serializer for general PDF organization requests."""
    pdf_file = serializers.FileField(required=True)
    operation = serializers.ChoiceField(
        choices=['reorder', 'sort'],
        required=False,
        help_text="Organization operation type."
    )

