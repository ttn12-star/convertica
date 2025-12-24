"""Serializers for batch PDF page numbers."""

from rest_framework import serializers


class AddPageNumbersBatchSerializer(serializers.Serializer):
    """Serializer for batch PDF page numbers requests."""

    pdf_files = serializers.ListField(
        child=serializers.FileField(),
        help_text="List of PDF files to add page numbers (up to 10 for premium users)",
        required=True,
        min_length=1,
        max_length=10,
    )

    position = serializers.ChoiceField(
        choices=[
            "top-left",
            "top-center",
            "top-right",
            "bottom-left",
            "bottom-center",
            "bottom-right",
        ],
        default="bottom-center",
        help_text="Position of page numbers on the page",
    )

    font_size = serializers.IntegerField(
        default=12,
        min_value=6,
        max_value=72,
        help_text="Font size for page numbers",
    )

    color = serializers.CharField(
        default="#000000",
        help_text="Text color in hex format",
    )

    format = serializers.ChoiceField(
        choices=["number", "page_of_total", "roman"],
        default="number",
        help_text="Format of page numbers: 'number' (1,2,3), 'page_of_total' (Page 1 of 10), 'roman' (i,ii,iii)",
    )

    start_number = serializers.IntegerField(
        default=1,
        min_value=1,
        help_text="Starting page number",
    )

    pages = serializers.CharField(
        default="all",
        help_text="Pages to add numbers: 'all', or custom range",
    )
