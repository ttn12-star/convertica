# serializers.py
from rest_framework import serializers


class AddPageNumbersSerializer(serializers.Serializer):
    """Serializer for adding page numbers to PDF."""
    pdf_file = serializers.FileField(required=True)
    position = serializers.ChoiceField(
        choices=['bottom-center', 'bottom-left', 'bottom-right', 'top-center', 'top-left', 'top-right'],
        required=False,
        default='bottom-center',
        help_text="Position of page numbers on the page."
    )
    font_size = serializers.IntegerField(
        required=False,
        default=12,
        min_value=8,
        max_value=72,
        help_text="Font size for page numbers (8-72)."
    )
    start_number = serializers.IntegerField(
        required=False,
        default=1,
        min_value=1,
        help_text="Starting page number."
    )
    format_str = serializers.CharField(
        required=False,
        default="{page}",
        help_text="Format string for page numbers. Use {page} for page number, {total} for total pages."
    )

