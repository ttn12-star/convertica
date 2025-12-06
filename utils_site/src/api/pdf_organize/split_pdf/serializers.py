# serializers.py
from rest_framework import serializers


class SplitPDFSerializer(serializers.Serializer):
    """Serializer for PDF split requests."""
    pdf_file = serializers.FileField(required=True)
    split_type = serializers.ChoiceField(
        choices=['page', 'range', 'every_n'],
        required=False,
        default='page',
        help_text="Split type: 'page' (one page per file), 'range' (by page ranges), 'every_n' (every N pages)."
    )
    pages = serializers.CharField(
        required=False,
        help_text="For 'page': comma-separated page numbers. For 'range': ranges like '1-3,5-7'. For 'every_n': number of pages per file."
    )

