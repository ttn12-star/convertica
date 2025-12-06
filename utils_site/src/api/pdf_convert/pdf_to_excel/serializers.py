# serializers.py
from rest_framework import serializers


class PDFToExcelSerializer(serializers.Serializer):
    """Serializer for PDF to Excel conversion."""
    pdf_file = serializers.FileField(required=True)
    pages = serializers.CharField(
        required=False,
        default="all",
        help_text="Pages to extract tables from. Use 'all' for all pages, or specify pages like '1,3,5' or '1-5'."
    )

