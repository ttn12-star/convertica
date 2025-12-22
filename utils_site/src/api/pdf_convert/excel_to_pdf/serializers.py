"""
Serializers for Excel to PDF conversion API.
"""

from rest_framework import serializers


class ExcelToPDFSerializer(serializers.Serializer):
    """Serializer for Excel to PDF conversion requests."""

    excel_file = serializers.FileField(
        required=True, help_text="Excel file (.xls or .xlsx) to convert to PDF"
    )


class ExcelToPDFBatchSerializer(serializers.Serializer):
    """Serializer for batch Excel to PDF conversion requests."""

    excel_files = serializers.ListField(
        child=serializers.FileField(),
        required=True,
        min_length=1,
        max_length=20,  # Premium users can process up to 20 files
        help_text="List of Excel files (.xls or .xlsx) to convert to PDF",
    )
